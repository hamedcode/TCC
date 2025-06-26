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

# خواندن اولین عدد معتبر از فایل ایندکس
last_index = 0
if os.path.exists(index_file):
    with open(index_file, "r") as idx_file:
        for line in idx_file:
            line = line.strip()
            if line.isdigit():
                last_index = int(line)
                break

# محدوده ارسال
batch_size = 5
end_index = min(last_index + batch_size, len(lines))

print(f"Total configs: {len(lines)} | Sending lines {last_index + 1} to {end_index}")

if last_index >= len(lines):
    print("✅ Nothing to send. All configs already sent.")
else:
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

    # ذخیره اندیس جدید (فقط یک عدد)
    with open(index_file, "w") as idx_file:
        idx_file.write(str(end_index))

    print(f"✅ Finished sending {end_index - last_index} configs.")
