import os
import json
import base64
import re
from datetime import datetime, timedelta
from pyrogram import Client

# تنظیمات
SESSION_NAME = "pyrogram_config_collector"
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_B64 = os.getenv("PYROGRAM_SESSION_B64")

if not all([API_ID, API_HASH, SESSION_B64]):
    raise Exception("❌ محیط اجرا فاقد API_ID یا API_HASH یا PYROGRAM_SESSION_B64 است.")

# بازیابی فایل session از secret
with open(f"{SESSION_NAME}.session", "wb") as f:
    f.write(base64.b64decode(SESSION_B64))

# فایل‌ها و مسیرها
CHANNEL_FILE = "channels.json"
OUTPUT_DIR = "output"
ALL_CONFIGS_FILE = "all_configs.txt"
CONFIG_PROTOCOLS = ["vmess://", "vless://", "ss://", "trojan://", "hy2://", "tuic://"]

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def extract_configs_from_text(text):
    found = []

    # لینک‌های مستقیم
    for proto in CONFIG_PROTOCOLS:
        found += re.findall(f"{proto}[^\s]+", text)

    # base64 های طولانی
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

# بررسی پیام‌های ۸ ساعت اخیر
cutoff_time = datetime.utcnow() - timedelta(hours=8)

# خواندن کانال‌ها
with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    channels = json.load(f)

all_configs = []

with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
    for channel in channels:
        print(f"📥 بررسی کانال: {channel}")
        try:
            messages = app.get_chat_history(channel, limit=30)
            configs = []

            for msg in messages:
                if msg.date < cutoff_time:
                    continue
                if msg.text:
                    configs += extract_configs_from_text(msg.text)

            configs = list(set(configs))

            if configs:
                all_configs += configs
                output_path = os.path.join(OUTPUT_DIR, channel.replace("@", "") + ".txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(configs))
                print(f"✅ {len(configs)} کانفیگ از {channel} ذخیره شد.")
            else:
                print(f"⚠️ کانفیگی در {channel} یافت نشد.")

        except Exception as e:
            print(f"❌ خطا در {channel}: {e}")

# نوشتن فایل all_configs.txt
if all_configs:
    with open(ALL_CONFIGS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(all_configs))))
    print(f"\n📦 فایل all_configs.txt با {len(all_configs)} کانفیگ ساخته شد.")
else:
    print("\n⚠️ هیچ کانفیگی برای all_configs.txt پیدا نشد.")
