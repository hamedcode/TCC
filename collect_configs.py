import os
import re
import json
import time
import shutil
import base64
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

CHANNEL_FILE = "channels.json"
OUTPUT_DIR = "output"
ALL_CONFIGS_FILE = "all_configs.txt"
INDEX_FILE = "last_index.txt"
CONFIG_PROTOCOLS = ["vmess://", "vless://", "ss://", "trojan://", "hy2://", "tuic://"]

CUTOFF_HOURS = 8
MAX_PAGES_PER_CHANNEL = 6  # هر صفحه‌ی t.me/s حدود ۲۰ پیام داره
REQUEST_TIMEOUT = 15
RETRY_COUNT = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

DEBUG = os.getenv("DEBUG", "0") == "1"
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=CUTOFF_HOURS)

# پاکسازی پوشه output
try:
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    print("🧹 پوشه output پاک شد.")
except Exception as e:
    print(f"❌ خطا در حذف output/: {e}")

# کاراکترهای نامرئی/کنترلی رایج که تلگرام یا کلاینت‌ها هنگام کپی/فرمت اضافه می‌کنن
INVISIBLE_CHARS_RE = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff\u00a0]"
)


def clean_text(text):
    if not text:
        return text
    return INVISIBLE_CHARS_RE.sub("", text)


# تابع استخراج کانفیگ‌ها از متن خام پیام
def extract_configs_from_text(text):
    found = []
    if not text:
        return found

    text = clean_text(text)

    # (?<![A-Za-z]) جلوی match شدن پروتکل‌هایی که زیررشته‌ی یه پروتکل دیگه‌ن رو می‌گیره
    # مثلاً "ss://" که داخل "vless://" هم به صورت زیررشته وجود داره
    for proto in CONFIG_PROTOCOLS:
        pattern = r"(?<![A-Za-z])" + re.escape(proto) + r"[^\s]+"
        found += re.findall(pattern, text)

    # بررسی خط به خط برای موارد base64-encoded (که با پروتکل شروع نمی‌شن)
    lines = text.splitlines()
    for line in lines:
        line = line.strip().strip("\"'").lstrip(">«»•-–—▪●◦ \t").strip()

        if len(line) >= 30 and re.fullmatch(r"[A-Za-z0-9+/=]+", line):
            try:
                padded = line + "=" * (-len(line) % 4)
                decoded = base64.b64decode(padded).decode("utf-8")
                for proto in CONFIG_PROTOCOLS:
                    pattern = r"(?<![A-Za-z])" + re.escape(proto) + r"[^\s]+"
                    found += re.findall(pattern, decoded)
            except Exception:
                continue

    found = [c.rstrip("\"'”’)]}.,،؛;") for c in found]
    return found


# تابع استخراج کانفیگ‌هایی که پشت لینک مخفی (hidden hyperlink) قایم شدن
def extract_configs_from_links(text_div):
    found = []
    if text_div is None:
        return found
    for a in text_div.find_all("a", href=True):
        href = clean_text(a["href"])
        for proto in CONFIG_PROTOCOLS:
            if href.startswith(proto):
                found.append(href.rstrip("\"'”’)]}.,،؛;"))
    return found


def normalize_channel(raw):
    ch = str(raw).strip()
    if ch.startswith("@"):
        ch = ch[1:]
    return ch


def fetch_page(username, before=None):
    url = f"https://t.me/s/{username}"
    if before:
        url += f"?before={before}"

    last_err = None
    for attempt in range(RETRY_COUNT):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429:
                # rate limit شدیم؛ کمی صبر و تلاش دوباره
                time.sleep(3 * (attempt + 1))
                last_err = f"HTTP 429 (rate limited)"
                continue
            raise Exception(f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(2 * (attempt + 1))

    raise Exception(last_err or "fetch failed")


def parse_messages(html):
    soup = BeautifulSoup(html, "html.parser")
    messages = []

    for wrap in soup.find_all("div", class_="tgme_widget_message"):
        post_id_attr = wrap.get("data-post", "")
        try:
            msg_id = int(post_id_attr.split("/")[-1])
        except (ValueError, IndexError):
            continue

        time_tag = wrap.find("time")
        msg_date = None
        if time_tag and time_tag.get("datetime"):
            try:
                msg_date = datetime.fromisoformat(time_tag["datetime"])
            except ValueError:
                msg_date = None

        text_div = wrap.find("div", class_="tgme_widget_message_text")
        text_content = text_div.get_text("\n") if text_div else ""

        messages.append({
            "id": msg_id,
            "date": msg_date,
            "text": text_content,
            "text_div": text_div,
        })

    return messages


with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    raw_channels = json.load(f)

all_configs = []

for raw_channel in raw_channels:
    channel = normalize_channel(raw_channel)

    # کانال‌های خصوصی (آیدی عددی، بدون یوزرنیم) با این روش قابل اسکرپ نیستن
    if channel.lstrip("-").isdigit():
        print(f"⏭️ {raw_channel}: کانال خصوصی/بدون یوزرنیم، رد شد (t.me/s فقط برای کانال‌های عمومی کار می‌کنه).")
        continue

    print(f"🔍 بررسی: @{channel}")
    configs = []
    total_fetched = 0
    within_cutoff = 0
    before = None
    reached_old_message = False

    try:
        for page in range(MAX_PAGES_PER_CHANNEL):
            try:
                html = fetch_page(channel, before)
            except Exception as fetch_err:
                print(f"⚠️ خطا در دریافت صفحه از @{channel}: {fetch_err}")
                break

            messages = parse_messages(html)
            if not messages:
                if page == 0:
                    print(f"⚠️ هیچ پیامی برای @{channel} پیدا نشد (شاید پیش‌نمایش عمومی غیرفعاله یا یوزرنیم اشتباهه).")
                break

            for m in messages:
                total_fetched += 1

                if m["date"] is not None and m["date"] < cutoff_time:
                    reached_old_message = True
                    continue

                within_cutoff += 1

                if DEBUG:
                    print(f"   [DEBUG] msg_id={m['id']} date={m['date']} text_len={len(m['text'])}")
                    if m["text"]:
                        print(f"   [DEBUG] raw content repr: {repr(m['text'])[:500]}")

                configs += extract_configs_from_text(m["text"])
                configs += extract_configs_from_links(m["text_div"])

            oldest_id = min(m["id"] for m in messages)
            before = oldest_id

            if reached_old_message:
                break

            time.sleep(1)  # فاصله بین صفحات همون کانال

        print(f"   ℹ️ @{channel}: {total_fetched} پیام fetch شد، {within_cutoff} پیام داخل بازه‌ی زمانی بود.")

        configs = list(set(configs))

        if configs:
            all_configs += configs
            output_path = os.path.join(OUTPUT_DIR, channel + ".txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(configs))
            print(f"✅ {len(configs)} کانفیگ از @{channel} ذخیره شد.")
        else:
            print(f"⚠️ کانفیگی در @{channel} یافت نشد.")

    except Exception as e:
        print(f"❌ خطا در @{channel}: {e}")

    time.sleep(2)  # فاصله بین کانال‌ها

with open(ALL_CONFIGS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(list(set(all_configs))))
print(f"\n📦 فایل all_configs.txt با {len(all_configs)} کانفیگ نوشته شد.")

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write("0")
print("🔁 فایل last_index.txt ریست شد.")
