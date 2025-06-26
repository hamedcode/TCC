# Telegram Config Collector (via Pyrogram + GitHub Actions)

این پروژه کانفیگ‌های پروکسی (vmess, vless, ss, trojan و ...) را از کانال‌های عمومی تلگرام استخراج می‌کند.

## مراحل راه‌اندازی:

1. مقادیر زیر را از [https://my.telegram.org](https://my.telegram.org) دریافت کن:
   - API_ID
   - API_HASH
2. یک بات از [@BotFather](https://t.me/BotFather) بساز و توکنش رو بگیر.
3. این مقادیر را در بخش:
   **Settings → Secrets and Variables → Actions → New Repository Secret** وارد کن:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`

## اجرا در GitHub Actions

- این پروژه هر ۸ ساعت اجرا شده و آخرین کانفیگ‌ها را در پوشه `output/` به‌روزرسانی می‌کند.
- برای اجرای دستی نیز از تب **Actions** استفاده کنید.

## خروجی

در پوشه `output/` برای هر کانال یک فایل `.txt` شامل کانفیگ‌ها ذخیره می‌شود.
