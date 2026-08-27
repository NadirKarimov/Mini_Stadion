from __future__ import annotations

from datetime import timedelta
from typing import Any

import aiosqlite

from app.config import DB_PATH, DATA_DIR, PENDING_EXPIRE_MINUTES, STADIUM_NAME
from app.timeparse import parse_created
from app.utils import now, ranges_overlap

_on_change = None


def set_on_change(fn) -> None:
    global _on_change
    _on_change = fn


def notify_change() -> None:
    if _on_change:
        try:
            _on_change()
        except Exception:
            pass

DEFAULT_SETTINGS = {
    "stadium_name": STADIUM_NAME,
    "stadium_address": "Manzil hali kiritilmagan",
    "stadium_lat": "41.311081",
    "stadium_lon": "69.240562",
    "hourly_price": "60000",
    "open_min": "360",
    "close_min": "1440",
    "card_click": "",
    "card_payme": "",
    "card_uzcard": "",
    "card_other_name": "",
    "card_other": "",
    "card_holder": "",
}


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


async def get_db() -> aiosqlite.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")
    return db


async def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = await get_db()
    try:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                book_date TEXT NOT NULL,
                start_min INTEGER NOT NULL,
                end_min INTEGER NOT NULL,
                price INTEGER NOT NULL,
                status TEXT NOT NULL,
                screenshot_file_id TEXT,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(book_date, status);
            CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(telegram_id, created_at);
            """
        )
        for key, value in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, value),
            )
        await db.commit()
    finally:
        await db.close()


async def upsert_user(telegram_id: int, username: str | None, full_name: str | None) -> None:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO users(telegram_id, username, full_name, created_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
            """,
            (telegram_id, username or "", full_name or "", now().isoformat()),
        )
        await db.commit()
    finally:
        await db.close()


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return _row_to_dict(await cur.fetchone())
    finally:
        await db.close()


async def list_user_ids() -> list[int]:
    db = await get_db()
    try:
        cur = await db.execute("SELECT telegram_id FROM users")
        rows = await cur.fetchall()
        return [int(r["telegram_id"]) for r in rows]
    finally:
        await db.close()


async def get_settings() -> dict[str, str]:
    db = await get_db()
    try:
        cur = await db.execute("SELECT key, value FROM settings")
        rows = await cur.fetchall()
        data = dict(DEFAULT_SETTINGS)
        data.update({r["key"]: r["value"] for r in rows})
        return data
    finally:
        await db.close()


