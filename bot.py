"""bot.py — Application entry point.
Initialises DB, seeds barbers, registers routers, starts scheduler, and polls.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, BARBERS
from database.db import init_db, seed_barbers
from handlers import user_handlers, admin_handlers
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s – %(message)s",
)

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    await init_db()
    await seed_barbers(BARBERS)
    logger.info("Database initialised and barbers seeded.")

    info = await bot.get_me()
    logger.info(f"Bot started: @{info.username}")


async def on_shutdown(scheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Bot stopped.")


async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Routers
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    # Startup hook
    dp.startup.register(lambda: on_startup(bot))

    # Scheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Reminder scheduler started.")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown(scheduler)
        await bot.session.close()


if name == "__main__":
    asyncio.run(main())
