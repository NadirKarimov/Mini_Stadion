from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://127.0.0.1:8080").rstrip("/")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
DEV_MODE = os.getenv("DEV_MODE", "0").strip() in {"1", "true", "True", "yes"}
STADIUM_NAME = os.getenv("STADIUM_NAME", "Mini Stadion").strip() or "Mini Stadion"
TIMEZONE = "Asia/Tashkent"
PENDING_EXPIRE_MINUTES = 30
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "stadion.db"
WEBAPP_DIR = ROOT / "webapp"


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))


def is_admin(user_id: int | None) -> bool:
    return bool(user_id) and int(user_id) in ADMIN_IDS


def github_repo() -> str:
    if GITHUB_REPO:
        return GITHUB_REPO
    # https://ali.github.io/Stadion → ali/Stadion
    if "github.io" not in WEBAPP_URL:
        return ""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(WEBAPP_URL if "://" in WEBAPP_URL else f"https://{WEBAPP_URL}")
        user = parsed.netloc.split(".")[0]
        parts = [p for p in parsed.path.split("/") if p]
        repo = parts[0] if parts else f"{user}.github.io"
        return f"{user}/{repo}"
    except Exception:
        return ""
