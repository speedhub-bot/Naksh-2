# Naksh-2

Telegram bot for authorized, own-account Minecraft/Microsoft account checks.

## Setup

1. Install dependencies:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Configure required environment variables:

   ```bash
   export BOT_TOKEN="your-telegram-bot-token"
   export ADMIN_ID="your-telegram-user-id"
   ```

   Optional safety limits:

   ```bash
   export MAX_CONCURRENT_CHECKS=1
   export MAX_UPLOAD_ACCOUNTS=1
   ```

3. Run the bot:

   ```bash
   python3 main.py
   ```

## Notes

- Do not commit `.env`, database files, or result files.
- Proxy uploads are disabled.
- Uploads are limited to one own account by default.
- Result files and hit notifications do not echo account passwords.
