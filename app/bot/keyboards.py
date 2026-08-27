from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import WEBAPP_URL, is_admin


def webapp_url() -> str:
    url = (WEBAPP_URL or "").strip().rstrip("/")
    if not url:
        return url
    return url + "/"


def open_app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏟️ Bron qilish va vaqtlarni ko'rish", web_app=WebAppInfo(url=webapp_url()))]
        ]
    )


def main_keyboard(user_id: int | None = None) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🏟️ Bron qilish", web_app=WebAppInfo(url=webapp_url()))],
        [KeyboardButton(text="📅 Mening bronlarim"), KeyboardButton(text="📰 Yangiliklar")],
        [KeyboardButton(text="📍 Lokatsiya"), KeyboardButton(text="ℹ️ Yordam")],
    ]
    if is_admin(user_id):
        rows.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Kartalar"), KeyboardButton(text="💰 Narx")],
            [KeyboardButton(text="🕐 Ish vaqti"), KeyboardButton(text="📍 Stadion manzili")],
            [KeyboardButton(text="⏳ Kutilayotgan bronlar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="✍️ Yangilik qo'shish")],
            [KeyboardButton(text="⬅️ Foydalanuvchi menyusi")],
        ],
        resize_keyboard=True,
    )


def cards_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Click karta", callback_data="set:card_click")],
            [InlineKeyboardButton(text="Payme karta", callback_data="set:card_payme")],
            [InlineKeyboardButton(text="Uzcard / Humo", callback_data="set:card_uzcard")],
            [InlineKeyboardButton(text="Boshqa to'lov", callback_data="set:card_other")],
            [InlineKeyboardButton(text="Karta egasi (F.I.Sh.)", callback_data="set:card_holder")],
        ]
    )


def booking_admin_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"bk:ok:{booking_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"bk:no:{booking_id}"),
            ]
        ]
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor")]],
        resize_keyboard=True,
    )


def news_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Barchaga yuborish", callback_data="news:send"),
                InlineKeyboardButton(text="Faqat saqlash", callback_data="news:save"),
            ]
        ]
    )
