from pyrogram import Client
import re
import json
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

SESSION_NAME = "bot_session"

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

def main():
    if not os.path.exists("output"):
        os.makedirs("output")

    channels = load_channels()
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    with app:
        for ch in channels:
            try:
                print(f"Reading from {ch}")
                configs = []
                for msg in app.get_chat_history(ch, limit=100):
                    if msg.text:
                        configs += extract_configs(msg.text)
                if configs:
                    filename = ch.replace("@", "") + ".txt"
                    with open(f"output/{filename}", "w", encoding="utf-8") as f:
                        f.write("\n".join(sorted(set(configs))))
                    print(f"Saved {len(configs)} configs from {ch}")
                else:
                    print(f"No configs found in {ch}")
            except Exception as e:
                print(f"Error reading {ch}: {e}")

if __name__ == "__main__":
    main()
