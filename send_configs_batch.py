import os
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

# خواندن اندیس آخرین ارسال
last_index = 0
if os.path.exists(index_file):
    with open(index_file, "r") as idx_file:
        for line in idx_file:
            if line.strip().isdigit():
                last_index = int(line.strip())
                break

batch_size = 5
end_index = min(last_index + batch_size, len(lines))

if last_index >= len(lines):
    print("✅ همه کانفیگ‌ها قبلاً ارسال شده.")
else:
    batch = lines[last_index:end_index]

    # ساخت پیام با قالب مناسب
    message_lines = [
        "🚀 ۵ کانفیگ جدید از تلگرام امروز:",
        "",
    ]
    for i, cfg in enumerate(batch, start=1):
        message_lines.append(f"{i}. `{cfg}`")

    message = "\n".join(message_lines)

    # ارسال به تلگرام با Markdown
    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    })

    if res.status_code != 200:
        print(f"❌ ارسال با خطا مواجه شد: {res.text}")
    else:
        print("✅ پیام با موفقیت ارسال شد.")

    # ذخیره اندیس جدید
    with open(index_file, "w") as idx_file:
        idx_file.write(str(end_index))

    print(f"✅ اندیس جدید: {end_index}")
