import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import (
    BOT_TOKEN, BARBERS, WEBHOOK_URL, WEBHOOK_PATH, 
    WEB_SERVER_HOST, WEB_SERVER_PORT
)
from database.db import init_db, seed_barbers
from handlers import user_handlers, admin_handlers
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Tasks to run when the bot starts."""
    await init_db()
    await seed_barbers(BARBERS)
    logger.info("Database initialised and barbers seeded.")

    # Set webhook
    await bot.set_webhook(WEBHOOK_URL)
    info = await bot.get_me()
    logger.info(f"Bot started: @{info.username}")
    logger.info(f"Webhook set to: {WEBHOOK_URL}")


async def on_shutdown(scheduler) -> None:
    """Graceful shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Bot stopped.")


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set! Copy .env.example → .env and fill it in.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ── Register routers ──────────────────────────────────────────────────────
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    # ── Background scheduler ──────────────────────────────────────────────────
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Reminder scheduler started.")

    # ── Lifecycle hooks ───────────────────────────────────────────────────────
    dp.startup.register(on_startup)

    # ── Webhook Setup ────────────────────────────────────────────────────────
    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    # Register webhook handler on application
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Mount dispatcher startup and shutdown hooks to aiohttp app
    setup_application(app, dp, bot=bot)

    # Run web server
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    main()
