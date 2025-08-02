import os
import re
import time
import json
from pyrogram import Client
from pyrogram.errors import FloodWait, UsernameNotOccupied, UsernameInvalid

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_B64 = os.environ["PYROGRAM_SESSION_B64"]

CHANNELS_FILE = "channels.json"
OUTPUT_FOLDER = "output"
LAST_INDEX_FILE = "last_index.txt"
PEER_CACHE_FILE = "peer_ids_cache.json"


def extract_configs_from_text(text):
    config_patterns = [
        r"vmess://[a-zA-Z0-9+/=._\-]+",
        r"vless://[a-zA-Z0-9+/=._\-]+",
        r"trojan://[a-zA-Z0-9+/=._\-]+",
        r"ss://[a-zA-Z0-9+/=._\-]+",
        r"socks://[a-zA-Z0-9+/=._\-]+",
        r"hysteria://[a-zA-Z0-9+/=._\-]+",
    ]
    configs = []
    for pattern in config_patterns:
        configs.extend(re.findall(pattern, text))
    return configs


def save_configs_to_files(configs, output_folder):
    for i, config in enumerate(configs):
        with open(os.path.join(output_folder, f"config_{i+1}.txt"), "w", encoding="utf-8") as f:
            f.write(config)


def load_peer_id_cache():
    if os.path.exists(PEER_CACHE_FILE):
        with open(PEER_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_peer_id_cache(cache):
    with open(PEER_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_channels():
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_last_index():
    if os.path.exists(LAST_INDEX_FILE):
        with open(LAST_INDEX_FILE, "r") as f:
            return int(f.read().strip() or 0)
    return 0


def save_last_index(index):
    with open(LAST_INDEX_FILE, "w") as f:
        f.write(str(index))


def main():
    app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_B64)
    peer_cache = load_peer_id_cache()
    channels = get_channels()
    last_index = get_last_index()

    # حذف کامل پوشه output
    if os.path.exists(OUTPUT_FOLDER):
        for f in os.listdir(OUTPUT_FOLDER):
            try:
                os.remove(os.path.join(OUTPUT_FOLDER, f))
            except Exception as e:
                print(f"❌ خطا در حذف فایل {f}: {e}")
    else:
        os.makedirs(OUTPUT_FOLDER)

    all_configs = []

    with app:
        for i, username in enumerate(channels[last_index:], start=last_index):
            print(f"🔍 بررسی: @{username}")
            time.sleep(3)  # تأخیر بین درخواست‌ها

            try:
                if username in peer_cache:
                    peer = peer_cache[username]
                else:
                    peer = app.get_chat(username).id
                    peer_cache[username] = peer

                messages = app.get_history(peer, limit=15)
                found = False
                for message in messages:
                    text = message.text or message.caption
                    if not text:
                        continue
                    configs = extract_configs_from_text(text)
                    if configs:
                        all_configs.extend(configs)
                        save_configs_to_files(configs, OUTPUT_FOLDER)
                        found = True

                if not found:
                    print(f"⚠️ کانفیگی در @{username} یافت نشد.")

            except FloodWait as e:
                print(f"⏳ FLOOD_WAIT: {e.value} ثانیه - در حال صبر...")
                time.sleep(e.value)
            except (UsernameNotOccupied, UsernameInvalid):
                print(f"❌ کانال @{username} معتبر نیست.")
            except Exception as e:
                print(f"❌ خطا در @{username}: {e}")

            last_index = i + 1
            save_last_index(last_index)

    save_peer_id_cache(peer_cache)

    print(f"\n📦 تمام کانفیگ‌ها ذخیره شدند. ({len(all_configs)} عدد)")
    save_last_index(0)
    print("🔁 فایل last_index.txt ریست شد.")


if __name__ == "__main__":
    main()
