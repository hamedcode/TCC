import os
import json
import base64
import re
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

# 📌 نام فایل سشن و دریافت آن از Secret
SESSION_FILE = "pyrogram_config_collector"
B64_ENV_VAR = os.getenv("PYROGRAM_SESSION_B64")

if B64_ENV_VAR:
    with open(f"{SESSION_FILE}.session", "wb") as f:
        f.write(base64.b64decode(B64_ENV_VAR))
else:
    raise Exception("❌ Secret 'PYROGRAM_SESSION_B64' not found!")

# ⚙️ اطلاعات API
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# 📁 مسیر فایل‌ها
CHANNEL_FILE = "channels.json"
OUTPUT_DIR = "output"
ALL_CONFIGS_FILE = "all_configs.txt"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

CONFIG_PROTOCOLS = ["vmess://", "vless://", "ss://", "trojan://", "hy2://", "tuic://"]

def extract_configs_from_text(text):
    found = []

    # 1. لینک‌های مستقیم
    for proto in CONFIG_PROTOCOLS:
        found += re.findall(f"{proto}[^\s]+", text)

    # 2. base64 های طولانی
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

# 🕒 پیام‌های ۸ ساعت گذشته
cutoff_time = datetime.utcnow() - timedelta(hours=8)

# 📥 خواندن کانال‌ها
with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    channels = json.load(f)

all_configs = []

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

            configs = list(set(configs))
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

# ✏️ ذخیره فایل کلی
if all_configs:
    with open(ALL_CONFIGS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(all_configs))))
    print(f"\n📦 فایل all_configs.txt با {len(all_configs)} کانفیگ ساخته شد.")
else:
    print("\n⚠️ هیچ کانفیگی برای ساخت all_configs.txt پیدا نشد.")
