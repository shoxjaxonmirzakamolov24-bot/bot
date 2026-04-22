"""
Booking business logic: slot generation, availability checks.
"""
from datetime import datetime, date, timedelta
from config import WORK_START_HOUR, WORK_END_HOUR, SLOT_DURATION_MINUTES, CALENDAR_DAYS_AHEAD
from database.db import get_booked_slots


def generate_all_slots() -> list[str]:
    """Generate every 30-min slot in a working day as 'HH:MM'."""
    slots = []
    current = datetime.strptime(f"{WORK_START_HOUR:02d}:00", "%H:%M")
    end = datetime.strptime(f"{WORK_END_HOUR:02d}:00", "%H:%M")
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=SLOT_DURATION_MINUTES)
    return slots


def get_available_dates() -> list[date]:
    """Return list of calendar dates (today … +CALENDAR_DAYS_AHEAD)."""
    today = date.today()
    return [today + timedelta(days=i) for i in range(CALENDAR_DAYS_AHEAD)]


async def get_available_slots(barber_id: int, booking_date: str) -> list[str]:
    """
    Returns time slots that are still free for the given barber and date.
    Past slots on today's date are automatically excluded.
    """
    booked = await get_booked_slots(barber_id, booking_date)
    all_slots = generate_all_slots()

    # If the date is today, strip past slots (add 30min buffer)
    today_str = date.today().isoformat()
    if booking_date == today_str:
        now = datetime.now()
        cutoff = (now + timedelta(minutes=30)).strftime("%H:%M")
        all_slots = [s for s in all_slots if s >= cutoff]

    return [s for s in all_slots if s not in booked]
