import os
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID is not set in secrets")

all_file = "all_configs.txt"
index_file = "last_index.txt"

# خواندن همه کانفیگ‌ها
with open(all_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

# اندیس قبلی
last_index = 0
if os.path.exists(index_file):
    with open(index_file, "r") as idx_file:
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

# زمان تهران
tehran_time = datetime.utcnow() + timedelta(hours=3, minutes=30)
time_str = tehran_time.strftime("%Y/%m/%d - %H:%M")

# لیست پرچم‌ها
country_flags = {
    "ir": "🇮🇷", "iran": "🇮🇷",
    "de": "🇩🇪", "germany": "🇩🇪",
    "us": "🇺🇸", "usa": "🇺🇸", "america": "🇺🇸",
    "nl": "🇳🇱", "netherlands": "🇳🇱",
    "fr": "🇫🇷", "france": "🇫🇷",
    "uk": "🇬🇧", "gb": "🇬🇧", "london": "🇬🇧",
    "ru": "🇷🇺", "russia": "🇷🇺",
    "sg": "🇸🇬", "singapore": "🇸🇬",
    "ca": "🇨🇦", "canada": "🇨🇦",
    "tr": "🇹🇷", "turkey": "🇹🇷",
    "jp": "🇯🇵", "japan": "🇯🇵",
    "kr": "🇰🇷", "korea": "🇰🇷",
    "hk": "🇭🇰", "hongkong": "🇭🇰",
    "in": "🇮🇳", "india": "🇮🇳",
    "br": "🇧🇷", "brazil": "🇧🇷",
    "th": "🇹🇭", "thailand": "🇹🇭",
    "vn": "🇻🇳", "vietnam": "🇻🇳",
    "sa": "🇸🇦", "ksa": "🇸🇦", "arabia": "🇸🇦",
    "sy": "🇸🇾", "syria": "🇸🇾"
}

flags = []
protocols = set()
ports = set()

for cfg in batch:
    # پروتکل
    proto = cfg.split("://")[0]
    protocols.add(proto)

    # پورت
    try:
        parsed = urlparse(cfg)
        host_port = parsed.netloc.split("@")[-1]
        if ':' in host_port:
            ports.add(host_port.split(":")[-1])
    except:
        pass

    # پرچم
    for key, flag in country_flags.items():
        if key in cfg.lower():
            flags.append(flag)

# نمایش اطلاعات
flags = sorted(set(flags))
protocol_str = "، ".join(sorted(protocols))
port_str = "، ".join(sorted(ports))

summary = f"{len(batch)} کانفیگ جدید با پروتکل‌های {protocol_str}"
if port_str:
    summary += f" و پورت‌های {port_str}"
if flags:
    summary += f"\n🌍 کشورها: {' '.join(flags)}"

# ساخت پیام نهایی
configs_text = "\n".join(batch)
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

with open(index_file, "w") as idx_file:
    idx_file.write(str(end_index))

print(f"✅ اندیس جدید: {end_index}")
