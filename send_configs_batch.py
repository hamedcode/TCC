import os
import json
import time
import requests
from datetime import datetime
from utils import get_country_flag, extract_domain_from_config

# تنظیمات
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
BATCH_SIZE = 10
BATCH_INTERVAL = 60 * 30  # هر ۳۰ دقیقه

# مسیر فایل کانفیگ‌ها
CONFIGS_DIR = "output"
INDEX_FILE = "last_index.txt"
DAILY_FILE = f"sent_configs_{datetime.now().strftime('%Y-%m-%d')}.txt"

# مقداردهی اولیه ایندکس
if not os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "w") as f:
        f.write("0")

# دریافت کانفیگ‌ها
with open(INDEX_FILE, "r") as f:
    last_index = int(f.read().strip())

config_files = sorted(os.listdir(CONFIGS_DIR))
new_configs = config_files[last_index:last_index + BATCH_SIZE]

# قالب‌سازی و ارسال
configs_text = ""
for filename in new_configs:
    with open(os.path.join(CONFIGS_DIR, filename), "r", encoding="utf-8") as f:
        config = f.read().strip()

    # پردازش ریمارک: پرچم + تاریخ + آیدی کانال
    domain = extract_domain_from_config(config)
    flag = get_country_flag(domain)
    today = datetime.now().strftime("%m/%d")
    remark_line = f"{flag} {today} @Config724"

    # جایگزینی ریمارک در کانفیگ
    config = replace_remark(config, remark_line)

    # اضافه کردن به دسته
    configs_text += config + "\n"

# اگر کانفیگی برای ارسال هست
if configs_text:
    message = (
        f"```text\n{configs_text}\n```\n\n"
        f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ‌ها توی هر منطقه فرق داره\n"
        f"📡 برای دریافت بیشتر: @Config724"
    )

    response = requests.post(
        f"{API_URL}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
    )

    # ذخیره کانفیگ‌ها در فایل روزانه
    with open(DAILY_FILE, "a", encoding="utf-8") as f:
        f.write(configs_text + "\n")

    # بروزرسانی ایندکس
    with open(INDEX_FILE, "w") as f:
        f.write(str(last_index + len(new_configs)))
