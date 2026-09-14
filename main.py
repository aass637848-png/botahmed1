import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from bot.database.session import init_db
from bot.middlewares import DbSessionMiddleware, LoggingMiddleware
from bot.handlers import register_all_handlers
from bot.services.scheduler_service import (
    start_scheduler,
    shutdown_scheduler,
    load_pending_campaigns,
)


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s : %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


async def main() -> None:
    """Main application entrypoint."""
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Initializing Telegram Broadcast Bot...")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "SAMPLE_TOKEN":
        logger.error(
            "BOT_TOKEN is missing or set to default sample! "
            "Please create a .env file and provide a valid BOT_TOKEN."
        )
        sys.exit(1)

    # 1. Initialize Database Tables
    logger.info("Connecting to database and initializing schemas...")
    await init_db()
    logger.info("Database schemas verified.")

    # 2. Initialize Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Register Middlewares
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(DbSessionMiddleware())

    # 4. Register Handlers
    register_all_handlers(dp)

    # 5. Start APScheduler and restore pending jobs
    start_scheduler()
    await load_pending_campaigns(bot)

    # 6. Start Polling
    try:
        bot_user = await bot.get_me()
        logger.info(f"Bot started successfully as @{bot_user.username} (ID: {bot_user.id})")
        logger.info("Listening for updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Shutting down bot...")
        shutdown_scheduler()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot application terminated.")
