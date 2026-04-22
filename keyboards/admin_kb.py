"""
Admin keyboards for the Telegram-based admin panel.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta


def admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Bugungi jadval",     callback_data="adm:today")
    builder.button(text="📆 Ertangi jadval",     callback_data="adm:tomorrow")
    builder.button(text="📋 Barcha (kelgusi)",   callback_data="adm:all")
    builder.button(text="🚫 Vaqtni band qilish", callback_data="adm:block_start")
    builder.button(text="💬 Izohlarni ko'rish",  callback_data="adm:view_ratings")
    builder.button(text="🔍 Sana bo'yicha",      callback_data="adm:by_date")
    builder.adjust(2)
    return builder.as_markup()


def admin_booking_action_kb(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Bajarildi",       callback_data=f"adm_status:{booking_id}:completed")
    builder.button(text="❌ Bekor qilindi",   callback_data=f"adm_status:{booking_id}:cancelled")
    builder.button(text="🗑 O'chirish",       callback_data=f"adm_delete:{booking_id}")
    builder.button(text="⬅️ Orqaga",          callback_data="adm:today")
    builder.adjust(2)
    return builder.as_markup()
