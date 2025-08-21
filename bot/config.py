# bot/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # подхватит .env из корня проекта

TOKEN = os.getenv("BOT_TOKEN")  # берём из .env
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "bot_data.sqlite3")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавь его в .env")
