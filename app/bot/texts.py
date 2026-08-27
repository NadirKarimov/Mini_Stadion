from __future__ import annotations

from app.config import PENDING_EXPIRE_MINUTES
from app.utils import display_range, duration_text, format_card, format_sum, format_uz_date


STATUS_TEXT = {
    "pending_payment": "🟠 Skrinshot kutilmoqda",
    "pending_review": "🟠 Admin tasdig'i kutilmoqda",
    "confirmed": "🔴 Tasdiqlangan / band",
    "cancelled": "Bekor qilingan",
    "rejected": "Admin rad etgan",
}


def cards_text(settings: dict) -> str:
    lines = ["<b>To'lov kartalari</b>\n"]
    holder = settings.get("card_holder") or "—"
    lines.append(f"Karta egasi: <b>{holder}</b>\n")
    mapping = [
        ("Click", settings.get("card_click")),
        ("Payme", settings.get("card_payme")),
        ("Uzcard / Humo", settings.get("card_uzcard")),
    ]
    other_name = settings.get("card_other_name") or "Boshqa"
    other = settings.get("card_other")
    if other:
        mapping.append((other_name, other))
    any_card = False
    for name, number in mapping:
        if number:
            any_card = True
            lines.append(f"• {name}: <code>{format_card(number)}</code>")
    if not any_card:
        lines.append("Hali karta raqami kiritilmagan.")
    return "\n".join(lines)


def payment_instruction(settings: dict, booking: dict) -> str:
    name = settings.get("stadium_name") or "Mini Stadion"
    cards = cards_text(settings)
    rng = display_range(booking["start_min"], booking["end_min"])
    return (
        f"<b>{name}</b> — to'lov\n\n"
        f"📅 {format_uz_date(booking['book_date'])}\n"
        f"🕐 {rng}  ({duration_text(booking['start_min'], booking['end_min'])})\n"
        f"💵 <b>{format_sum(booking['price'])} so'm</b>\n\n"
        f"{cards}\n\n"
        "Pul o'tkazib, chek/skrinshotni shu yerga rasm qilib yuboring.\n"
        f"Skrinshot {PENDING_EXPIRE_MINUTES} daqiqa ichida yuborilmasa, bron avtomatik bekor qilinadi."
    )


def booking_card(booking: dict, username: str | None = None, full_name: str | None = None) -> str:
    who = full_name or "Foydalanuvchi"
    uname = f" @{username}" if username else ""
    return (
        f"<b>Bron #{booking['id']}</b>\n"
        f"👤 {who}{uname}\n"
        f"🆔 <code>{booking['telegram_id']}</code>\n"
        f"📅 {format_uz_date(booking['book_date'])}\n"
        f"🕐 {display_range(booking['start_min'], booking['end_min'])} "
        f"({duration_text(booking['start_min'], booking['end_min'])})\n"
        f"💵 {format_sum(booking['price'])} so'm\n"
        f"Holat: {STATUS_TEXT.get(booking['status'], booking['status'])}"
    )


HELP_TEXT = (
    "<b>Qanday bron qilinadi?</b>\n\n"
    "1) <b>🏟️ Bron qilish</b> tugmasini bosing — Mini App ochiladi.\n"
    "2) Sanani tanlang, soat ranglari bo'yicha bo'sh vaqtni ko'ring.\n"
    "3) Boshlanish va tugash vaqtini belgilang (masalan 19:00 dan 20:30 gacha).\n"
    "4) Summani to'lab, skrinshotni botga yuboring.\n"
    "5) Admin tasdiqlagach, vaqt rasman band bo'ladi.\n\n"
    "<b>Ranglar:</b>\n"
    "🟢 Yashil — soat to'liq bo'sh\n"
    "🔵 Ko'k — soatning bir qismi band, bir qismi bo'sh\n"
    "🔴 Qizil — soat to'liq band\n"
    "🟠 To'q sariq — to'lov tasdig'i kutilmoqda\n\n"
    "1 soat 21:00/21:59 ko'rinishida yoziladi. "
    "1 soat 30 daqiqa esa 20:00/21:29."
)
