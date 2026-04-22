"""
User-facing handlers: /start, booking flow, AI chat, location, my bookings.
All booking steps are protected by FSM states.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command

from config import (
    SERVICES, BARBERS,
    SHOP_LATITUDE, SHOP_LONGITUDE, SHOP_NAME, SHOP_ADDRESS,
)
from database import db
from keyboards import user_kb
from services.booking_service import get_available_slots
from states.booking_states import BookingStates, RescheduleStates, RatingStates

logger = logging.getLogger(__name__)
router = Router()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _service_by_id(svc_id: str) -> dict | None:
    return next((s for s in SERVICES if s["id"] == svc_id), None)

def _barber_by_id(barber_id: int) -> dict | None:
    return next((b for b in BARBERS if b["id"] == barber_id), None)

async def _ensure_user(message: Message) -> None:
    await db.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
    )


# ── /start ────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _ensure_user(message)
    name = message.from_user.first_name or "Do'stim"
    await message.answer(
        f"✂️ Salom, <b>{name}</b>! <b>Barbershop Elite</b>ga xush kelibsiz!\n\n"
        f"Quyidagi menüdan kerakli bo'limni tanlang 👇",
        reply_markup=user_kb.main_menu_kb(),
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Bekor qilish")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🔙 Asosiy menüga qaytdingiz.",
        reply_markup=user_kb.main_menu_kb(),
    )


# ── Info ──────────────────────────────────────────────────────────────────────

@router.message(F.text == "ℹ️ Ma'lumot")
async def cmd_info(message: Message) -> None:
    text = (
        "💈 <b>Barbershop Elite haqida</b>\n\n"
        "⏰ Ish vaqti: <b>09:00 – 21:00</b> (har kuni)\n"
        "👨‍💼 Sartaroshlar soni: <b>4 nafar</b>\n"
        "⏱ Har bir xizmat: <b>30 daqiqa</b>\n\n"
        "💰 <b>Narxlar:</b>\n"
        "  • ✂️ Soch qisqartirish – <b>$10</b>\n"
        "  • 🪒 Soqol tekislash  – <b>$7</b>\n"
        "  • 💈 Kombo            – <b>$15</b>\n"
        "  • ⭐ Premium stil     – <b>$20</b>\n\n"
        "Joy band qilish uchun <b>📅 Joy band qilish</b> tugmasini bosing."
    )
    await message.answer(text, parse_mode="HTML")


# ── Location ──────────────────────────────────────────────────────────────────

@router.message(F.text == "📍 Manzil")
async def cmd_location(message: Message) -> None:
    await message.answer(
        f"📍 <b>{SHOP_NAME}</b>\n{SHOP_ADDRESS}",
        parse_mode="HTML",
        reply_markup=user_kb.maps_kb(SHOP_LATITUDE, SHOP_LONGITUDE),
    )
    await message.answer_location(
        latitude=SHOP_LATITUDE,
        longitude=SHOP_LONGITUDE,
    )


# ══════════════════════════════════════════════════════════════════════════════
# BOOKING FLOW  (FSM)
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "📅 Joy band qilish")
async def booking_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _ensure_user(message)
    await state.set_state(BookingStates.waiting_for_service)
    await message.answer(
        "💈 <b>Xizmat turini tanlang:</b>",
        reply_markup=user_kb.services_kb(),
        parse_mode="HTML",
    )


# ── Step 1: Service selected ──────────────────────────────────────────────────

@router.callback_query(BookingStates.waiting_for_service, F.data.startswith("svc:"))
async def booking_service_chosen(call: CallbackQuery, state: FSMContext) -> None:
    svc_id = call.data.split(":")[1]
    svc = _service_by_id(svc_id)
    if not svc:
        await call.answer("Xizmat topilmadi!", show_alert=True)
        return

    await state.update_data(
        service_id=svc["id"],
        service_name=svc["name"],
        price=svc["price"],
    )
    await state.set_state(BookingStates.waiting_for_barber)
    stats = await db.get_all_barbers_stats()
    await call.message.edit_text(
        f"✅ Xizmat tanlandi: <b>{svc['name']}</b>  –  ${svc['price']}\n\n"
        f"👨‍💼 Sartaroshni tanlang:",
        reply_markup=user_kb.barbers_kb(stats),
        parse_mode="HTML",
    )
    await call.answer()


# ── Step 2: Barber selected ───────────────────────────────────────────────────

@router.callback_query(BookingStates.waiting_for_barber, F.data.startswith("barber:"))
async def booking_barber_chosen(call: CallbackQuery, state: FSMContext) -> None:
    barber_id = int(call.data.split(":")[1])
    barber = _barber_by_id(barber_id)
    if not barber:
        await call.answer("Sartarosh topilmadi!", show_alert=True)
        return

    await state.update_data(barber_id=barber_id, barber_name=barber["name"])
    await state.set_state(BookingStates.waiting_for_date)
    await call.message.edit_text(
        f"✅ Sartarosh: <b>{barber['name']}</b>\n\n"
        f"📅 Sanani tanlang:",
        reply_markup=user_kb.date_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Step 3: Date selected ─────────────────────────────────────────────────────

@router.callback_query(BookingStates.waiting_for_date, F.data.startswith("date:"))
async def booking_date_chosen(call: CallbackQuery, state: FSMContext) -> None:
    chosen_date = call.data.split(":")[1]
    data = await state.get_data()
    barber_id = data["barber_id"]

    available = await get_available_slots(barber_id, chosen_date)
    if not available:
        await call.answer(
            "Bu kun uchun bo'sh vaqt yo'q! Boshqa sanani tanlang.",
            show_alert=True,
        )
        return

    await state.update_data(booking_date=chosen_date)
    await state.set_state(BookingStates.waiting_for_time)
    await call.message.edit_text(
        f"✅ Sana: <b>{chosen_date}</b>\n\n"
        f"⏰ Bo'sh vaqtni tanlang:",
        reply_markup=user_kb.timeslots_kb(available),
        parse_mode="HTML",
    )
    await call.answer()


# ── Step 4: Time slot selected → Show confirmation ────────────────────────────

@router.callback_query(BookingStates.waiting_for_time, F.data.startswith("time:"))
async def booking_time_chosen(call: CallbackQuery, state: FSMContext) -> None:
    time_slot = call.data.split(":")[1]
    data = await state.get_data()

    # Double-check the slot is still free (race-condition guard)
    if not await db.is_slot_free(data["barber_id"], data["booking_date"], time_slot):
        await call.answer(
            "⚠️ Bu vaqt allaqachon band! Boshqa vaqtni tanlang.",
            show_alert=True,
        )
        # Refresh available slots
        available = await get_available_slots(data["barber_id"], data["booking_date"])
        if available:
            await call.message.edit_reply_markup(reply_markup=user_kb.timeslots_kb(available))
        return

    await state.update_data(time_slot=time_slot)
    await state.set_state(BookingStates.confirm_booking)

    barber = _barber_by_id(data["barber_id"])
    confirmation_text = (
        "📋 <b>Bandlov ma'lumotlari:</b>\n\n"
        f"💈 Xizmat:     <b>{data['service_name']}</b>\n"
        f"👨‍💼 Sartarosh:  <b>{data['barber_name']}</b>\n"
        f"📅 Sana:       <b>{data['booking_date']}</b>\n"
        f"⏰ Vaqt:       <b>{time_slot}</b>\n"
        f"💰 Narx:       <b>${data['price']}</b>\n\n"
        "Tasdiqlaysizmi?"
    )
    await call.message.edit_text(
        confirmation_text,
        reply_markup=user_kb.confirm_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Step 5: Confirm ───────────────────────────────────────────────────────────

@router.callback_query(BookingStates.confirm_booking, F.data == "booking:confirm")
async def booking_confirmed(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()

    booking_id = await db.create_booking(
        user_id=call.from_user.id,
        barber_id=data["barber_id"],
        service_id=data["service_id"],
        service_name=data["service_name"],
        booking_date=data["booking_date"],
        time_slot=data["time_slot"],
        price=data["price"],
    )

    await state.clear()

    if booking_id is None:
        await call.message.edit_text(
            "⚠️ Kechirasiz, bu vaqt aynan shu paytda band bo'ldi!\n"
            "Iltimos, boshqa vaqt tanlang.",
        )
        await call.message.answer(
            "📅 Qaytadan joy band qilish uchun tugmani bosing:",
            reply_markup=user_kb.main_menu_kb(),
        )
        return

    success_text = (
        f"🎉 <b>Bandlov muvaffaqiyatli yaratildi!</b>\n\n"
        f"🔖 Bandlov ID: <code>#{booking_id}</code>\n"
        f"💈 Xizmat:     <b>{data['service_name']}</b>\n"
        f"👨‍💼 Sartarosh:  <b>{data['barber_name']}</b>\n"
        f"📅 Sana:       <b>{data['booking_date']}</b>\n"
        f"⏰ Vaqt:       <b>{data['time_slot']}</b>\n"
        f"💰 Narx:       <b>${data['price']}</b>\n\n"
        f"⏰ Vaqtidan 2 soat oldin eslatma yuboriladi.\n"
        f"Barbershop Elite sizni kutmoqda! ✂️"
    )
    await call.message.edit_text(success_text, parse_mode="HTML")
    await call.message.answer("Asosiy menü:", reply_markup=user_kb.main_menu_kb())
    await call.answer("✅ Muvaffaqiyatli!")


@router.callback_query(BookingStates.confirm_booking, F.data == "booking:cancel_flow")
async def booking_cancel_flow(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("❌ Bandlov bekor qilindi.")
    await call.message.answer("Asosiy menü:", reply_markup=user_kb.main_menu_kb())
    await call.answer()


# ══════════════════════════════════════════════════════════════════════════════
# MY BOOKINGS
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "📋 Mening bandlovlarim")
async def my_bookings(message: Message, state: FSMContext) -> None:
    await state.clear()
    bookings = await db.get_user_bookings(message.from_user.id)
    if not bookings:
        await message.answer(
            "📭 Sizda hozircha faol bandlovlar yo'q.\n"
            "Joy band qilish uchun <b>📅 Joy band qilish</b> tugmasini bosing.",
            reply_markup=user_kb.main_menu_kb(),
            parse_mode="HTML",
        )
        return
    await message.answer(
        f"📋 <b>Sizning bandlovlaringiz ({len(bookings)} ta):</b>\n"
        "Batafsil ko'rish uchun bandlovni tanlang:",
        reply_markup=user_kb.my_bookings_kb(bookings),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mybk:"))
async def view_single_booking(call: CallbackQuery) -> None:
    payload = call.data.split(":")[1]
    if payload == "back":
        bookings = await db.get_user_bookings(call.from_user.id)
        if not bookings:
            await call.message.edit_text("📭 Faol bandlovlar yo'q.")
            return
        await call.message.edit_text(
            "📋 Bandlovlaringiz:",
            reply_markup=user_kb.my_bookings_kb(bookings),
        )
        await call.answer()
        return

    booking_id = int(payload)
    bk = await db.get_booking_by_id(booking_id)
    if not bk or bk["user_id"] != call.from_user.id:
        await call.answer("Bandlov topilmadi!", show_alert=True)
        return

    status_emoji = {"confirmed": "✅", "pending": "⏳", "completed": "🏁", "cancelled": "❌"}
    emoji = status_emoji.get(bk["status"], "❓")
    text = (
        f"📋 <b>Bandlov #{bk['id']}</b>  {emoji}\n\n"
        f"💈 Xizmat:    <b>{bk['service_name']}</b>\n"
        f"👨‍💼 Sartarosh: <b>{bk['barber_name']}</b>\n"
        f"📅 Sana:      <b>{bk['booking_date']}</b>\n"
        f"⏰ Vaqt:      <b>{bk['time_slot']}</b>\n"
        f"💰 Narx:      <b>${bk['price']}</b>\n"
        f"📌 Holat:     <b>{bk['status']}</b>"
    )
    await call.message.edit_text(
        text,
        reply_markup=user_kb.single_booking_kb(booking_id),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("cancel_bk:"))
async def cancel_booking_handler(call: CallbackQuery) -> None:
    booking_id = int(call.data.split(":")[1])
    success = await db.cancel_booking(booking_id, call.from_user.id)
    if success:
        await call.message.edit_text(
            f"✅ Bandlov <b>#{booking_id}</b> bekor qilindi.",
            parse_mode="HTML",
        )
    else:
        await call.answer("Bekor qilib bo'lmadi. Avval tasdiqlangan bo'lishi kerak.", show_alert=True)
    await call.answer()


# ══════════════════════════════════════════════════════════════════════════════
# RESCHEDULE  (FSM)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("reschedule:"))
async def reschedule_start(call: CallbackQuery, state: FSMContext) -> None:
    booking_id = int(call.data.split(":")[1])
    bk = await db.get_booking_by_id(booking_id)
    if not bk or bk["user_id"] != call.from_user.id:
        await call.answer("Bandlov topilmadi!", show_alert=True)
        return

    await state.update_data(
        rescheduling_id=booking_id,
        barber_id=bk["barber_id"],
        barber_name=bk["barber_name"],
        service_id=bk["service_id"],
        service_name=bk["service_name"],
        price=bk["price"],
    )
    await state.set_state(RescheduleStates.waiting_for_new_date)
    await call.message.edit_text(
        f"🔄 <b>Qayta rejalashtirish</b>\n"
        f"Bandlov #{booking_id}\n\n"
        "📅 Yangi sanani tanlang:",
        reply_markup=user_kb.date_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(RescheduleStates.waiting_for_new_date, F.data.startswith("date:"))
async def reschedule_date(call: CallbackQuery, state: FSMContext) -> None:
    new_date = call.data.split(":")[1]
    data = await state.get_data()
    available = await get_available_slots(data["barber_id"], new_date)
    if not available:
        await call.answer("Bu kun uchun bo'sh vaqt yo'q!", show_alert=True)
        return
    await state.update_data(booking_date=new_date)
    await state.set_state(RescheduleStates.waiting_for_new_time)
    await call.message.edit_text(
        f"📅 Yangi sana: <b>{new_date}</b>\n\n⏰ Yangi vaqtni tanlang:",
        reply_markup=user_kb.timeslots_kb(available),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(RescheduleStates.waiting_for_new_time, F.data.startswith("time:"))
async def reschedule_time(call: CallbackQuery, state: FSMContext) -> None:
    new_time = call.data.split(":")[1]
    data = await state.get_data()

    if not await db.is_slot_free(data["barber_id"], data["booking_date"], new_time):
        await call.answer("⚠️ Bu vaqt band! Boshqa vaqt tanlang.", show_alert=True)
        return

    # Cancel old booking and create new one
    await db.cancel_booking(data["rescheduling_id"], call.from_user.id)
    new_id = await db.create_booking(
        user_id=call.from_user.id,
        barber_id=data["barber_id"],
        service_id=data["service_id"],
        service_name=data["service_name"],
        booking_date=data["booking_date"],
        time_slot=new_time,
        price=data["price"],
    )
    await state.clear()

    if new_id:
        await call.message.edit_text(
            f"✅ Bandlov muvaffaqiyatli qayta rejalashtirildi!\n\n"
            f"🔖 Yangi ID: <code>#{new_id}</code>\n"
            f"📅 Sana: <b>{data['booking_date']}</b>\n"
            f"⏰ Vaqt: <b>{new_time}</b>",
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text("⚠️ Vaqt band bo'lib qoldi. Eski bandlovingiz saqlandi.")
    await call.answer()


# ══════════════════════════════════════════════════════════════════════════════
# RATING FLOW (FSM)
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "⭐ Baxolash")
async def rating_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RatingStates.waiting_for_barber)
    stats = await db.get_all_barbers_stats()
    await message.answer(
        "⭐ <b>Sartaroshni baxolash</b>\n\nBaxolamoqchi bo'lgan sartaroshingizni tanlang:",
        reply_markup=user_kb.barbers_kb(stats),
        parse_mode="HTML"
    )

@router.callback_query(RatingStates.waiting_for_barber, F.data.startswith("barber:"))
async def rating_barber_chosen(call: CallbackQuery, state: FSMContext) -> None:
    barber_id = int(call.data.split(":")[1])
    barber = _barber_by_id(barber_id)
    
    stats = await db.get_barber_stats(barber_id)
    
    await state.update_data(barber_id=barber_id, barber_name=barber["name"])
    await state.set_state(RatingStates.waiting_for_rating)
    
    text = (
        f"👨‍💼 Sartarosh: <b>{barber['name']}</b>\n"
        f"📊 Reyting: <b>{stats['avg']} ⭐</b> ({stats['count']} ta fikr)\n\n"
        "O'z baxongizni tanlang:"
    )
    await call.message.edit_text(text, reply_markup=user_kb.rating_stars_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(RatingStates.waiting_for_rating, F.data.startswith("rate:"))
async def rating_value_chosen(call: CallbackQuery, state: FSMContext) -> None:
    rating = int(call.data.split(":")[1])
    await state.update_data(rating=rating)
    await state.set_state(RatingStates.waiting_for_comment)
    await call.message.edit_text(
        f"Siz <b>{rating} ⭐</b> tanladingiz.\n\n"
        "Iltimos, o'z fikringizni yozing (ixtiyoriy):",
        reply_markup=user_kb.skip_comment_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(RatingStates.waiting_for_comment, F.data == "rate:skip_comment")
async def rating_skip_comment(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await db.save_rating(call.from_user.id, data["barber_id"], data["rating"], None)
    await state.clear()
    await call.message.edit_text("✅ Baxongiz uchun rahmat! Fikringiz biz uchun muhim.")
    await call.message.answer("Asosiy menyu:", reply_markup=user_kb.main_menu_kb())
    await call.answer()

@router.message(RatingStates.waiting_for_comment)
async def rating_comment_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await db.save_rating(message.from_user.id, data["barber_id"], data["rating"], message.text)
    await state.clear()
    await message.answer("✅ Baxo va fikringiz qabul qilindi! Rahmat.", reply_markup=user_kb.main_menu_kb())
