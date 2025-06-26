import os
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")  # باید @channelusername باشه یا chat_id عددی

if not BOT_TOKEN or not CHAT_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID is not set in secrets")

# خواندن خطوط فایل all_configs.txt
with open("all_configs.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f.readlines() if line.strip()]

# ارسال یکی‌یکی با تاخیر ۵ دقیقه
for i, config in enumerate(lines):
    print(f"[{i+1}/{len(lines)}] Sending config...")
    response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": config
    })
    if response.status_code != 200:
        print(f"❌ Failed to send: {response.text}")
    else:
        print(f"✅ Sent successfully.")
    time.sleep(300)  # ۵ دقیقه
