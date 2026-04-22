#!/usr/bin/env python3
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from database import Database
from database.models import ConditionType
from monitoring import NonKYCClient, MarketMonitor
from notifications import NotificationHandler
from handlers import register_commands

logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", handlers=[logging.FileHandler(Config.LOG_FILE, encoding="utf-8", mode="a"), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

async def on_monitoring_data(data, db: Database, notifier: NotificationHandler):
    if not hasattr(data, 'events') or not data.events:
        return
    subscriptions = await db.get_active_subscriptions(data.symbol)
    for sub in subscriptions:
        for event in data.events:
            if _match_subscription(sub, event):
                await notifier.send_alert(user_id=sub.user_id, symbol=data.symbol, event=event, market_data=data)

def _match_subscription(sub, event: dict) -> bool:
    if sub.condition_type.value != event["type"]:
        return False
    if sub.direction and sub.direction != event.get("direction"):
        return False
    event_value = abs(event.get("value", 0))
    if sub.condition_type == ConditionType.PRICE_CHANGE_PERCENT:
        return event_value >= sub.condition_value
    elif sub.condition_type == ConditionType.PRICE_LEVEL_REACHED:
        return abs(event_value - sub.condition_value) < 0.0001
    elif sub.condition_type in (ConditionType.VOLUME_SPIKE, ConditionType.ORDERBOOK_DEPTH):
        return event_value >= sub.condition_value
    return False

async def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error("Config error: %s", e)
        sys.exit(1)

    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    db = Database(Config.DATABASE_URL)
    await db.init()
    client = NonKYCClient(Config.NONKYC_API_BASE_URL, Config.NONKYC_API_TIMEOUT)
    notifier = NotificationHandler(bot)
    register_commands(dp, db, notifier)

    monitor = MarketMonitor(client=client, symbol=Config.DEFAULT_SYMBOL, interval=Config.MONITOR_INTERVAL)
    
    # Fixed callback: proper async wrapper
    async def monitor_callback(data):
        await on_monitoring_data(data, db, notifier)
    monitor.subscribe(monitor_callback)

    @dp.startup()
    async def on_startup(bot: Bot):
        logger.info("Bot started: @%s", (await bot.get_me()).username)
        monitor.start()

    @dp.shutdown()
    async def on_shutdown(bot: Bot):
        logger.info("Bot stopping...")
        monitor.stop()
        await bot.session.close()

    logger.info("Starting polling...")
    await dp.start_polling(bot, dp=dp)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by Ctrl+C")
    except Exception as e:
        logger.critical("Critical error: %s", e, exc_info=True)
        sys.exit(1)