async def set_setting(key: str, value: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        await db.commit()
    finally:
        await db.close()
    notify_change()


async def get_active_bookings_from(date_from: str) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cur = await db.execute(
            """
            SELECT book_date, start_min, end_min, status FROM bookings
            WHERE book_date >= ?
              AND status IN ('pending_payment', 'pending_review', 'confirmed')
            ORDER BY book_date, start_min
            """,
            (date_from,),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def get_bookings_for_date(book_date: str, active_only: bool = True) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        if active_only:
            cur = await db.execute(
                """
                SELECT * FROM bookings
                WHERE book_date = ?
                  AND status IN ('pending_payment', 'pending_review', 'confirmed')
                ORDER BY start_min
                """,
                (book_date,),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM bookings WHERE book_date = ? ORDER BY start_min",
                (book_date,),
            )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def get_booking(booking_id: int) -> dict[str, Any] | None:
    db = await get_db()
    try:
        cur = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        return _row_to_dict(await cur.fetchone())
    finally:
        await db.close()


async def user_bookings(telegram_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cur = await db.execute(
            """
            SELECT * FROM bookings
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (telegram_id, limit),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def pending_review_bookings() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cur = await db.execute(
            """
            SELECT b.*, u.username, u.full_name
            FROM bookings b
            LEFT JOIN users u ON u.telegram_id = b.telegram_id
            WHERE b.status IN ('pending_payment', 'pending_review')
            ORDER BY b.created_at
            """
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def has_overlap(book_date: str, start_min: int, end_min: int, exclude_id: int | None = None) -> bool:
    bookings = await get_bookings_for_date(book_date, active_only=True)
    for b in bookings:
        if exclude_id and b["id"] == exclude_id:
            continue
        if ranges_overlap(start_min, end_min, b["start_min"], b["end_min"]):
            return True
    return False


async def create_booking(
    telegram_id: int,
    book_date: str,
    start_min: int,
    end_min: int,
    price: int,
) -> dict[str, Any]:
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute(
            """
            SELECT id, start_min, end_min FROM bookings
            WHERE book_date = ?
              AND status IN ('pending_payment', 'pending_review', 'confirmed')
            """,
            (book_date,),
        )
        for row in await cur.fetchall():
            if ranges_overlap(start_min, end_min, row["start_min"], row["end_min"]):
                await db.rollback()
                raise ValueError("Bu vaqt allaqachon band")
        created = now().isoformat()
        cur = await db.execute(
            """
            INSERT INTO bookings(
                telegram_id, book_date, start_min, end_min, price, status, created_at
            ) VALUES(?, ?, ?, ?, ?, 'pending_payment', ?)
            """,
            (telegram_id, book_date, start_min, end_min, price, created),
        )
        await db.commit()
        booking_id = cur.lastrowid
        cur = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        row = await cur.fetchone()
        result = dict(row)
    except ValueError:
        raise
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
    notify_change()
    return result


async def set_booking_status(
    booking_id: int,
    status: str,
    screenshot_file_id: str | None = None,
) -> dict[str, Any] | None:
    db = await get_db()
    try:
        fields = ["status = ?"]
        args: list[Any] = [status]
        if screenshot_file_id is not None:
            fields.append("screenshot_file_id = ?")
            args.append(screenshot_file_id)
        if status in {"confirmed", "rejected", "cancelled"}:
            fields.append("reviewed_at = ?")
            args.append(now().isoformat())
        args.append(booking_id)
        await db.execute(f"UPDATE bookings SET {', '.join(fields)} WHERE id = ?", args)
        await db.commit()
        cur = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        result = _row_to_dict(await cur.fetchone())
    finally:
        await db.close()
    notify_change()
    return result


async def user_pending_payment(telegram_id: int) -> dict[str, Any] | None:
    db = await get_db()
    try:
        cur = await db.execute(
            """
            SELECT * FROM bookings
            WHERE telegram_id = ? AND status = 'pending_payment'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (telegram_id,),
        )
        return _row_to_dict(await cur.fetchone())
    finally:
        await db.close()


async def expire_old_pending() -> list[dict[str, Any]]:
    db = await get_db()
    expired: list[dict[str, Any]] = []
    try:
        cur = await db.execute("SELECT * FROM bookings WHERE status = 'pending_payment'")
        rows = [dict(r) for r in await cur.fetchall()]
        cutoff = now() - timedelta(minutes=PENDING_EXPIRE_MINUTES)
        for row in rows:
            try:
                created = parse_created(row["created_at"])
            except ValueError:
                continue
            if created <= cutoff:
                await db.execute(
                    "UPDATE bookings SET status = 'cancelled', reviewed_at = ? WHERE id = ?",
                    (now().isoformat(), row["id"]),
                )
                expired.append(row)
        await db.commit()
        result = expired
    finally:
        await db.close()
    if result:
        notify_change()
    return result


async def add_news(title: str, body: str) -> dict[str, Any]:
    db = await get_db()
    try:
        created = now().isoformat()
        cur = await db.execute(
            "INSERT INTO news(title, body, created_at) VALUES(?, ?, ?)",
            (title, body, created),
        )
        await db.commit()
        return {"id": cur.lastrowid, "title": title, "body": body, "created_at": created}
    finally:
        await db.close()


async def latest_news(limit: int = 10) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cur = await db.execute(
            "SELECT * FROM news ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


async def stats() -> dict[str, int]:
    db = await get_db()
    try:
        async def count(sql: str, args: tuple = ()) -> int:
            cur = await db.execute(sql, args)
            row = await cur.fetchone()
            return int(row[0] if row else 0)

        today = now().strftime("%Y-%m-%d")
        return {
            "users": await count("SELECT COUNT(*) FROM users"),
            "confirmed_today": await count(
                "SELECT COUNT(*) FROM bookings WHERE book_date = ? AND status = 'confirmed'",
                (today,),
            ),
            "pending": await count(
                "SELECT COUNT(*) FROM bookings WHERE status IN ('pending_payment', 'pending_review')"
            ),
            "confirmed_all": await count("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'"),
        }
    finally:
        await db.close()
