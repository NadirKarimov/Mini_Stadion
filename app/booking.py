from __future__ import annotations

import logging
from typing import Any

from app.config import is_admin
from app.db import create_booking, get_settings, upsert_user
from app.utils import calc_price, display_range, duration_text, format_sum, now, today_str

logger = logging.getLogger(__name__)


async def place_booking(
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    book_date: str,
    start_min: int,
    end_min: int,
) -> dict[str, Any]:
    await upsert_user(telegram_id, username, full_name)
    s = await get_settings()
    open_min = int(s.get("open_min") or 0)
    close_min = int(s.get("close_min") or 1440)
    price_hour = int(s.get("hourly_price") or 0)
    start_min = int(start_min)
    end_min = int(end_min)

    if end_min <= start_min:
        raise ValueError("Tugash vaqti boshlanishidan keyin bo'lishi kerak")
    if (end_min - start_min) < 30:
        raise ValueError("Minimal bron — 30 daqiqa")
    if start_min < open_min or end_min > close_min:
        raise ValueError("Stadion ish vaqtidan tashqari")
    if book_date < today_str():
        raise ValueError("O'tgan sanani bron qilib bo'lmaydi")
    if book_date == today_str() and start_min < now().hour * 60 + now().minute:
        raise ValueError("O'tgan vaqtni bron qilib bo'lmaydi")
    if price_hour <= 0:
        raise ValueError("Admin hali 1 soat narxini kiritmagan")

    price = calc_price(price_hour, start_min, end_min)
    booking = await create_booking(telegram_id, book_date, start_min, end_min, price)

    try:
        from app.bot.bot import notify_admins, notify_user_payment
        from app.bot.texts import booking_card, payment_instruction

        await notify_user_payment(telegram_id, payment_instruction(s, booking))
        if not is_admin(telegram_id):
            await notify_admins(
                "🟠 Yangi bron (to'lov kutilmoqda)\n\n"
                + booking_card(booking, username, full_name)
            )
    except Exception:
        logger.exception("Bron xabarini yuborishda xato")

    return {
        "ok": True,
        "id": booking["id"],
        "range": display_range(start_min, end_min),
        "duration": duration_text(start_min, end_min),
        "price": price,
        "price_text": format_sum(price),
        "message": "Botga o'ting — kartaga pul o'tkazib, skrinshot yuboring.",
    }
