import os
import base64
from pyrogram import Client

# اطلاعات احراز هویت
SESSION_NAME = "pyrogram_config_collector"
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_B64 = os.getenv("PYROGRAM_SESSION_B64")

# ساخت فایل session از secret
with open(f"{SESSION_NAME}.session", "wb") as f:
    f.write(base64.b64decode(SESSION_B64))

# اجرای کلاینت Pyrogram و گرفتن پیام
with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
    msg = app.get_messages("@Achavpn", 10699)

    print("🧾 مشخصات کامل پیام:")
    print(msg)

    print("\n📨 TEXT:", msg.text)
    print("📨 CAPTION:", msg.caption)
    if msg.document:
        print("📄 فایل دارد:", msg.document.file_name, "-", msg.document.mime_type)
    elif msg.photo:
        print("🖼 عکس دارد.")
    else:
        print("📭 پیام بدون مدیا یا فایل.")
