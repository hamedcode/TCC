import os
import json
import base64
import re
import shutil
import time
from datetime import datetime, timedelta
from pyrogram import Client

SESSION_NAME = "pyrogram_config_collector"
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_B64 = os.getenv("PYROGRAM_SESSION_B64")

if not all([API_ID, API_HASH, SESSION_B64]):
    raise Exception("API_ID, API_HASH یا PYROGRAM_SESSION_B64 تعریف نشده است.")

with open(f"{SESSION_NAME}.session", "wb") as f:
    f.write(base64.b64decode(SESSION_B64))

CHANNEL_FILE = "channels.json"
OUTPUT_DIR = "output"
ALL_CONFIGS_FILE = "all_configs.txt"
INDEX_FILE = "last_index.txt"
CONFIG_PROTOCOLS = ["vmess://", "vless://", "ss://", "trojan://", "hy2://", "tuic://"]

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
        # حذف کاراکترهای رایج quote/bullet که ممکنه کاربر دستی اول خط بذاره
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

    # حذف کاراکترهای اضافی رایج که ممکنه به انتهای کانفیگ بچسبن (نقل‌قول، پرانتز و ...)
    found = [c.rstrip("\"'”’)]}.,،؛;") for c in found]
    return found


# تابع استخراج کانفیگ‌هایی که پشت لینک مخفی (hidden hyperlink / text_link) قایم شدن
def extract_configs_from_entities(msg):
    found = []
    entities = (msg.entities or []) + (msg.caption_entities or [])
    for ent in entities:
        url = getattr(ent, "url", None)  # فقط MessageEntityType.TEXT_LINK این رو داره
        if not url:
            continue
        url = clean_text(url)
        for proto in CONFIG_PROTOCOLS:
            if url.startswith(proto):
                found.append(url)
    return found

cutoff_time = datetime.utcnow() - timedelta(hours=8)

with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    channels = json.load(f)

all_configs = []

with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
    for channel in channels:
        print(f"🔍 بررسی: {channel}")
        try:
            messages = app.get_chat_history(channel, limit=50)
            configs = []

            for msg in messages:
                if msg.date < cutoff_time:
                    continue

                content = msg.text or msg.caption
                if content:
                    configs += extract_configs_from_text(str(content))

                configs += extract_configs_from_entities(msg)

            configs = list(set(configs))

            if configs:
                all_configs += configs
                output_path = os.path.join(OUTPUT_DIR, channel.replace("@", "").replace("-", "") + ".txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(configs))
                print(f"✅ {len(configs)} کانفیگ از {channel} ذخیره شد.")
            else:
                print(f"⚠️ کانفیگی در {channel} یافت نشد.")
        except Exception as e:
            print(f"❌ خطا در {channel}: {e}")
        
        time.sleep(2)  # ⏱️ افزودن تأخیر ۲ ثانیه‌ای بین کانال‌ها

# ذخیره‌ی فایل نهایی و ریست ایندکس
with open(ALL_CONFIGS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(list(set(all_configs))))
print(f"\n📦 فایل all_configs.txt با {len(all_configs)} کانفیگ نوشته شد.")

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write("0")
print("🔁 فایل last_index.txt ریست شد.")
