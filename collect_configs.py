import os
import base64

# بازسازی فایل session از secret
def restore_session():
    if not os.path.exists("pyrogram_config_collector.session"):
        session_data = os.getenv("PYROGRAM_SESSION_B64")
        if not session_data:
            raise Exception("PYROGRAM_SESSION_B64 not found in environment.")
        with open("pyrogram_config_collector.session", "wb") as f:
            f.write(base64.b64decode(session_data))

restore_session()
