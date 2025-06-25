# Telegram Configs Collector

این پروژه به صورت ساده کانفیگ‌های پروکسی (vmess, vless, trojan, ss, tuic, hy2) را از لیست کانال‌های تلگرام در فایل `channels.json` جمع‌آوری کرده و خروجی همه کانفیگ‌ها را در `output.txt` ذخیره می‌کند.

## شروع به کار

1. ایجاد محیط مجازی (اختیاری):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. نصب پیش‌نیازها:
   ```bash
   pip install -r requirements.txt
   ```
3. اجرای اسکریپت:
   ```bash
   python fetch_configs.py
   ```
4. کانفیگ‌های جمع‌آوری شده در `output.txt` ذخیره می‌شوند.

## فایل‌ها

- **channels.json**: لیست کانال‌های تلگرام و پروتکل‌های مدنظر.
- **fetch_configs.py**: اسکریپت اصلی برای جمع‌آوری کانفیگ‌ها.
- **requirements.txt**: وابستگی‌های پروژه.
- **output.txt**: خروجی کانفیگ‌های جمع‌آوری شده (در اجرا ایجاد می‌شود).

## ویرایش لیست کانال‌ها

برای اضافه کردن یا حذف کانال‌ها، فایل `channels.json` را ویرایش کنید.
