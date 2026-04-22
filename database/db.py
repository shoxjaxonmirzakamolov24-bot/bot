"""
Database layer – uses aiosqlite for async SQLite.
For PostgreSQL, replace aiosqlite calls with asyncpg/SQLAlchemy async.
"""
import aiosqlite
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "barbershop.db"


async def init_db() -> None:
    """Create all tables on first run."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                phone       TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS barbers (
                id      INTEGER PRIMARY KEY,
                name    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                barber_id    INTEGER NOT NULL,
                service_id   TEXT NOT NULL,
                service_name TEXT NOT NULL,
                booking_date TEXT NOT NULL,   -- YYYY-MM-DD
                time_slot    TEXT NOT NULL,   -- HH:MM
                price        INTEGER NOT NULL,
                status       TEXT NOT NULL DEFAULT 'confirmed',
                reminder_sent INTEGER DEFAULT 0,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id)   REFERENCES users(user_id),
                FOREIGN KEY(barber_id) REFERENCES barbers(id)
            );

            CREATE TABLE IF NOT EXISTS ratings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                barber_id  INTEGER NOT NULL,
                rating     INTEGER NOT NULL, -- 1-5
                comment    TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id)   REFERENCES users(user_id),
                FOREIGN KEY(barber_id) REFERENCES barbers(id)
            );

            CREATE INDEX IF NOT EXISTS idx_bookings_date_barber
                ON bookings(booking_date, barber_id, status);
        """)
        await db.commit()


# ── User helpers ─────────────────────────────────────────────────────────────

async def upsert_user(user_id: int, username: str, full_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name))
        await db.commit()


# ── Barber helpers ───────────────────────────────────────────────────────────

async def seed_barbers(barbers: list[dict]) -> None:
    """Insert default barbers if not present."""
    async with aiosqlite.connect(DB_PATH) as db:
        for b in barbers:
            await db.execute("""
                INSERT OR IGNORE INTO barbers (id, name) VALUES (?, ?)
            """, (b["id"], b["name"]))
        await db.commit()


async def get_all_barbers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM barbers ORDER BY id") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ── Booking helpers ──────────────────────────────────────────────────────────

async def is_slot_free(barber_id: int, booking_date: str, time_slot: str) -> bool:
    """Returns True if the slot is NOT already booked."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT id FROM bookings
            WHERE barber_id = ?
              AND booking_date = ?
              AND time_slot = ?
              AND status IN ('confirmed', 'pending')
        """, (barber_id, booking_date, time_slot)) as cur:
            row = await cur.fetchone()
    return row is None


async def create_booking(
    user_id: int,
    barber_id: int,
    service_id: str,
    service_name: str,
    booking_date: str,
    time_slot: str,
    price: int,
) -> Optional[int]:
    """
    Creates a booking ONLY if the slot is still free.
    Returns the new booking id, or None on conflict.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Final race-condition guard inside a transaction
        async with db.execute("""
            SELECT id FROM bookings
            WHERE barber_id = ?
              AND booking_date = ?
              AND time_slot = ?
              AND status IN ('confirmed', 'pending')
        """, (barber_id, booking_date, time_slot)) as cur:
            conflict = await cur.fetchone()

        if conflict:
            return None  # Slot taken – caller should handle this

        cursor = await db.execute("""
            INSERT INTO bookings
                (user_id, barber_id, service_id, service_name,
                 booking_date, time_slot, price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed')
        """, (user_id, barber_id, service_id, service_name,
              booking_date, time_slot, price))
        await db.commit()
        return cursor.lastrowid


async def get_booked_slots(barber_id: int, booking_date: str) -> list[str]:
    """Returns list of time strings 'HH:MM' already booked for this barber/date."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT time_slot FROM bookings
            WHERE barber_id = ?
              AND booking_date = ?
              AND status IN ('confirmed', 'pending')
        """, (barber_id, booking_date)) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_user_bookings(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT b.*, br.name AS barber_name
            FROM bookings b
            JOIN barbers br ON b.barber_id = br.id
            WHERE b.user_id = ?
              AND b.status IN ('confirmed', 'pending')
              AND b.booking_date >= date('now', 'localtime')
            ORDER BY b.booking_date, b.time_slot
        """, (user_id,)) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_booking_by_id(booking_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT b.*, br.name AS barber_name
            FROM bookings b
            JOIN barbers br ON b.barber_id = br.id
            WHERE b.id = ?
        """, (booking_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def cancel_booking(booking_id: int, user_id: int) -> bool:
    """Cancels a booking – verifies it belongs to the user."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            UPDATE bookings SET status = 'cancelled'
            WHERE id = ? AND user_id = ? AND status IN ('confirmed', 'pending')
        """, (booking_id, user_id))
        await db.commit()
    return cur.rowcount > 0


# ── Admin helpers ─────────────────────────────────────────────────────────────

async def admin_get_daily_schedule(booking_date: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT b.*, br.name AS barber_name, u.full_name AS client_name, u.username
            FROM bookings b
            JOIN barbers br ON b.barber_id = br.id
            JOIN users u ON b.user_id = u.user_id
            WHERE b.booking_date = ?
              AND b.status NOT IN ('cancelled')
            ORDER BY b.barber_id, b.time_slot
        """, (booking_date,)) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def admin_get_all_upcoming() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT b.*, br.name AS barber_name, u.full_name AS client_name, u.username
            FROM bookings b
            JOIN barbers br ON b.barber_id = br.id
            JOIN users u ON b.user_id = u.user_id
            WHERE b.booking_date >= date('now', 'localtime')
              AND b.status NOT IN ('cancelled')
            ORDER BY b.booking_date, b.time_slot
        """) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def admin_update_status(booking_id: int, new_status: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE bookings SET status = ? WHERE id = ?",
            (new_status, booking_id)
        )
        await db.commit()
    return cur.rowcount > 0


async def get_upcoming_unreminded() -> list[dict]:
    """
    Returns bookings where reminder_sent=0 and appointment is
    within REMINDER_HOURS_BEFORE hours from now.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT b.*, u.user_id AS telegram_id
            FROM bookings b
            JOIN users u ON b.user_id = u.user_id
            WHERE b.status = 'confirmed'
              AND b.reminder_sent = 0
              AND datetime(b.booking_date || ' ' || b.time_slot)
                  BETWEEN datetime('now', '+1 hours', 'localtime')
                  AND  datetime('now', '+3 hours', 'localtime')
        """) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def mark_reminder_sent(booking_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET reminder_sent = 1 WHERE id = ?", (booking_id,)
        )
        await db.commit()


async def save_rating(user_id: int, barber_id: int, rating: int, comment: str = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO ratings (user_id, barber_id, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, barber_id, rating, comment))
        await db.commit()

async def get_barber_stats(barber_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) as count, AVG(rating) as avg
            FROM ratings WHERE barber_id = ?
        """, (barber_id,)) as cur:
            row = await cur.fetchone()
    return {"count": row[0], "avg": round(row[1], 1) if row[1] else 0}


async def get_all_barbers_stats() -> dict[int, dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT barber_id, COUNT(*) as count, AVG(rating) as avg
            FROM ratings GROUP BY barber_id
        """) as cur:
            rows = await cur.fetchall()
    
    stats = {row[0]: {"count": row[1], "avg": round(row[2], 1)} for row in rows}
    return stats


async def get_recent_ratings(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT r.*, u.full_name as user_name
            FROM ratings r
            JOIN users u ON r.user_id = u.user_id
            ORDER BY r.created_at DESC LIMIT ?
        """, (limit,)) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]
