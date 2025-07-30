import os
import requests
import json
import base64
import datetime
import re
import geoip2.database
from collections import Counter

# ==== تنظیمات ====
GEOIP_DB_PATH = "GeoLite2-Country.mmdb"
ALL_CONFIGS_PATH = "all_configs.txt"
CHANNEL_ID = "@Config724"
BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
SEND_LIMIT = 10  # تعداد کانفیگ برای هر بار ارسال
# =================

def extract_domain(config):
    ip_pattern = re.compile(r'"address"\s*:\s*"([^"]+)"')
    sni_pattern = re.compile(r'"sni"\s*:\s*"([^"]+)"')
    host_pattern = re.compile(r'"host"\s*:\s*"([^"]+)"')
    domain_pattern = re.compile(r'@([\w.-]+)')

    for pattern in [ip_pattern, sni_pattern, host_pattern, domain_pattern]:
        match = pattern.search(config)
        if match:
            return match.group(1)
    return None

def get_country_flag(domain, reader):
    if not domain:
        return "🏳️"
    try:
        ip = domain
        if not re.match(r"\d+\.\d+\.\d+\.\d+", domain):
            ip = socket.gethostbyname(domain)
        response = reader.country(ip)
        country_code = response.country.iso_code or "UN"
        return chr(0x1F1E6 + (ord(country_code[0]) - 65)) + chr(0x1F1E6 + (ord(country_code[1]) - 65))
    except:
        return "🏳️"

def update_remark(config, flag):
    today = datetime.datetime.now().strftime("%m/%d")
    return re.sub(r'remark":\s*"([^"]*)"', f'remark": "{flag} | {today} 🌀{CHANNEL_ID}"', config)

def summarize_configs(configs):
    protocols = []
    ports = []

    for config in configs:
        if "vmess://" in config:
            protocols.append("vmess")
        elif "vless://" in config:
            protocols.append("vless")
        elif "ss://" in config:
            protocols.append("ss")
        elif "trojan://" in config:
            protocols.append("trojan")
        elif "socks" in config:
            protocols.append("socks")
        elif "hysteria" in config.lower():
            protocols.append("hysteria")
        else:
            protocols.append("other")

        port_match = re.search(r'"port"\s*:\s*"(\d+)"', config)
        if port_match:
            ports.append(port_match.group(1))

    proto_summary = " | ".join(f"{k}:{v}" for k, v in Counter(protocols).items())
    port_summary = " | ".join(f"{k}:{v}" for k, v in Counter(ports).items())

    return f"🌐 پروتکل‌ها: {proto_summary}\n🔢 پورت‌ها: {port_summary}"

def send_to_telegram(configs, summary_text):
    config_text = "\n\n".join(configs)
    message = (
        f"🔥 {len(configs)} کانفیگ جدید آماده اتصال\n"
        f"{summary_text}\n\n"
        f"```text\n{config_text}\n```\n\n"
        f"🚨 به دلیل اختلال شدید در اینترنت کشور، اتصال و کیفیت کانفیگ‌ها در هر منطقه فرق دارد\n"
        f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
    )

    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(TELEGRAM_API, json=payload)
    print("ارسال به تلگرام:", response.status_code)

def save_sent_configs(configs):
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"sent_{today}.txt"

    # حذف فایل روز قبل
    for file in os.listdir("."):
        if file.startswith("sent_") and file.endswith(".txt") and file != filename:
            os.remove(file)

    with open(filename, "a", encoding="utf-8") as f:
        for config in configs:
            f.write(config + "\n\n")

# === اجرای اصلی ===
if not os.path.exists(ALL_CONFIGS_PATH):
    print("فایل all_configs.txt پیدا نشد.")
    exit()

with open(ALL_CONFIGS_PATH, "r", encoding="utf-8") as f:
    raw_configs = [c.strip() for c in f.read().split("\n\n") if c.strip()]

raw_configs = raw_configs[:SEND_LIMIT]

reader = geoip2.database.Reader(GEOIP_DB_PATH)
processed_configs = []
flags = []

for config in raw_configs:
    domain = extract_domain(config)
    flag = get_country_flag(domain, reader)
    flags.append(flag)
    new_config = update_remark(config, flag)
    processed_configs.append(new_config)

reader.close()

summary = summarize_configs(processed_configs)
send_to_telegram(processed_configs, summary)
save_sent_configs(processed_configs)
