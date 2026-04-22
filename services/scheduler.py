"""
APScheduler-based background reminder system.
Runs every 15 minutes, checks for upcoming bookings.
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database.db import get_upcoming_unreminded, mark_reminder_sent

logger = logging.getLogger(__name__)


async def send_reminders(bot: Bot) -> None:
    """Check and dispatch appointment reminders."""
    try:
        bookings = await get_upcoming_unreminded()
        for booking in bookings:
            try:
                text = (
                    f"⏰ <b>Eslatma!</b>\n\n"
                    f"Sizning bandlovingiz 2 soatdan keyin!\n\n"
                    f"📅 Sana: <b>{booking['booking_date']}</b>\n"
                    f"🕐 Vaqt: <b>{booking['time_slot']}</b>\n"
                    f"💈 Xizmat: <b>{booking['service_name']}</b>\n\n"
                    f"Barbershop Elite sizni kutmoqda! ✂️"
                )
                await bot.send_message(
                    chat_id=booking["telegram_id"],
                    text=text,
                    parse_mode="HTML"
                )
                await mark_reminder_sent(booking["id"])
                logger.info(f"Reminder sent for booking #{booking['id']}")
            except Exception as e:
                logger.warning(f"Failed to send reminder for booking #{booking['id']}: {e}")
    except Exception as e:
        logger.error(f"Reminder scheduler error: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Create and configure the background scheduler."""
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(
        send_reminders,
        trigger="interval",
        minutes=15,
        args=[bot],
        id="reminder_job",
        replace_existing=True,
    )
    return scheduler
