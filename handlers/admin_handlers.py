"""
Admin-only handlers. All commands are restricted to ADMIN_ID.
Access: send /admin to the bot.
"""
import logging
from datetime import date, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from database import db
from keyboards import admin_kb, user_kb
from states.booking_states import AdminBlockStates
import config

logger = logging.getLogger(__name__)
router = Router()


# ── Admin access guard ────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    await message.answer(
        "👨‍💼 <b>Admin Paneli</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML",
    )


# ── Schedule helpers ──────────────────────────────────────────────────────────

def _format_schedule(bookings: list[dict], title: str) -> str:
    if not bookings:
        return f"📭 <b>{title}</b>\n\nBandlovlar yo'q."

    lines = [f"📅 <b>{title}</b>\n"]
    current_barber = None
    for bk in bookings:
        if bk["barber_name"] != current_barber:
            current_barber = bk["barber_name"]
            lines.append(f"\n👨‍💼 <b>{current_barber}</b>")
        status_map = {
            "confirmed": "✅", "pending": "⏳",
            "completed": "🏁", "cancelled": "❌",
        }
        st = status_map.get(bk["status"], "❓")
        lines.append(
            f"  {st} <code>#{bk['id']}</code> {bk['time_slot']} — "
            f"{bk['service_name']} | "
            f"{bk.get('client_name','?')} "
            f"(@{bk.get('username','—')})"
        )
    return "\n".join(lines)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:today")
