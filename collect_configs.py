import os
import json
import base64
import re
import shutil
from datetime import datetime, timedelta
from pyrogram import Client

# ⚙️ تنظیمات اصلی
SESSION_NAME = "pyrogram_config_collector"
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_B64 = os.getenv("PYROGRAM_SESSION_B64")

if not all([API_ID, API_HASH, SESSION_B64]):
    raise Exception("❌ محیط اجرا فاقد API_ID یا API_HASH یا PYROGRAM_SESSION_B64 است.")

# 🎯 بازسازی فایل session
with open(f"{SESSION_NAME}.session", "wb") as f:
    f.write(base64.b64decode(SESSION_B64))

# 📁 مسیر فایل‌ها
CHANNEL_FILE = "channels.json"
OUTPUT_DIR = "output"
ALL_CONFIGS_FILE = "all_configs.txt"
INDEX_FILE = "last_index.txt"
CONFIG_PROTOCOLS = ["vmess://", "vless://", "ss://", "trojan://", "hy2://", "tuic://"]

# 🧹 پاکسازی پوشه output
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)

# 🔍 استخراج کانفیگ‌ها
def extract_configs_from_text(text):
    found = []

    # 1. لینک‌های مستقیم
    for proto in CONFIG_PROTOCOLS:
        found += re.findall(f"{proto}[^\s]+", text)

    # 2. بررسی خطوط base64
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 20 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in line):
            try:
                decoded = base64.b64decode(line + "=" * (-len(line) % 4)).decode("utf-8")
                for proto in CONFIG_PROTOCOLS:
                    found += re.findall(f"{proto}[^\s]+", decoded)
            except:
                continue

    return list(set(found))

# 🕒 فقط پیام‌های ۸ ساعت اخیر
cutoff_time = datetime.utcnow() - timedelta(hours=8)

# 📥 بارگذاری لیست کانال‌ها
with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    channels = json.load(f)

all_configs = []

with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
    for channel in channels:
        print(f"📥 بررسی: {channel}")
        try:
            messages = app.get_chat_history(channel, limit=30)
            configs = []

            for msg in messages:
                if msg.date < cutoff_time:
                    continue
                content = msg.text or msg.caption
                if content:
                    configs += extract_configs_from_text(content)

            configs = list(set(configs))

            if configs:
                all_configs += configs
                output_path = os.path.join(OUTPUT_DIR, channel.replace("@", "").replace("-", "") + ".txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(configs))
                print(f"✅ {len(configs)} کانفیگ از {channel} ذخیره شد.")
            else:
                print(f"⚠️ کانفیگی در {channel} یافت نشد.")

        except Exception as e:
            print(f"❌ خطا در {channel}: {e}")

# ✏️ ساخت all_configs.txt و ریست فایل اندکس
if all_configs:
    with open(ALL_CONFIGS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(all_configs))))
    print(f"\n📦 فایل all_configs.txt با {len(all_configs)} کانفیگ ساخته شد.")

    # 🔄 ریست فایل last_index.txt
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write("0")
    print("🔁 فایل last_index.txt ریست شد.")
else:
    print("\n⚠️ هیچ کانفیگی برای all_configs.txt پیدا نشد.")
