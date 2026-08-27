from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl
from zoneinfo import ZoneInfo

from app.config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)

DAY_NAMES = [
    "Dushanba",
    "Seshanba",
    "Chorshanba",
    "Payshanba",
    "Juma",
    "Shanba",
    "Yakshanba",
]
MONTH_NAMES = [
    "",
    "yanvar",
    "fevral",
    "mart",
    "aprel",
    "may",
    "iyun",
    "iyul",
    "avgust",
    "sentabr",
    "oktabr",
    "noyabr",
    "dekabr",
]


def now() -> datetime:
    return datetime.now(TZ)


def today_str() -> str:
    return now().strftime("%Y-%m-%d")


def format_sum(amount: int | float | str) -> str:
    try:
        n = int(round(float(str(amount).replace(" ", "").replace(",", ""))))
    except (TypeError, ValueError):
        n = 0
    sign = "-" if n < 0 else ""
    digits = str(abs(n))
    grouped = " ".join(digits[max(i - 3, 0) : i] for i in range(len(digits), 0, -3)[::-1])
    return f"{sign}{grouped}"


def parse_sum(text: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", str(text or ""))
    if not cleaned:
        return None
    return int(cleaned)


def format_card(number: str) -> str:
    digits = re.sub(r"\D", "", number or "")
    if not digits:
        return ""
    return " ".join(digits[i : i + 4] for i in range(0, len(digits), 4))


def minutes_to_hhmm(total: int) -> str:
    total = int(total) % (24 * 60 + 1)
    if total >= 24 * 60:
        return "24:00"
    return f"{total // 60:02d}:{total % 60:02d}"


def hhmm_to_minutes(value: str) -> int:
    parts = value.strip().split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return h * 60 + m


def display_range(start_min: int, end_min: int) -> str:
    """21:00..22:00 -> 21:00/21:59 ; 20:00..21:30 -> 20:00/21:29"""
    last = max(start_min, end_min - 1)
    return f"{minutes_to_hhmm(start_min)}/{minutes_to_hhmm(last)}"


def format_uz_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{DAY_NAMES[dt.weekday()]}, {dt.day}-{MONTH_NAMES[dt.month]}"


def duration_text(start_min: int, end_min: int) -> str:
    mins = max(0, end_min - start_min)
    hours, rest = divmod(mins, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} soat")
    if rest:
        parts.append(f"{rest} daqiqa")
    return " ".join(parts) if parts else "0 daqiqa"


def calc_price(hourly_price: int, start_min: int, end_min: int) -> int:
    minutes = max(0, end_min - start_min)
    return int(round(hourly_price * minutes / 60))


def occupied_minutes(intervals: list[tuple[int, int]], start: int, end: int) -> int:
    clipped: list[list[int]] = []
    for s, e in intervals:
        a, b = max(s, start), min(e, end)
        if a < b:
            clipped.append([a, b])
    if not clipped:
        return 0
    clipped.sort()
    merged = [clipped[0]]
    for s, e in clipped[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return sum(b - a for a, b in merged)


def hour_color(hour: int, bookings: list[dict[str, Any]], close_min: int | None = None) -> str:
    start = hour * 60
    end = hour * 60 + 60
    if close_min is not None:
        end = min(end, close_min)
    available = max(0, end - start)
    if available <= 0:
        return "green"
    confirmed = [(b["start_min"], b["end_min"]) for b in bookings if b["status"] == "confirmed"]
    pending = [
        (b["start_min"], b["end_min"])
        for b in bookings
        if b["status"] in {"pending_payment", "pending_review"}
    ]
    booked_mins = occupied_minutes(confirmed, start, end)
    pending_mins = occupied_minutes(pending, start, end)
    if booked_mins >= available:
        return "red"
    if pending_mins > 0:
        return "orange"
    if 0 < booked_mins < available:
        return "blue"
    return "green"


def ranges_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    return s1 < e2 and s2 < e1


def validate_webapp_init_data(init_data: str, bot_token: str) -> dict[str, Any] | None:
    if not init_data or not bot_token:
        return None
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        return None
    user_raw = parsed.get("user")
    if not user_raw:
        return None
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        return None
    if not user.get("id"):
        return None
    return user
