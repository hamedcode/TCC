import os
import json
import re
import base64
import datetime
from pyrogram import Client

def restore_session():
    if not os.path.exists("pyrogram_config_collector.session"):
        session_data = os.getenv("PYROGRAM_SESSION_B64")
        if not session_data:
            raise Exception("PYROGRAM_SESSION_B64 not found in environment.")
        with open("pyrogram_config_collector.session", "wb") as f:
            f.write(base64.b64decode(session_data))

restore_session()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "pyrogram_config_collector"

CONFIG_PATTERNS = [
    r"(vmess://[^\s]+)",
    r"(vless://[^\s]+)",
    r"(ss://[^\s]+)",
    r"(trojan://[^\s]+)",
    r"(tuic://[^\s]+)",
    r"(hy2://[^\s]+)",
]

def extract_configs(text):
    results = []
    for pattern in CONFIG_PATTERNS:
        results += re.findall(pattern, text)
    return results

def load_channels(path="channels.json"):
    with open(path, "r", encoding="utf-8") as f:
        return list(json.load(f).keys())

def is_today(msg_date):
    today = datetime.datetime.utcnow().date()
    return msg_date.date() == today

def main():
    if not os.path.exists("output"):
        os.makedirs("output")

    all_configs = set()
    channels = load_channels()
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

    with app:
        for ch in channels:
            try:
                print(f"Reading from {ch}")
                configs = []
                for msg in app.get_chat_history(ch, limit=100):
                    if not msg.date or not is_today(msg.date):
                        continue
                    if msg.text:
                        configs += extract_configs(msg.text)
                if configs:
                    filename = ch.replace("@", "") + ".txt"
                    with open(f"output/{filename}", "w", encoding="utf-8") as f:
                        f.write("\n".join(sorted(set(configs))))
                    print(f"Saved {len(configs)} configs to output/{filename}")
                    all_configs.update(configs)
                else:
                    print(f"No configs found today in {ch}")
            except Exception as e:
                print(f"Error reading {ch}: {e}")

    # ذخیره فایل کلی all_configs.txt
    with open("all_configs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(all_configs)))
    print(f"✅ Total {len(all_configs)} configs written to all_configs.txt")

if __name__ == "__main__":
    main()
