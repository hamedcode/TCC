import os
import requests
from datetime import datetime, timedelta

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

    # -------------------- اطلاعات بالا --------------------
    tehran_time = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = tehran_time.strftime("%Y/%m/%d - %H:%M")

    # تخمین پرچم از کلمات کلیدی در دامنه
    flags = []
    country_map = {
        "iran": "🇮🇷",
        "ir": "🇮🇷",
        "de": "🇩🇪",
        "us": "🇺🇸",
        "nl": "🇳🇱",
        "fr": "🇫🇷",
        "uk": "🇬🇧",
        "sg": "🇸🇬",
        "ca": "🇨🇦",
        "ru": "🇷🇺",
        "tr": "🇹🇷"
    }

    for cfg in batch:
        for key, flag in country_map.items():
            if key in cfg.lower():
                flags.append(flag)

    unique_flags = sorted(set(flags))

    # توضیح خلاصه
    summary = f"{len(batch)} کانفیگ جدید مناسب کاربران ایرانی با انواع vmess، ss، trojan"
    if unique_flags:
        summary += f"\nکشورها: {' '.join(unique_flags)}"

    # پیام نهایی با بلوک کپی
    message = f"""📦 کانفیگ‌های جدید - {time_str}
{summary}

