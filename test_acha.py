with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
    msg = app.get_messages("@Achavpn", 10699)
    content = msg.text or msg.caption
    print("📩 محتوای پیام 10699:\n", content)
