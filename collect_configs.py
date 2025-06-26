import os
import json
import re
import base64
from pyrogram import Client

# 🟩 بازیابی فایل .session از Secret به صورت Base64
def restore_session():
    if not os.path.exists("pyrogram_config_collector.session"):
        session_data = os.getenv("PYROGRAM_SESSION_B64")
        if not session_data:
            raise Exception("PYROGRAM_SESSION_B64 not found in environment.")
        with open("pyrogram_config_collector.session", "wb") as f:
            f.write(base64.b64decode(session_data))

restore_session()

# خواندن API_ID و API_HASH از Secrets گیتهاب
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "pyrogram_config_collector"

# الگوهای کانفیگ قابل شناسایی
CONFIG_PATTERNS = [
    r"(vmess://[^\s]+)",
    r"(vless://[^\s]+)",
    r"(ss://[^\s]+)",
    r"(trojan://[^\s]+)",
    r"(tuic://[^\s]+)",
    r"(hy2://[^\s]+)",
]

# استخراج کانفیگ‌ها از متن
def extract_configs(text):
    results = []
    for pattern in CONFIG_PATTERNS:
        results += re.findall(pattern, text)
    return results

# خواندن لیست کانال‌ها از فایل JSON
def load_channels(path="channels.json"):
    with open(path, "r", encoding="utf-8") as f:
        return list(json.load(f).keys())

# اجرای اصلی
def main():
    if not os.path.exists("output"):
        os.makedirs("output")

    channels = load_channels()
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

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
    
