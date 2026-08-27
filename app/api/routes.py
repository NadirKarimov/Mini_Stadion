from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.booking import place_booking
from app.config import BOT_TOKEN, DEV_MODE
from app.db import get_bookings_for_date, get_settings, user_bookings
from app.utils import (
    display_range,
    duration_text,
    format_sum,
    hour_color,
    now,
    today_str,
    validate_webapp_init_data,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"ok": "1"}


class BookIn(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_min: int = Field(ge=0, le=24 * 60)
    end_min: int = Field(ge=1, le=24 * 60)


def _user_from_init(init_data: str | None) -> dict[str, Any]:
    user = validate_webapp_init_data(init_data or "", BOT_TOKEN)
    if user:
        return user
    if DEV_MODE:
        return {"id": 1, "username": "dev", "first_name": "Dev"}
    raise HTTPException(status_code=401, detail="Mini App faqat Telegram orqali ochiladi")


@router.get("/config")
async def api_config() -> dict[str, Any]:
    s = await get_settings()
    price = int(s.get("hourly_price") or 0)
    return {
        "stadium_name": s.get("stadium_name"),
        "address": s.get("stadium_address"),
        "lat": float(s.get("stadium_lat") or 0),
        "lon": float(s.get("stadium_lon") or 0),
        "hourly_price": price,
        "hourly_price_text": format_sum(price),
        "open_min": int(s.get("open_min") or 0),
        "close_min": int(s.get("close_min") or 1440),
        "today": today_str(),
        "now_min": now().hour * 60 + now().minute,
    }


@router.get("/slots")
async def api_slots(date: str) -> dict[str, Any]:
    if len(date) != 10:
        raise HTTPException(400, "Sana noto'g'ri")
    s = await get_settings()
    open_min = int(s.get("open_min") or 0)
    close_min = int(s.get("close_min") or 1440)
    bookings = await get_bookings_for_date(date, active_only=True)
    public = [
        {"start_min": b["start_min"], "end_min": b["end_min"], "status": b["status"]}
        for b in bookings
    ]
    hours = []
    start_hour = open_min // 60
    end_hour = (close_min + 59) // 60
    if close_min % 60 == 0:
        end_hour = close_min // 60
    for h in range(start_hour, end_hour):
        color = hour_color(h, public, close_min)
        label_start = h * 60
        label_end = min(h * 60 + 60, close_min)
        hours.append(
            {
                "hour": h,
                "start_min": label_start,
                "end_min": label_end,
                "label": display_range(label_start, label_end),
                "color": color,
            }
        )
    now_min = now().hour * 60 + now().minute if date == today_str() else (-1 if date > today_str() else 24 * 60)
    return {
        "date": date,
        "open_min": open_min,
        "close_min": close_min,
        "now_min": now_min,
        "hourly_price": int(s.get("hourly_price") or 0),
        "hours": hours,
        "occupied": public,
    }


@router.get("/my")
async def api_my(x_telegram_init_data: str | None = Header(default=None)) -> dict[str, Any]:
    user = _user_from_init(x_telegram_init_data)
    rows = await user_bookings(int(user["id"]), 20)
    return {
        "items": [
            {
                "id": b["id"],
                "date": b["book_date"],
                "range": display_range(b["start_min"], b["end_min"]),
                "duration": duration_text(b["start_min"], b["end_min"]),
                "price": b["price"],
                "price_text": format_sum(b["price"]),
                "status": b["status"],
            }
            for b in rows
        ]
    }


@router.post("/book")
async def api_book(payload: BookIn, x_telegram_init_data: str | None = Header(default=None)) -> dict[str, Any]:
    user = _user_from_init(x_telegram_init_data)
    telegram_id = int(user["id"])
    full_name = " ".join(p for p in [user.get("first_name"), user.get("last_name")] if p).strip()
    try:
        return await place_booking(
            telegram_id,
            user.get("username"),
            full_name,
            payload.date,
            payload.start_min,
            payload.end_min,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
