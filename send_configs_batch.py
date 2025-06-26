import os
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID is not set in secrets")

all_file = "all_configs.txt"
index_file = "last_index.txt"

# خواندن همه کانفیگ‌ها
with open(all_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# خواندن آخرین اندیس ارسال‌شده
last_index = 0
if os.path.exists(index_file):
    with open(index_file, "r") as idx_file:
        try:
            last_index = int(idx_file.read().strip())
        except ValueError:
            last_index = 0

# محدوده‌ای که باید ارسال شود
batch_size = 5
end_index = min(last_index + batch_size, len(lines))

# ارسال
for i in range(last_index, end_index):
    config = lines[i]
    print(f"Sending [{i+1}/{len(lines)}]: {config[:50]}...")
    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": config
    })
    if res.status_code != 200:
        print(f"❌ Failed: {res.text}")
    else:
        print("✅ Sent.")

# ذخیره اندیس جدید
with open(index_file, "w") as idx_file:
    idx_file.write(str(end_index))

print(f"✅ Finished sending {end_index - last_index} configs.")
