import os
import requests
from datetime import datetime
import json
import geoip2.database
import base64
import re

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@Config724"
OUTPUT_FOLDER = "output"
GEOIP_DB_PATH = "GeoLite2-Country.mmdb"

# خواندن دیتابیس GeoIP
reader = geoip2.database.Reader(GEOIP_DB_PATH)

# تشخیص کشور از دامنه یا IP
def extract_domain_from_config(config):
    match = re.search(r'add(?:ress)?":\s*"?([^",\s]+)', config)
    if match:
        return match.group(1).strip()
    return None

def get_country_flag(ip_or_domain):
    try:
        response = reader.country(ip_or_domain)
        country_code = response.country.iso_code
        return country_flag_emoji(country_code)
    except:
        return "🏳️"

def country_flag_emoji(country_code):
    if not country_code:
        return "🏳️"
    return ''.join([chr(0x1F1E6 + ord(c.upper()) - ord('A')) for c in country_code])

# دریافت تاریخ امروز
today_str = datetime.now().strftime("%m-%d")
daily_file_path = f"{today_str}.txt"

# خواندن فایل ایندکس
INDEX_FILE = "last_index.txt"
if not os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "w") as f:
        f.write("0")

with open(INDEX_FILE, "r") as f:
    last_index = int(f.read().strip())

# گرفتن لیست فایل‌ها
files = sorted(os.listdir(OUTPUT_FOLDER))
new_files = files[last_index:last_index + 10]

configs_text = ""
for file in new_files:
    with open(os.path.join(OUTPUT_FOLDER, file), "r", encoding="utf-8") as f:
        config = f.read().strip()
        domain = extract_domain_from_config(config)
        flag = get_country_flag(domain) if domain else "🏳️"
        date_str = datetime.now().strftime("%m/%d")
        new_remark = f"{flag} {date_str} @Config724"
        # تغییر ریمارک فقط در خطوط دارای "remark"
        config = re.sub(r'"remark"\s*:\s*"([^"]*)"', f'"remark":"{new_remark}"', config)
        configs_text += config + "\n"

# ذخیره در فایل روزانه
with open(daily_file_path, "a", encoding="utf-8") as f:
    f.write(configs_text + "\n")

# ارسال به تلگرام
if configs_text:
    message = (
        f"```text\n{configs_text.strip()}\n```\n\n"
        f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ ها توی هر منطقه فرق داره\n"
        f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    })

    print("پیام ارسال شد:", response.status_code, response.text)

# بروزرسانی ایندکس
with open(INDEX_FILE, "w") as f:
    f.write(str(last_index + len(new_files)))
