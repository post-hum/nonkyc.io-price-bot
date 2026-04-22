import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    # Важно: базовый URL должен включать /api/v2
    NONKYC_API_BASE_URL = os.getenv("NONKYC_API_BASE_URL", "https://api.nonkyc.io/api/v2").rstrip("/")
    NONKYC_API_TIMEOUT = int(os.getenv("NONKYC_API_TIMEOUT", "10"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "60"))
    DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "XLA/USDT").replace("/", "_").upper()
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")

    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not cls.NONKYC_API_BASE_URL.endswith("/api/v2"):
            # Авто-фикс: добавляем /api/v2 если забыли
            cls.NONKYC_API_BASE_URL = cls.NONKYC_API_BASE_URL.rstrip("/") + "/api/v2"
        return True

Path(Config.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
