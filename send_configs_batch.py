import os
import re
import json
import requests
import datetime
import base64
import geoip2.database
from urllib.parse import urlparse

# 🔧 تنظیمات
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@Config724"
GEOIP_DB_PATH = "GeoLite2-Country.mmdb"
CONFIGS_FILE = "all_configs.txt"
INDEX_FILE = "last_index.txt"
SEND_COUNT = 10

# 🌐 پرچم کشورها
FLAGS = {
    "IR": "🇮🇷", "DE": "🇩🇪", "US": "🇺🇸", "GB": "🇬🇧", "FR": "🇫🇷", "NL": "🇳🇱", "CA": "🇨🇦",
    "RU": "🇷🇺", "CN": "🇨🇳", "JP": "🇯🇵", "AE": "🇦🇪", "IN": "🇮🇳", "TR": "🇹🇷", "SG": "🇸🇬",
    "FI": "🇫🇮", "SE": "🇸🇪", "NO": "🇳🇴", "IT": "🇮🇹", "AT": "🇦🇹", "CH": "🇨🇭", "BE": "🇧🇪",
    "PL": "🇵🇱", "UA": "🇺🇦", "ES": "🇪🇸", "KZ": "🇰🇿", "CZ": "🇨🇿", "RO": "🇷🇴", "TH": "🇹🇭"
}

def get_country_flag(ip):
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.country(ip)
            code = response.country.iso_code
            return FLAGS.get(code, "🏳️")
    except:
        return "🏳️"

def extract_domain(config):
    # استخراج دامنه یا IP
    try:
        if config.startswith("vmess://"):
            decoded = json.loads(base64.b64decode(config[8:] + "==="))
            return decoded.get("add", "")
        elif config.startswith("vless://") or config.startswith("trojan://") or config.startswith("ss://"):
            match = re.search(r"@([\w\.-]+)", config)
            return match.group(1) if match else ""
        else:
            return ""
    except:
        return ""

def extract_protocol(config):
    if config.startswith("vmess://"): return "vmess"
    if config.startswith("vless://"): return "vless"
    if config.startswith("ss://"): return "shadowsocks"
    if config.startswith("trojan://"): return "trojan"
    return "unknown"

# بررسی وجود فایل‌ها
if not os.path.exists(CONFIGS_FILE):
    print(f"⛔ فایل {CONFIGS_FILE} پیدا نشد.")
    exit(1)

if not os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "w") as f:
        f.write("0")

# خواندن ایندکس
with open(INDEX_FILE, "r") as f:
    last_index = int(f.read().strip())

# خواندن کانفیگ‌ها
with open(CONFIGS_FILE, "r", encoding="utf-8") as f:
    all_configs = [line.strip() for line in f if line.strip()]

new_configs = all_configs[last_index:last_index + SEND_COUNT]
if not new_configs:
    print("📭 کانفیگ جدیدی برای ارسال وجود ندارد.")
    exit(0)

# تولید لیست با ریمارک جدید
final_configs = []
today = datetime.datetime.now().strftime("%m/%d")
for cfg in new_configs:
    domain = extract_domain(cfg)
    ip = domain if re.match(r"\d+\.\d+\.\d+\.\d+", domain) else ""
    flag = get_country_flag(ip) if ip else "🏳️"
    proto = extract_protocol(cfg)
    remark = f"{flag} {today} | {proto.upper()} | {CHANNEL_ID}"
    if "remarks=" in cfg:
        cfg = re.sub(r"remarks=[^&\n]+", f"remarks={remark}", cfg)
    final_configs.append(cfg)

# ساخت پیام تلگرام
configs_text = "\n".join(final_configs)
message = (
    f"```text\n{configs_text}\n```\n\n"
    f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ ها توی هر منطقه فرق داره\n"
    f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
)

# ارسال به تلگرام
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
response = requests.post(url, data={
    "chat_id": CHANNEL_ID,
    "text": message,
    "parse_mode": "Markdown"
})

print("✅ وضعیت ارسال:", response.status_code, response.text)

# ذخیره ایندکس جدید
with open(INDEX_FILE, "w") as f:
    f.write(str(last_index + len(new_configs)))
