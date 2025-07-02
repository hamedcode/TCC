import os
import json
import base64
import re
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

# تنظیمات از محیط (API_ID, API_HASH)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_FILE = "session"

# فایل لیست کانال‌ها
CHANNEL_FILE = "channels.json"
OUTPUT_DIR = "output"
ALL_CONFIGS_FILE = "all_configs.txt"

# بررسی و ساخت پوشه خروجی
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# پروتکل‌های قابل شناسایی
CONFIG_PROTOCOLS = ["vmess://", "vless://", "ss://", "trojan://", "hy2://", "tuic://"]

def extract_configs_from_text(text):
    found = []

    # 1. لینک‌های مستقیم
    for proto in CONFIG_PROTOCOLS:
        found += re.findall(f"{proto}[^\s]+", text)

    # 2. رشته‌های base64 بلند
    base64_candidates = re.findall(r"[A-Za-z0-9+/=]{200,}", text)
    for b64 in base64_candidates:
        try:
            padded = b64 + "=" * (-len(b64) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")
            for proto in CONFIG_PROTOCOLS:
                found += re.findall(f"{proto}[^\s]+", decoded)
        except:
            continue

    return list(set(found))

# تاریخ امروز برای فیلتر پیام‌ها (۸ ساعت اخیر)
cutoff_time = datetime.utcnow() - timedelta(hours=8)

# خواندن لیست کانال‌ها
with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    channels = json.load(f)

# لیست نهایی همه کانفیگ‌ها
all_configs = []

# شروع کلاینت
with TelegramClient(SESSION_FILE, API_ID, API_HASH) as client:
    for channel, _ in channels.items():
        print(f"📥 خواندن از {channel}")
        try:
            result = client(GetHistoryRequest(
                peer=channel,
                limit=30,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))

            configs = []
            for msg in result.messages:
                if msg.date < cutoff_time:
                    continue
                text = msg.message or ""
                configs += extract_configs_from_text(text)

            configs = list(set(configs))  # حذف تکراری
            if configs:
                all_configs += configs
                output_file = os.path.join(OUTPUT_DIR, channel.replace("@", "") + ".txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(configs))
                print(f"✅ {len(configs)} کانفیگ ذخیره شد.")
            else:
                print("⚠️ کانفیگی یافت نشد.")

        except Exception as e:
            print(f"❌ خطا در خواندن {channel}: {e}")

# نوشتن all_configs.txt
if all_configs:
    with open(ALL_CONFIGS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(all_configs))))
    print(f"\n📦 فایل نهایی all_configs.txt با {len(all_configs)} کانفیگ ساخته شد.")
else:
    print("\n⚠️ هیچ کانفیگی برای ساخت all_configs.txt پیدا نشد.")
