from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import timedelta

import aiohttp

from app.config import GITHUB_BRANCH, GITHUB_TOKEN, WEBAPP_DIR, github_repo
from app.db import get_active_bookings_from, get_settings
from app.utils import format_sum, now, today_str

logger = logging.getLogger(__name__)
PUBLIC_PATH = WEBAPP_DIR / "data" / "public.json"


async def build_snapshot() -> dict:
    s = await get_settings()
    price = int(s.get("hourly_price") or 0)
    start = today_str()
    rows = await get_active_bookings_from(start)
    days: dict[str, dict] = {}
    for i in range(14):
        day = (now() + timedelta(days=i)).strftime("%Y-%m-%d")
        days[day] = {"occupied": []}
    for b in rows:
        day = b["book_date"]
        if day not in days:
            days[day] = {"occupied": []}
        days[day]["occupied"].append(
            {"start_min": b["start_min"], "end_min": b["end_min"], "status": b["status"]}
        )
    return {
        "stadium_name": s.get("stadium_name") or "Mini Stadion",
        "address": s.get("stadium_address") or "",
        "hourly_price": price,
        "hourly_price_text": format_sum(price),
        "open_min": int(s.get("open_min") or 0),
        "close_min": int(s.get("close_min") or 1440),
        "days": days,
    }


async def publish_snapshot() -> None:
    data = await build_snapshot()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PATH.write_text(text + "\n", encoding="utf-8")
    repo = github_repo()
    if GITHUB_TOKEN and repo:
        await _push_github(repo, text)


async def _push_github(repo: str, text: str) -> None:
    api = f"https://api.github.com/repos/{repo}/contents/webapp/data/public.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mini-stadion-bot",
    }
    body = {
        "message": "bron holati yangilandi [skip ci]",
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        sha = None
        async with session.get(api, params={"ref": GITHUB_BRANCH}) as resp:
            if resp.status == 200:
                payload = await resp.json()
                sha = payload.get("sha")
            elif resp.status not in {404, 200}:
                err = await resp.text()
                logger.warning("GitHub fayl o'qilmadi (%s): %s", resp.status, err[:300])
                return
        if sha:
            body["sha"] = sha
        async with session.put(api, json=body) as resp:
            if resp.status not in {200, 201}:
                err = await resp.text()
                logger.warning("GitHubga yozilmadi (%s): %s", resp.status, err[:400])
            else:
                logger.info("Mini App snapshot GitHubga yuborildi")


def schedule_publish() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_publish_safe())


async def _publish_safe() -> None:
    try:
        await publish_snapshot()
    except Exception:
        logger.exception("Mini App snapshot yangilanmadi")
