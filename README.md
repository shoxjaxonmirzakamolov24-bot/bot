# ✂️ Barbershop Elite — Telegram Bot

A **production-ready** Telegram booking bot for a mid-level barbershop, built with Python + aiogram 3 + SQLite.

---

## 📁 Project Structure

```
boooot/
├── bot.py                    ← Entry point
├── config.py                 ← All settings, prices, barber list
├── requirements.txt
├── .env.example              ← Copy to .env and fill in tokens
├── data/
│   └── barbershop.db         ← Auto-created SQLite database
├── database/
│   └── db.py                 ← Async CRUD & double-booking prevention
├── handlers/
│   ├── user_handlers.py      ← Full booking FSM + AI chat + location
│   └── admin_handlers.py     ← Admin panel (schedule, status changes)
├── keyboards/
│   ├── user_kb.py            ← All user-facing keyboards
│   └── admin_kb.py           ← Admin inline keyboards
├── services/
│   ├── booking_service.py    ← Slot generation & availability logic
│   ├── ai_service.py         ← Google Gemini AI (Uzbek language)
│   └── scheduler.py          ← APScheduler 2-hour reminders
└── states/
    └── booking_states.py     ← FSM state groups
```

---

## ⚡ Quick Start

### 1. Clone & install

```bash
cd boooot
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your Telegram numeric user ID (get from [@userinfobot](https://t.me/userinfobot)) |
| `GEMINI_API_KEY` | From [Google AI Studio](https://aistudio.google.com/app/apikey) *(optional)* |
| `SHOP_LATITUDE` | Barbershop GPS latitude |
| `SHOP_LONGITUDE` | Barbershop GPS longitude |

### 3. Run

```bash
python bot.py
```

---

## 🤖 Bot Features

### For Customers
| Feature | Description |
|---|---|
| 📅 **Booking** | Select service → barber → date → time → confirm |
| 📋 **My Bookings** | View, cancel, or reschedule active appointments |
| 📍 **Location** | Sends GPS pin + Google Maps link |
| 🤖 **AI Assistant** | Uzbek-language hairstyle advisor (Gemini-powered) |
| ⏰ **Reminders** | Auto reminder 2 hours before appointment |

### For Admin (`/admin`)
| Feature | Description |
|---|---|
| 📅 Today's schedule | All bookings for today by barber |
| 📆 Tomorrow's schedule | Plan ahead |
| 📋 All upcoming | Full list grouped by date |
| ✅ Mark completed | Change booking status |
| ❌ Cancel booking | Remove a booking |
| 📊 `/stats` | Quick stats summary |

---

## 💰 Pricing

| Service | Price |
|---|---|
| ✂️ Soch qisqartirish (Haircut) | $10 |
| 🪒 Soqol tekislash (Beard trim) | $7 |
| 💈 Kombo (Combo) | $15 |
| ⭐ Premium stil | $20 |

---

## 🔒 Double-Booking Prevention

Two-layer protection:
1. **Frontend** — Users only see free time slots (already-booked ones are hidden)
2. **Backend** — Final race-condition check inside a DB transaction before `INSERT`

---

## 🗂️ Database Schema

```sql
users    (user_id PK, username, full_name, phone, created_at)
barbers  (id PK, name)
bookings (id PK, user_id FK, barber_id FK, service_id, service_name,
          booking_date, time_slot, price, status, reminder_sent, created_at)
```

**Booking statuses:** `pending` → `confirmed` → `completed` / `cancelled`

---

## 🔄 Booking Flow (FSM)

```
/start
  └─► Main Menu
        ├─► 📅 Joy band qilish
        │     ├─► Select Service
        │     ├─► Select Barber
        │     ├─► Select Date
        │     ├─► Select Time (only free slots shown)
        │     └─► Confirm → ✅ Booked!
        ├─► 📋 My Bookings → View / Cancel / Reschedule
        ├─► 🤖 AI Assistant → Free-form Uzbek chat
        └─► 📍 Location → GPS + Maps link
```

---

## 🌍 Scaling to Production

| Concern | MVP (current) | Production upgrade |
|---|---|---|
| Database | SQLite | PostgreSQL + asyncpg |
| FSM Storage | MemoryStorage | RedisStorage |
| Deployment | `python bot.py` | Docker + systemd / Railway |
| AI History | In-memory dict | Redis cache |

---

## 📞 Customisation

All barber names, prices, working hours, and shop info are in **`config.py`** — no code changes needed elsewhere.
