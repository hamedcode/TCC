import os
import json
import base64
import requests
from datetime import datetime
import geoip2.database

# 🟢 کانفیگ‌ها
API_URL = os.environ["API_URL"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
DAILY_CONFIG_FILE = "daily_configs.txt"
GEOIP_DB_PATH = "GeoLite2-City.mmdb"

def get_country_emoji(ip):
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.city(ip)
            country_code = response.country.iso_code
            if not country_code:
                return "🏳️"
            return "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in country_code.upper())
    except Exception:
        return "🏳️"

def extract_ip_from_config(config_line):
    if "vless://" in config_line or "vmess://" in config_line:
        parts = config_line.split("@")
        if len(parts) > 1:
            ip_port = parts[1].split("?")[0]
            return ip_port.split(":")[0]
    elif "trojan://" in config_line:
        parts = config_line.split("@")
        if len(parts) > 1:
            ip_port = parts[1].split("?")[0]
            return ip_port.split(":")[0]
    elif "ss://" in config_line:
        try:
            from urllib.parse import unquote
            raw = config_line.split("ss://")[1].split("#")[0]
            decoded = base64.urlsafe_b64decode(raw + '==').decode()
            ip_port = decoded.split("@")[1]
            return ip_port.split(":")[0]
        except:
            return ""
    return ""

def update_remarks(config):
    ip = extract_ip_from_config(config)
    country = get_country_emoji(ip)
    today = datetime.now().strftime("%m/%d")
    return f"{country} {today} @Config724"

def update_config_remarks(config):
    try:
        if '#' in config:
            config, remark = config.split('#', 1)
            new_remark = update_remarks(config)
            return f"{config}#{new_remark}"
        else:
            return f"{config}#{update_remarks(config)}"
    except Exception:
        return config

def read_configs():
    configs = []
    for root, _, files in os.walk("output"):
        for file in files:
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        configs.append(line)
    return configs

def reset_daily_file_if_needed():
    today_str = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(DAILY_CONFIG_FILE):
        with open(DAILY_CONFIG_FILE, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if not first_line.endswith(today_str):
                os.remove(DAILY_CONFIG_FILE)

def append_to_daily_file(text):
    today_str = datetime.now().strftime("%Y-%m-%d")
    header = f"# کانفیگ‌های ارسال‌شده در {today_str}"
    if not os.path.exists(DAILY_CONFIG_FILE):
        with open(DAILY_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(header + "\n\n")
    with open(DAILY_CONFIG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n\n")

def send_to_telegram(text):
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(f"{API_URL}/sendMessage", json=payload)
    print(f"Telegram response: {response.text}")

if __name__ == "__main__":
    reset_daily_file_if_needed()
    configs = read_configs()
    if not configs:
        print("⚠️ No configs to send.")
        exit()

    # فقط ۱۰ تای آخر
    latest_configs = configs[-10:]
    updated = [update_config_remarks(cfg) for cfg in latest_configs]
    configs_text = "\n".join(updated)

    # ذخیره در فایل روزانه
    append_to_daily_file(configs_text)

    # ارسال به تلگرام
    final_message = (
        f"<pre>\n{configs_text}\n</pre>\n\n"
        f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ‌ها توی هر منطقه فرق داره.\n"
        f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
    )
    send_to_telegram(final_message)
