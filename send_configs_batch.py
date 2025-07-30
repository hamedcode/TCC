import os
import json
import base64
import requests
import socket
import datetime
import re
import geoip2.database
from pyrogram import Client

# 🔹 توابع کمکی یکپارچه‌شده
GEOIP_DB_PATH = "GeoLite2-City.mmdb"
reader = geoip2.database.Reader(GEOIP_DB_PATH)

def get_country_flag(domain_or_ip: str) -> str:
    try:
        ip = socket.gethostbyname(domain_or_ip)
        response = reader.city(ip)
        country_code = response.country.iso_code
        if country_code:
            return country_flag(country_code)
    except Exception:
        pass
    return "🏳️"

def country_flag(country_code: str) -> str:
    if not country_code:
        return "🏳️"
    return ''.join(
        chr(0x1F1E6 + ord(c.upper()) - ord('A')) for c in country_code
    )

def extract_domain_from_config(config: str) -> str:
    match = re.search(r'"(?:address|add|host)"\s*:\s*"([^"]+)"', config)
    if match:
        return match.group(1)
    return ""

def replace_remark(config: str, new_remark: str) -> str:
    return re.sub(r'"remark"\s*:\s*"[^"]+"', f'"remark": "{new_remark}"', config)

# 🔹 تنظیمات
CHANNEL_ID = "@Config724"
DAILY_FILE = "daily_configs.txt"

# خواندن سکرت
session_string = os.environ["PYROGRAM_SESSION_B64"]
session_bytes = base64.b64decode(session_string)

# ساخت کلاینت Pyrogram از سکرت
with open("my_session.session", "wb") as f:
    f.write(session_bytes)

app = Client("my_session")

# خواندن کانفیگ‌ها
with open("output/index.txt", "r") as f:
    index = int(f.read().strip())

config_files = sorted(os.listdir("output"))
configs_to_send = config_files[index:index + 10]

configs_text = ""
for filename in configs_to_send:
    with open(f"output/{filename}", "r", encoding="utf-8") as f:
        config = f.read()

    domain = extract_domain_from_config(config)
    flag = get_country_flag(domain)
    date_str = datetime.datetime.now().strftime("%m/%d")
    remark = f"{flag} {date_str} {CHANNEL_ID}"
    config = replace_remark(config, remark)
    configs_text += config + "\n\n"

# آپدیت ایندکس
with open("output/index.txt", "w") as f:
    f.write(str(index + len(configs_to_send)))

# ذخیره در فایل روزانه
today_file = DAILY_FILE
with open(today_file, "a", encoding="utf-8") as f:
    f.write(configs_text)

# حذف فایل دیروز
yesterday_file = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d") + "_configs.txt"
if os.path.exists(yesterday_file):
    os.remove(yesterday_file)

# ارسال به تلگرام
caption = (
    f"```text\n{configs_text}\n```\n\n"
    f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ‌ها توی هر منطقه فرق داره\n"
    f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
)

with app:
    app.send_message(CHANNEL_ID, caption)
