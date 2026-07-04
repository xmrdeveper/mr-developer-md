#!/usr/bin/env python3
"""Entry point to run the Telegram pairing bot."""
import os
from dotenv import load_dotenv

load_dotenv()

from bot.telegram_bot import TelegramPairingBot

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print('TELEGRAM_TOKEN not set. Copy .env.example to .env and set TELEGRAM_TOKEN.')
        raise SystemExit(1)

    bot = TelegramPairingBot(token)
    bot.run()
