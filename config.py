import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot credentials ──────────────────────────────────────────────────────────
BOT_TOKEN: str = "8691567765:AAGsZocSLQZBlLaCFiJUt_FIDGNz-L0efy0"
ADMIN_ID: int = 1134823495
GEMINI_API_KEY: str = "AIzaSyBEf1vsCwzR1pDht_l-fGzIeYYzFVvGrLU"

# ── Shop info ────────────────────────────────────────────────────────────────
SHOP_LATITUDE: float = float(os.getenv("SHOP_LATITUDE", "40.75141"))
SHOP_LONGITUDE: float = float(os.getenv("SHOP_LONGITUDE", "72.35256"))
SHOP_NAME: str = os.getenv("SHOP_NAME", "Faded")
SHOP_ADDRESS: str = os.getenv("SHOP_ADDRESS", "Andijon, mashrab ko'chasi")

# ── Working hours ────────────────────────────────────────────────────────────
WORK_START_HOUR: int = 9
WORK_END_HOUR: int = 21
SLOT_DURATION_MINUTES: int = 30

# ── Barbers ──────────────────────────────────────────────────────────────────
BARBERS: list[dict] = [
    {"id": 1, "name": "Barber 1 – Azizbek"},
    {"id": 2, "name": "Barber 2 – Jasur"},
    {"id": 3, "name": "Barber 3 – Sherzod"},
    {"id": 4, "name": "Barber 4 – Doniyor"},
]

# ── Services ─────────────────────────────────────────────────────────────────
SERVICES: list[dict] = [
    {"id": "haircut",       "name": "✂️ Soch qisqartirish",  "price": 10},
    {"id": "beard",         "name": "🪒 Soqol tekislash",    "price": 7},
    {"id": "combo",         "name": "💈 Kombo (soch+soqol)", "price": 15},
    {"id": "premium",       "name": "⭐ Premium stil",       "price": 20},
]

# ── Calendar settings ────────────────────────────────────────────────────────
CALENDAR_DAYS_AHEAD: int = 14   # Show next 14 days

# ── Reminder ─────────────────────────────────────────────────────────────────
REMINDER_HOURS_BEFORE: int = 2

# ── Webhook settings (for Render.com) ────────────────────────────────────────
WEBHOOK_HOST: str = os.getenv("RENDER_EXTERNAL_URL", "")  # e.g., https://your-app.onrender.com
WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEB_SERVER_HOST: str = "0.0.0.0"
WEB_SERVER_PORT: int = int(os.getenv("PORT", 8080))
