"""
FSM state groups for the booking flow and AI chat.
"""
from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    waiting_for_service   = State()
    waiting_for_barber    = State()
    waiting_for_date      = State()
    waiting_for_time      = State()
    confirm_booking       = State()


class RescheduleStates(StatesGroup):
    waiting_for_booking_id = State()
    waiting_for_new_date   = State()
    waiting_for_new_time   = State()


class RatingStates(StatesGroup):
    waiting_for_barber = State()
    waiting_for_rating = State()
    waiting_for_comment = State()


class AdminBlockStates(StatesGroup):
    waiting_for_barber = State()
    waiting_for_date   = State()
    waiting_for_time   = State()
