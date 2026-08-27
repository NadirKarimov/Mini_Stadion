from __future__ import annotations

from datetime import datetime

from app.utils import TZ


def parse_created(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt
