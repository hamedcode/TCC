import os
import json
import time
import re
import shutil
from pyrogram import Client
from pyrogram.errors import FloodWait, PeerIdInvalid

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_B64 = os.environ["PYROGRAM_SESSION_B64"]

CHANNELS = [
    "redfree8", "bluevpn11", "avaalvpn", "configms", "befreewithus",
    "bombvpnn", "configt", "ehsawn8", "elfv2ray", "evay_vpn", "expressvpn_420",
    "configv2rayforfree", "customvpnserver", "CHv2raynp", "freeland8", 
    "free_vpn02", "free_serverir", "filterk0sh", "chanel_v2ray_2", 
    "-1002045040453", "ezaccess1", "Achavpn"
]

OUTPUT_DIR = "output"
LAST_INDEX_FILE = "last_index.txt"
PEER_CACHE_FILE = "peer_ids_cache.json"
CONFIG_PATTERN = r"(vmess|vless|trojan|ss|socks|hysteria)://[^\s]+"


def load_cache():
    if os.path.exists(PEER_CACHE_FILE):
        with open(PEER_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(PEER_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_last_index():
    if os.path.exists(LAST_INDEX_FILE):
        return int(open(LAST_INDEX_FILE).read().strip())
    return 0

def reset_last_index():
    with open(LAST_INDEX_FILE, "w") as f:
        f.write("0")
    print("🔁 فایل last_index.txt ریست شد.")


def extract_configs(text):
    return re.findall(CONFIG_PATTERN, text)


def main():
    print("📥 اتصال به کلاینت...")
    app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_B64)
    
    with app:
        print("🧹 حذف کامل پوشه output/")
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        peer_cache = load_cache()
        all_configs = []
        
        for username in CHANNELS:
            print(f"🔍 بررسی: @{username}")
            peer_id = peer_cache.get(username)
            
            try:
                if not peer_id:
                    chat = app.get_chat(username)
                    peer_id = chat.id
                    peer_cache[username] = peer_id
                    save_cache(peer_cache)
                    print(f"✅ آیدی @{username} ذخیره شد: {peer_id}")
                    time.sleep(5)  # delay برای جلوگیری از Flood

                messages = app.get_chat_history(peer_id, limit=10)
                found = False

                for msg in messages:
                    content = msg.text or msg.caption or ""
                    configs = extract_configs(content)
                    if configs:
                        found = True
                        for cfg in configs:
                            all_configs.append(cfg)

                if not found:
                    print(f"⚠️ کانفیگی در @{username} یافت نشد.")

            except FloodWait as e:
                print(f"⏳ FloodWait @{username}: {e.value} ثانیه انتظار")
                time.sleep(e.value + 5)
            except PeerIdInvalid:
                print(f"❌ خطا در @{username}: Peer ID invalid یا هنوز resolve نشده")
            except Exception as ex:
                print(f"❌ خطای ناشناخته در @{username}: {ex}")

    # ذخیره همه کانفیگ‌ها
    if all_configs:
        with open(os.path.join(OUTPUT_DIR, "all_configs.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(all_configs))
        print(f"📦 ذخیره {len(all_configs)} کانفیگ در all_configs.txt")
    else:
        print("📭 هیچ کانفیگی یافت نشد.")

    reset_last_index()


if __name__ == "__main__":
    main()
