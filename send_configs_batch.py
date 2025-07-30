import os
import requests

# 🔧 تنظیمات
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@Config724"
CONFIGS_FILE = "all_configs.txt"
INDEX_FILE = "last_index.txt"
SEND_COUNT = 10  # هر بار چند کانفیگ بفرسته

# 📦 بررسی وجود فایل کانفیگ‌ها
if not os.path.exists(CONFIGS_FILE):
    print(f"⛔ فایل {CONFIGS_FILE} پیدا نشد.")
    exit(1)

# 🧮 اگر ایندکس نبود، مقدار اولیه ایجاد کن
if not os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "w") as f:
        f.write("0")

# 🔢 خواندن ایندکس قبلی
with open(INDEX_FILE, "r") as f:
    last_index = int(f.read().strip())

# 📥 خواندن کانفیگ‌ها از فایل
with open(CONFIGS_FILE, "r", encoding="utf-8") as f:
    all_configs = [line.strip() for line in f if line.strip()]

# ✅ بررسی اینکه چیزی برای ارسال هست یا نه
new_configs = all_configs[last_index:last_index + SEND_COUNT]
if not new_configs:
    print("📭 کانفیگ جدیدی برای ارسال وجود ندارد.")
    exit(0)

# 📝 ساخت پیام
configs_text = "\n".join(new_configs)
message = (
    f"```text\n{configs_text}\n```\n\n"
    f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ ها توی هر منطقه فرق داره\n"
    f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
)

# 📤 ارسال پیام
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
response = requests.post(url, data={
    "chat_id": CHANNEL_ID,
    "text": message,
    "parse_mode": "Markdown"
})

# 📋 چاپ نتیجه
print("✅ وضعیت ارسال:", response.status_code, response.text)

# 📈 ذخیره ایندکس جدید
with open(INDEX_FILE, "w") as f:
    f.write(str(last_index + len(new_configs)))
