import os
import json
import socket
import requests
import base64
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
import geoip2.database

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
MMDB_PATH = "GeoLite2-Country.mmdb"
REPLACE_TAG = "@Config724"

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID not set")

if not os.path.exists(MMDB_PATH):
    raise FileNotFoundError(f"❌ فایل GeoIP ({MMDB_PATH}) یافت نشد. لطفاً آن را در ریشه پروژه قرار دهید.")

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

# خواندن کانفیگ‌ها
with open("all_configs.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# خواندن ایندکس
last_index = 0
if os.path.exists("last_index.txt"):
    with open("last_index.txt", "r") as f:
        for line in f:
            if line.strip().isdigit():
                last_index = int(line.strip())
                break

batch_size = 5
end_index = min(last_index + batch_size, len(lines))

if last_index >= len(lines):
    print("✅ همه کانفیگ‌ها ارسال شده.")
    exit(0)

batch = lines[last_index:end_index]
cleaned_batch = [update_tag(cfg) for cfg in batch]

# زمان تهران
tehran_time = datetime.utcnow() + timedelta(hours=3, minutes=30)
time_str = tehran_time.strftime("%Y/%m/%d - %H:%M")

# آمار
proto_set, port_set, flag_set = set(), set(), set()
for cfg in batch:
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

res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
    "chat_id": CHANNEL_ID,
    "text": message,
    "parse_mode": "Markdown"
})

if res.status_code != 200:
    print(f"❌ ارسال ناموفق: {res.text}")
else:
    print("✅ پیام ارسال شد.")

# ذخیره ایندکس جدید
with open("last_index.txt", "w") as f:
    f.write(str(end_index))
