"""
Keyboards and inline keyboards for regular users.
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import SERVICES, BARBERS
from services.booking_service import get_available_dates


# ── Main menu ─────────────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Joy band qilish"),
             KeyboardButton(text="📋 Mening bandlovlarim")],
            [KeyboardButton(text="⭐ Baxolash"),
             KeyboardButton(text="📍 Manzil")],
            [KeyboardButton(text="ℹ️ Ma'lumot")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Quyidagi menüdan tanlang..."
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


# ── Services ──────────────────────────────────────────────────────────────────

def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for svc in SERVICES:
        builder.button(
            text=f"{svc['name']}  –  ${svc['price']}",
            callback_data=f"svc:{svc['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


# ── Barbers ───────────────────────────────────────────────────────────────────

def barbers_kb(stats: dict[int, dict] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in BARBERS:
        label = b["name"]
        if stats and b["id"] in stats:
            label += f" ({stats[b['id']]['avg']} ⭐)"
        builder.button(text=label, callback_data=f"barber:{b['id']}")
    builder.adjust(2)
    return builder.as_markup()


# ── Date picker ───────────────────────────────────────────────────────────────

def date_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    dates = get_available_dates()
    for d in dates:
        label = d.strftime("%d %B, %A")   # e.g. "22 April, Wednesday"
        builder.button(text=label, callback_data=f"date:{d.isoformat()}")
    builder.adjust(2)
    return builder.as_markup()


# ── Time slots ────────────────────────────────────────────────────────────────

def timeslots_kb(available_slots: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in available_slots:
        builder.button(text=f"🕐 {slot}", callback_data=f"time:{slot}")
    builder.adjust(4)
    return builder.as_markup()


# ── Booking confirmation ───────────────────────────────────────────────────────

def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash",  callback_data="booking:confirm")
    builder.button(text="❌ Bekor qilish", callback_data="booking:cancel_flow")
    builder.adjust(2)
    return builder.as_markup()


# ── User bookings list ────────────────────────────────────────────────────────

def my_bookings_kb(bookings: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for bk in bookings:
        label = f"📅 {bk['booking_date']} {bk['time_slot']} – {bk['barber_name']}"
        builder.button(text=label, callback_data=f"mybk:{bk['id']}")
    builder.adjust(1)
    return builder.as_markup()


def single_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Qayta rejalashtirish", callback_data=f"reschedule:{booking_id}")
    builder.button(text="🗑 Bekor qilish",          callback_data=f"cancel_bk:{booking_id}")
    builder.button(text="⬅️ Orqaga",               callback_data="mybk:back")
    builder.adjust(1)
    return builder.as_markup()


# ── Maps button ───────────────────────────────────────────────────────────────

def maps_kb(lat: float, lon: float) -> InlineKeyboardMarkup:
    url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Google Maps da ochish", url=url)
    return builder.as_markup()


# ── Rating keyboards ─────────────────────────────────────────────────────────

def rating_stars_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(5, 0, -1):
        builder.button(text=f"{'⭐' * i}", callback_data=f"rate:{i}")
    builder.adjust(1)
    return builder.as_markup()


def skip_comment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Izohsiz qoldirish ➡️", callback_data="rate:skip_comment")
    return builder.as_markup()
