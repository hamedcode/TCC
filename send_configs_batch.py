import os
import json
import socket
import requests
import base64
import subprocess
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
import geoip2.database

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
MMDB_PATH = "GeoLite2-Country.mmdb"
REPLACE_TAG = "@Config724"
SENT_FILE = "sent_configs.txt"
INDEX_FILE = "last_index.txt"

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("❌ BOT_TOKEN یا CHANNEL_ID تعریف نشده‌اند.")

if not os.path.exists(MMDB_PATH):
    raise FileNotFoundError(f"❌ فایل GeoIP ({MMDB_PATH}) یافت نشد.")

reader = geoip2.database.Reader(MMDB_PATH)

def get_country_info(ip):
    try:
        resp = reader.country(ip)
        code = resp.country.iso_code or "ZZ"
        name = resp.country.name or "Unknown"
        flag = ''.join([chr(0x1F1E6 + ord(c) - 65) for c in code.upper()]) if code != "ZZ" else "🏳️"
        return flag, name
    except:
        return "🏳️", "Unknown"

def build_tag(ip):
    flag, name = get_country_info(ip)
    date = datetime.now().strftime("%m/%d")
    return f"{flag} {name} - {date} {REPLACE_TAG}"

def resolve_ip(host):
    try:
        return socket.gethostbyname(host)
    except:
        return host

def update_tag(cfg):
    if cfg.startswith("vmess://"):
        try:
            raw = cfg.replace("vmess://", "")
            padded = raw + '=' * (-len(raw) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode()).decode()
            data = json.loads(decoded)
            host = data.get("add", "")
            ip = resolve_ip(host)
            data["ps"] = build_tag(ip)
            encoded = base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':')).encode()).decode().rstrip("=")
            return "vmess://" + encoded
        except:
            return cfg
    elif any(cfg.startswith(proto) for proto in ["vless://", "trojan://", "ss://", "hy2://", "tuic://"]):
        try:
            parsed = urlparse(cfg)
            host = parsed.hostname or "8.8.8.8"
            ip = resolve_ip(host)
            new_tag = build_tag(ip)
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                new_tag
            ))
        except:
            return cfg
    else:
        return cfg

# حذف فایل ارسالی اگر مال روز قبل باشد
if os.path.exists(SENT_FILE):
    creation_time = datetime.fromtimestamp(os.path.getmtime(SENT_FILE))
    now = datetime.now()
    if (now - creation_time).days >= 1:
        os.remove(SENT_FILE)

# خواندن همه کانفیگ‌ها
with open("all_configs.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# خواندن ایندکس
last_index = 0
if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r") as f:
        try:
            last_index = int(f.read().strip())
        except:
            last_index = 0

batch_size = 10
end_index = min(last_index + batch_size, len(lines))
if last_index >= len(lines):
    print("✅ همه کانفیگ‌ها قبلاً ارسال شده.")
    exit(0)

batch = lines[last_index:end_index]
cleaned_batch = [update_tag(cfg) for cfg in batch]

# آمار و زمان
now = datetime.utcnow() + timedelta(hours=3, minutes=30)
time_str = now.strftime("%Y/%m/%d - %H:%M")

proto_set, port_set, flag_set = set(), set(), set()
for cfg in cleaned_batch:
    proto_set.add(cfg.split("://")[0])
    try:
        parsed = urlparse(cfg)
        if parsed.port:
            port_set.add(str(parsed.port))
        ip = resolve_ip(parsed.hostname or "8.8.8.8")
        flag, _ = get_country_info(ip)
        flag_set.add(flag)
    except:
        continue

summary = f"{len(cleaned_batch)} کانفیگ جدید با پروتکل‌های {'، '.join(sorted(proto_set))}"
if port_set:
    summary += f" و پورت‌های {'، '.join(sorted(port_set))}"
if flag_set:
    summary += f"\n🌍 کشورها: {' '.join(sorted(flag_set))}"

configs_text = "\n".join(cleaned_batch)

message = (
    f"📦 کانفیگ‌های جدید - {time_str}\n\n"
    f"{summary}\n\n"
    f"```text\n{configs_text}\n```\n"
    f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ‌ها توی هر منطقه فرق داره.\n"
    f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
)

# ارسال به تلگرام
res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
    "chat_id": CHANNEL_ID,
    "text": message,
    "parse_mode": "Markdown"
})

if res.status_code == 200:
    print("✅ پیام با موفقیت ارسال شد.")

    # ذخیره در فایل ثابت
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        for cfg in cleaned_batch:
            f.write(cfg + "\n")

    # ذخیره ایندکس جدید
    with open(INDEX_FILE, "w") as f:
        f.write(str(end_index))

    # افزودن به گیت
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"])
    subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"])
    subprocess.run(["git", "add", SENT_FILE, INDEX_FILE])
    subprocess.run(["git", "commit", "-m", "📝 Update sent_configs.txt and last_index.txt"])
    subprocess.run(["git", "push"])
else:
    print(f"❌ خطا در ارسال پیام: {res.text}")
