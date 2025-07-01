import os
import re
import json
import socket
import requests
import base64
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
import ipaddress

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID is not set.")

REPLACE_TAG = "@Config724"
IP_DB_PATH = "ip2country_full.json"

# بارگذاری دیتابیس IP به کشور
with open(IP_DB_PATH, "r") as f:
    ip_db = json.load(f)

country_names = {
    "IR": "Iran", "DE": "Germany", "US": "United States", "FR": "France",
    "SG": "Singapore", "NL": "Netherlands", "RU": "Russia", "CA": "Canada",
    "TR": "Turkey", "JP": "Japan", "GB": "United Kingdom", "HK": "Hong Kong",
    "CN": "China", "IN": "India", "KR": "South Korea", "AE": "UAE",
    "SE": "Sweden", "IT": "Italy", "ES": "Spain", "PL": "Poland", "RO": "Romania",
    "UA": "Ukraine", "BR": "Brazil", "ID": "Indonesia", "VN": "Vietnam",
    "MY": "Malaysia", "TH": "Thailand", "AU": "Australia", "KZ": "Kazakhstan",
    "FI": "Finland", "NO": "Norway", "DK": "Denmark", "CH": "Switzerland",
    "BE": "Belgium", "AT": "Austria", "CZ": "Czech Republic", "SK": "Slovakia",
    "HU": "Hungary", "GR": "Greece", "BG": "Bulgaria", "IL": "Israel",
    "SA": "Saudi Arabia", "PK": "Pakistan", "AF": "Afghanistan", "IQ": "Iraq",
    "SY": "Syria", "YE": "Yemen", "MA": "Morocco", "EG": "Egypt", "ZA": "South Africa"
}

def country_code_to_flag(code):
    return ''.join([chr(0x1F1E6 + ord(c.upper()) - 65) for c in code]) if code != "ZZ" else "🏳️"

def get_country_code(ip):
    try:
        ip_addr = ipaddress.IPv4Address(ip)
        for code, ranges in ip_db.items():
            for net in ranges:
                if ip_addr in ipaddress.IPv4Network(net):
                    return code
    except:
        pass
    return "ZZ"

def build_tag(ip):
    code = get_country_code(ip)
    name = country_names.get(code, "Unknown")
    flag = country_code_to_flag(code)
    date = datetime.now().strftime("%m/%d")
    return f"{flag} {name} - {date} {REPLACE_TAG}"

def resolve_ip(host):
    try:
        return socket.gethostbyname(host)
    except:
        return host

def update_tag(cfg):
    if cfg.startswith("vmess://"):
        try:
            raw = cfg.replace("vmess://", "")
            padded = raw + '=' * (-len(raw) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode()).decode()
            data = json.loads(decoded)
            host = data.get("add", "")
            ip = resolve_ip(host)
            data["ps"] = build_tag(ip)
            encoded = base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':')).encode()).decode().rstrip("=")
            return "vmess://" + encoded
        except:
            return cfg
    elif any(cfg.startswith(proto) for proto in ["vless://", "trojan://", "ss://", "hy2://", "tuic://"]):
        try:
            parsed = urlparse(cfg)
            host = parsed.hostname or "8.8.8.8"
            ip = resolve_ip(host)
            new_tag = build_tag(ip)
            new_cfg = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                new_tag
            ))
            return new_cfg
        except:
            return cfg
    else:
        return cfg

# خواندن کانفیگ‌ها
with open("all_configs.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# خواندن اندیس قبلی
last_index = 0
if os.path.exists("last_index.txt"):
    with open("last_index.txt", "r") as idx_file:
        for line in idx_file:
            if line.strip().isdigit():
                last_index = int(line.strip())
                break

batch_size = 5
end_index = min(last_index + batch_size, len(lines))
if last_index >= len(lines):
    print("✅ همه کانفیگ‌ها ارسال شده.")
    exit(0)

batch = lines[last_index:end_index]
cleaned_batch = [update_tag(cfg) for cfg in batch]

# زمان تهران
tehran_time = datetime.utcnow() + timedelta(hours=3, minutes=30)
time_str = tehran_time.strftime("%Y/%m/%d - %H:%M")

# آمار
proto_set, port_set, flag_set = set(), set(), set()
for cfg in batch:
    proto_set.add(cfg.split("://")[0])
    try:
        parsed = urlparse(cfg)
        if parsed.port:
            port_set.add(str(parsed.port))
        host = parsed.hostname or ""
        code = get_country_code(resolve_ip(host))
        flag_set.add(country_code_to_flag(code))
    except:
        continue

summary = f"{len(cleaned_batch)} کانفیگ جدید با پروتکل‌های {'، '.join(sorted(proto_set))}"
if port_set:
    summary += f" و پورت‌های {'، '.join(sorted(port_set))}"
if flag_set:
    summary += f"\n🌍 کشورها: {' '.join(sorted(flag_set))}"

configs_text = "\n".join(cleaned_batch)
message = (
    f"📦 کانفیگ‌های جدید - {time_str}\n\n"
    f"{summary}\n\n"
    f"```text\n{configs_text}\n```\n\n"
    f"📡 برای دریافت بیشتر: {CHANNEL_ID}"
)

res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
    "chat_id": CHANNEL_ID,
    "text": message,
    "parse_mode": "Markdown"
})

if res.status_code != 200:
    print(f"❌ ارسال ناموفق: {res.text}")
else:
    print("✅ پیام ارسال شد.")

# ذخیره اندیس جدید
with open("last_index.txt", "w") as f:
    f.write(str(end_index))
