import os
import json
import datetime
import requests
import base64
import geoip2.database
from urllib.parse import urlparse

# تنظیمات اولیه
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@Config724"  # آیدی کانال با @
GEOIP_DB_PATH = "GeoLite2-Country.mmdb"
ALL_CONFIGS_FILE = "all_configs.txt"
DAILY_SENT_FILE = "sent_configs_" + datetime.datetime.now().strftime("%Y-%m-%d") + ".txt"
FLAGS = {
    "IR": "🇮🇷", "DE": "🇩🇪", "US": "🇺🇸", "GB": "🇬🇧", "FR": "🇫🇷", "NL": "🇳🇱", "TR": "🇹🇷", "SE": "🇸🇪", "FI": "🇫🇮",
    "RU": "🇷🇺", "SG": "🇸🇬", "IN": "🇮🇳", "CN": "🇨🇳", "JP": "🇯🇵", "CA": "🇨🇦", "NO": "🇳🇴", "AE": "🇦🇪", "CH": "🇨🇭"
}

# استخراج دامنه از کانفیگ
def extract_domain(config_line):
    try:
        if config_line.startswith("vmess://"):
            data = json.loads(base64.b64decode(config_line[8:] + "==").decode("utf-8"))
            return data.get("add", "")
        elif config_line.startswith("vless://") or config_line.startswith("trojan://"):
            domain = config_line.split("@")[1].split(":")[0]
            return domain
        elif config_line.startswith("ss://"):
            parts = config_line[5:].split("@")
            if len(parts) == 2:
                return parts[1].split(":")[0]
        return ""
    except:
        return ""

# گرفتن پرچم از روی آدرس IP یا دامنه
def get_country_flag(domain):
    try:
        reader = geoip2.database.Reader(GEOIP_DB_PATH)
        ip = domain if domain.replace('.', '').isdigit() else socket.gethostbyname(domain)
        response = reader.country(ip)
        country_code = response.country.iso_code
        return FLAGS.get(country_code, "")
    except:
        return ""

# بارگذاری کانفیگ‌ها
if not os.path.exists(ALL_CONFIGS_FILE):
    print("فایل all_configs.txt یافت نشد.")
    exit(1)

with open(ALL_CONFIGS_FILE, "r", encoding="utf-8") as f:
    all_configs = [line.strip() for line in f if line.strip()]

# بارگذاری لیست ارسال‌شده‌های قبلی
sent_configs = []
if os.path.exists(DAILY_SENT_FILE):
    with open(DAILY_SENT_FILE, "r", encoding="utf-8") as f:
        sent_configs = [line.strip() for line in f if line.strip()]

# فیلتر کانفیگ‌های جدید
new_configs = [cfg for cfg in all_configs if cfg not in sent_configs]
if not new_configs:
    print("کانفیگ جدیدی برای ارسال وجود ندارد.")
    exit(0)

# ارسال کانفیگ‌ها (حداکثر ۱۰ عدد)
configs_to_send = new_configs[:10]
formatted_configs = []
for cfg in configs_to_send:
    domain = extract_domain(cfg)
    flag = get_country_flag(domain)
    remark = domain or "Unknown"
    formatted_configs.append(f"{flag} `{remark}`\n{cfg}")

# ساخت متن نهایی پست
configs_text = "\n\n".join(formatted_configs)
footer = (
    f"```text\n{configs_text}\n```\n\n"
    f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ‌ها متفاوت است.\n"
    f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
)

# ارسال به تلگرام
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHANNEL_ID,
    "text": footer,
    "parse_mode": "Markdown"
}
response = requests.post(TELEGRAM_API, json=payload)

# لاگ وضعیت
print("📤 وضعیت ارسال به تلگرام:", response.status_code)
print("📩 پاسخ کامل تلگرام:", response.text)

# ذخیره کانفیگ‌های ارسال‌شده
if response.status_code == 200:
    with open(DAILY_SENT_FILE, "a", encoding="utf-8") as f:
        for cfg in configs_to_send:
            f.write(cfg + "\n")
else:
    print("⚠️ ارسال با خطا مواجه شد. اطلاعات بالا را بررسی کن.")