async def adm_today(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    today = date.today().isoformat()
    bookings = await db.admin_get_daily_schedule(today)
    text = _format_schedule(bookings, f"Bugungi jadval – {today}")
    await call.message.edit_text(
        text,
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "adm:tomorrow")
async def adm_tomorrow(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    bookings = await db.admin_get_daily_schedule(tomorrow)
    text = _format_schedule(bookings, f"Ertangi jadval – {tomorrow}")
    await call.message.edit_text(
        text,
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "adm:all")
async def adm_all(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    bookings = await db.admin_get_all_upcoming()

    if not bookings:
        await call.message.edit_text(
            "📭 Kelgusi bandlovlar yo'q.",
            reply_markup=admin_kb.admin_main_kb(),
        )
        await call.answer(); return

    # Group by date for readability
    by_date: dict[str, list] = {}
    for bk in bookings:
        by_date.setdefault(bk["booking_date"], []).append(bk)

    chunks: list[str] = []
    for d, bks in by_date.items():
        chunks.append(_format_schedule(bks, d))

    full_text = "\n\n".join(chunks)
    # Telegram message limit 4096 chars
    if len(full_text) > 3800:
        full_text = full_text[:3800] + "\n\n<i>...qisqartirildi</i>"

    await call.message.edit_text(
        full_text,
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_status:"))
async def adm_change_status(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    _, booking_id_str, new_status = call.data.split(":")
    booking_id = int(booking_id_str)
    ok = await db.admin_update_status(booking_id, new_status)
    if ok:
        await call.answer(f"✅ Holat «{new_status}» ga o'zgartirildi.")
        await call.message.edit_text(
            f"✅ Bandlov <b>#{booking_id}</b> holati: <b>{new_status}</b>",
            parse_mode="HTML",
            reply_markup=admin_kb.admin_main_kb(),
        )
    else:
        await call.answer("Xatolik yuz berdi.", show_alert=True)


@router.callback_query(F.data.startswith("adm_delete:"))
async def adm_delete(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    booking_id = int(call.data.split(":")[1])
    ok = await db.admin_update_status(booking_id, "cancelled")
    if ok:
        await call.answer(f"🗑 Bandlov #{booking_id} o'chirildi (cancelled).")
        await call.message.edit_text(
            f"🗑 Bandlov <b>#{booking_id}</b> bekor qilindi.",
            parse_mode="HTML",
            reply_markup=admin_kb.admin_main_kb(),
        )
    else:
        await call.answer("Xatolik!", show_alert=True)


# ── /stats command ────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def admin_stats(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔"); return
    bookings = await db.admin_get_all_upcoming()
    today = date.today().isoformat()
    today_count = sum(1 for b in bookings if b["booking_date"] == today)
# ══════════════════════════════════════════════════════════════════════════════
# BLOCK SLOT FLOW (Admin)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm:block_start")
async def adm_block_start(call: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminBlockStates.waiting_for_barber)
    stats = await db.get_all_barbers_stats()
    await call.message.edit_text(
        "🚫 <b>Vaqtni band qilish (Block)</b>\n\nSartaroshni tanlang:",
        reply_markup=user_kb.barbers_kb(stats),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(AdminBlockStates.waiting_for_barber, F.data.startswith("barber:"))
async def adm_block_barber(call: CallbackQuery, state: FSMContext) -> None:
    barber_id = int(call.data.split(":")[1])
    barber_name = next(b["name"] for b in config.BARBERS if b["id"] == barber_id)
    await state.update_data(barber_id=barber_id, barber_name=barber_name)
    await state.set_state(AdminBlockStates.waiting_for_date)
    await call.message.edit_text(
        f"👨‍💼 Sartarosh: <b>{barber_name}</b>\n\nSanani tanlang:",
        reply_markup=user_kb.date_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(AdminBlockStates.waiting_for_date, F.data.startswith("date:"))
async def adm_block_date(call: CallbackQuery, state: FSMContext) -> None:
    chosen_date = call.data.split(":")[1]
    data = await state.get_data()
    from services.booking_service import get_available_slots
    available = await get_available_slots(data["barber_id"], chosen_date)
    
    await state.update_data(booking_date=chosen_date)
    await state.set_state(AdminBlockStates.waiting_for_time)
    await call.message.edit_text(
        f"📅 Sana: <b>{chosen_date}</b>\n\nBand qilinadigan vaqtni tanlang:",
        reply_markup=user_kb.timeslots_kb(available),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(AdminBlockStates.waiting_for_time, F.data.startswith("time:"))
async def adm_block_time(call: CallbackQuery, state: FSMContext) -> None:
    time_slot = call.data.split(":")[1]
    data = await state.get_data()
    
    # Create a "Special" booking to block the time
    booking_id = await db.create_booking(
        user_id=call.from_user.id,
        barber_id=data["barber_id"],
        service_id="BLOCKED",
        service_name="🚫 ADMIN TOMONIDAN BAND QILINGAN",
        booking_date=data["booking_date"],
        time_slot=time_slot,
        price=0
    )
    
    await state.clear()
    if booking_id:
        await call.message.edit_text(
            f"✅ Muvaffaqiyatli band qilindi!\n\n"
            f"Sartarosh: {data['barber_name']}\n"
            f"Sana: {data['booking_date']}\n"
            f"Vaqt: {time_slot}",
            reply_markup=admin_kb.admin_main_kb()
        )
    else:
        await call.message.edit_text("⚠️ Xatolik: Bu vaqt allaqachon band!", reply_markup=admin_kb.admin_main_kb())
    await call.answer()

@router.callback_query(F.data == "adm:view_ratings")
async def adm_view_ratings(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id): return
    
    ratings = await db.get_recent_ratings(15)
    if not ratings:
        await call.message.edit_text("💬 Hozircha hech qanday izoh yo'q.", reply_markup=admin_kb.admin_main_kb())
        return

    text = "💬 <b>Oxirgi 15 ta izoh:</b>\n\n"
    for r in ratings:
        barber = next((b["name"] for b in config.BARBERS if b["id"] == r["barber_id"]), "Noma'lum")
        text += (
            f"👤 {r['user_name']}\n"
            f"👨‍💼 {barber} | {'⭐' * r['rating']}\n"
            f"📝 {r['comment'] or 'Izohsiz'}\n"
            f"📅 {r['created_at'][:16]}\n"
            f"-------------------\n"
        )
    
    await call.message.edit_text(text, reply_markup=admin_kb.admin_main_kb(), parse_mode="HTML")
    await call.answer()
