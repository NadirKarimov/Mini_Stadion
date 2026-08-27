from __future__ import annotations

import asyncio
import json
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart, Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from app.bot.keyboards import (
    admin_keyboard,
    booking_admin_keyboard,
    cancel_kb,
    cards_keyboard,
    main_keyboard,
    news_broadcast_kb,
    open_app_keyboard,
)
from app.bot.states import AdminStates
from app.bot.texts import HELP_TEXT, STATUS_TEXT, booking_card, cards_text
from app.booking import place_booking
from app.config import is_admin
from app.db import (
    add_news,
    get_booking,
    get_settings,
    latest_news,
    list_user_ids,
    pending_review_bookings,
    set_booking_status,
    set_setting,
    stats,
    upsert_user,
    user_bookings,
    user_pending_payment,
)
from app.utils import (
    display_range,
    duration_text,
    format_card,
    format_sum,
    format_uz_date,
    hhmm_to_minutes,
    minutes_to_hhmm,
    parse_sum,
)

logger = logging.getLogger(__name__)
router = Router()


class PendingScreenshot(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        pending = await user_pending_payment(message.from_user.id)
        return pending is not None


def _name(message: Message) -> str:
    user = message.from_user
    if not user:
        return "Foydalanuvchi"
    return " ".join(p for p in [user.first_name, user.last_name] if p).strip() or user.full_name


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user:
        await upsert_user(user.id, user.username, _name(message))
    settings = await get_settings()
    name = settings.get("stadium_name") or "Mini Stadion"
    address = settings.get("stadium_address") or ""
    try:
        lat = float(settings.get("stadium_lat") or 41.311081)
        lon = float(settings.get("stadium_lon") or 69.240562)
    except ValueError:
        lat, lon = 41.311081, 69.240562

    await message.answer_venue(
        latitude=lat,
        longitude=lon,
        title=name,
        address=address or "Mini stadion",
    )
    text = (
        f"Assalomu alaykum, <b>{_name(message)}</b>!\n\n"
        f"<b>{name}</b> ga xush kelibsiz.\n"
        "Bron qilish va bo'sh vaqtlarni ko'rish uchun pastdagi "
        "<b>🏟️ Bron qilish</b> tugmasini bosing — Mini App ochiladi."
    )
    await message.answer(text, reply_markup=open_app_keyboard(), parse_mode="HTML")
    await message.answer("Pastdagi menyudan ham Mini Appni ochishingiz mumkin.", reply_markup=main_keyboard(user.id if user else None))


@router.message(F.web_app_data)
async def from_mini_app(message: Message) -> None:
    if not message.from_user or not message.web_app_data:
        return
    try:
        payload = json.loads(message.web_app_data.data or "{}")
        book_date = str(payload.get("date") or "")
        start_min = int(payload["start_min"])
        end_min = int(payload["end_min"])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        await message.answer("Bron ma'lumoti noto'g'ri. Qayta urinib ko'ring.")
        return
    try:
        await place_booking(
            message.from_user.id,
            message.from_user.username,
            _name(message),
            book_date,
            start_min,
            end_min,
        )
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_keyboard(message.from_user.id))


@router.message(F.text == "📍 Lokatsiya")
@router.message(Command("location"))
async def cmd_location(message: Message) -> None:
    settings = await get_settings()
    name = settings.get("stadium_name") or "Mini Stadion"
    address = settings.get("stadium_address") or "Manzil"
    try:
        lat = float(settings.get("stadium_lat") or 0)
        lon = float(settings.get("stadium_lon") or 0)
    except ValueError:
        await message.answer("Lokatsiya hali kiritilmagan. Admin sozlamalardan manzilni qo'ying.")
        return
    await message.answer_venue(latitude=lat, longitude=lon, title=name, address=address)


@router.message(F.text == "ℹ️ Yordam")
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_markup=main_keyboard(message.from_user.id if message.from_user else None))


@router.message(F.text == "📰 Yangiliklar")
@router.message(Command("news"))
async def cmd_news(message: Message) -> None:
    items = await latest_news(10)
    if not items:
        await message.answer("Hozircha yangilik yo'q.")
        return
    chunks: list[str] = []
    for item in items:
        date = (item["created_at"] or "")[:10]
        chunks.append(f"<b>{item['title']}</b>\n{item['body']}\n<i>{date}</i>")
    text = "\n\n────────\n\n".join(chunks)
    if len(text) > 3900:
        text = text[:3900] + "…"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📅 Mening bronlarim")
@router.message(Command("my"))
async def cmd_my_bookings(message: Message) -> None:
    if not message.from_user:
        return
    rows = await user_bookings(message.from_user.id, 15)
    if not rows:
        await message.answer("Sizda hali bron yo'q. Mini App orqali vaqt band qiling.")
        return
    lines = ["<b>Sizning bronlaringiz</b>\n"]
    for b in rows:
        lines.append(
            f"#{b['id']} • {format_uz_date(b['book_date'])}\n"
            f"{display_range(b['start_min'], b['end_min'])}  —  {format_sum(b['price'])} so'm\n"
            f"{STATUS_TEXT.get(b['status'], b['status'])}"
        )
    await message.answer("\n\n".join(lines), parse_mode="HTML")


@router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def back_to_user(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    await message.answer("Asosiy menyu", reply_markup=main_keyboard(uid))


@router.message(F.text == "❌ Bekor")
async def cancel_any(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    kb = admin_keyboard() if is_admin(uid) else main_keyboard(uid)
    await message.answer("Bekor qilindi.", reply_markup=kb)


@router.message(PendingScreenshot(), F.photo | F.document)
async def receive_screenshot(message: Message, bot: Bot, state: FSMContext) -> None:
    if not message.from_user:
        return
    pending = await user_pending_payment(message.from_user.id)
    if not pending:
        return
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        file_id = message.document.file_id
    if not file_id:
        await message.answer("Iltimos, to'lov chekini rasm qilib yuboring.")
        return

    updated = await set_booking_status(pending["id"], "pending_review", screenshot_file_id=file_id)
    await state.clear()
    await message.answer(
        "Skrinshot qabul qilindi. Admin tekshirgach, sizga javob yuboriladi.",
        reply_markup=main_keyboard(message.from_user.id),
    )
    user = message.from_user
    caption = booking_card(updated or pending, user.username, _name(message))
    caption += "\n\nTo'lov skrinshoti. Tasdiqlaysizmi?"
    from app.config import ADMIN_IDS

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=booking_admin_keyboard(pending["id"]),
            )
        except Exception:
            logger.exception("Admin %s ga skrinshot yuborilmadi", admin_id)


@router.callback_query(F.data.startswith("bk:"))
async def on_booking_decision(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Faqat admin", show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, action, sid = parts
    booking = await get_booking(int(sid))
    if not booking:
        await callback.answer("Bron topilmadi", show_alert=True)
        return
    if booking["status"] not in {"pending_payment", "pending_review"}:
        await callback.answer("Bu bron allaqachon ko'rib chiqilgan", show_alert=True)
        return

    if action == "ok":
        await set_booking_status(booking["id"], "confirmed")
        await callback.answer("Tasdiqlandi")
        text = (
            "✅ To'lovingiz tasdiqlandi!\n\n"
            f"📅 {format_uz_date(booking['book_date'])}\n"
            f"🕐 {display_range(booking['start_min'], booking['end_min'])} "
            f"({duration_text(booking['start_min'], booking['end_min'])})\n"
            "Stadion sizni kutadi ⚽"
        )
        try:
            await bot.send_message(booking["telegram_id"], text)
        except Exception:
            logger.exception("Foydalanuvchiga tasdiq yuborilmadi")
        note = f"✅ Bron #{booking['id']} tasdiqlandi"
    else:
        await set_booking_status(booking["id"], "rejected")
        await callback.answer("Bekor qilindi")
        text = (
            "❌ Bron bekor qilindi.\n\n"
            "To'lov tasdiqlanmadi yoki vaqt bo'shatildi. "
            "Savol bo'lsa, admin bilan bog'laning. Vaqt yana yashil holatga qaytdi."
        )
        try:
            await bot.send_message(booking["telegram_id"], text)
        except Exception:
            logger.exception("Foydalanuvchiga rad javobi yuborilmadi")
        note = f"❌ Bron #{booking['id']} bekor qilindi"

    try:
        if callback.message:
            if callback.message.caption:
                await callback.message.edit_caption(
                    caption=(callback.message.caption or "") + f"\n\n{note}",
                    reply_markup=None,
                )
            else:
                await callback.message.edit_text(
                    (callback.message.html_text or callback.message.text or "") + f"\n\n{note}",
                    reply_markup=None,
                )
    except Exception:
        if callback.message:
            await callback.message.answer(note)


# ── Admin ──────────────────────────────────────────────────────────────────


@router.message(F.text == "⚙️ Admin panel")
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("Bu bo'lim faqat admin uchun.")
        return
    await state.clear()
    settings = await get_settings()
    await message.answer(
        "<b>Admin panel</b>\n\n"
        f"Stadion: {settings.get('stadium_name')}\n"
        f"1 soat: <b>{format_sum(int(settings.get('hourly_price') or 0))} so'm</b>\n"
        f"Ish vaqti: {minutes_to_hhmm(int(settings.get('open_min') or 0))} – "
        f"{minutes_to_hhmm(int(settings.get('close_min') or 1440))}",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "💳 Kartalar")
async def admin_cards(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    settings = await get_settings()
    await message.answer(cards_text(settings), parse_mode="HTML", reply_markup=cards_keyboard())


@router.callback_query(F.data.startswith("set:"))
async def admin_set_field(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Faqat admin", show_alert=True)
        return
    field = (callback.data or "").split(":", 1)[-1]
    mapping = {
        "card_click": (AdminStates.card_click, "Click karta raqamini yuboring (16 xonali)."),
        "card_payme": (AdminStates.card_payme, "Payme karta raqamini yuboring."),
        "card_uzcard": (AdminStates.card_uzcard, "Uzcard/Humo raqamini yuboring."),
        "card_other": (AdminStates.card_other_name, "To'lov tizimi nomini yuboring (masalan: Uzum)."),
        "card_holder": (AdminStates.card_holder, "Karta egasining F.I.Sh. ini yuboring."),
    }
    if field not in mapping:
        await callback.answer()
        return
    st, prompt = mapping[field]
    await state.set_state(st)
    await callback.answer()
    if callback.message:
        await callback.message.answer(prompt, reply_markup=cancel_kb())


@router.message(AdminStates.card_click)
@router.message(AdminStates.card_payme)
@router.message(AdminStates.card_uzcard)
async def save_card(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    current = await state.get_state()
    key = {
        AdminStates.card_click.state: "card_click",
        AdminStates.card_payme.state: "card_payme",
        AdminStates.card_uzcard.state: "card_uzcard",
    }.get(current or "")
    if not key:
        return
    number = format_card(message.text or "")
    if len(number.replace(" ", "")) < 13:
        await message.answer("Karta raqami noto'g'ri. Qayta yuboring.")
        return
    await set_setting(key, number.replace(" ", ""))
    await state.clear()
    await message.answer(f"Saqlandi: <code>{number}</code>", parse_mode="HTML", reply_markup=admin_keyboard())


@router.message(AdminStates.card_other_name)
async def save_other_name(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await state.update_data(other_name=(message.text or "").strip())
    await state.set_state(AdminStates.card_other)
    await message.answer("Endi shu tizimning karta raqamini yuboring.")


@router.message(AdminStates.card_other)
async def save_other_card(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    number = format_card(message.text or "")
    data = await state.get_data()
    await set_setting("card_other_name", data.get("other_name") or "Boshqa")
    await set_setting("card_other", number.replace(" ", ""))
    await state.clear()
    await message.answer(f"Saqlandi: {data.get('other_name')} — <code>{number}</code>", parse_mode="HTML", reply_markup=admin_keyboard())


@router.message(AdminStates.card_holder)
async def save_holder(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await set_setting("card_holder", (message.text or "").strip())
    await state.clear()
    await message.answer("Karta egasi saqlandi.", reply_markup=admin_keyboard())


@router.message(F.text == "💰 Narx")
async def admin_price(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    settings = await get_settings()
    current = format_sum(int(settings.get("hourly_price") or 0))
    await state.set_state(AdminStates.hourly_price)
    await message.answer(
        f"Hozirgi 1 soat narxi: <b>{current} so'm</b>\n\n"
        "Yangi narxni yuboring. Masalan: <code>60000</code> yoki <code>60 000</code>.\n"
        "Yarim soat avtomatik hisoblanadi (30 000).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.hourly_price)
async def save_price(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = parse_sum(message.text or "")
    if value is None or value <= 0:
        await message.answer("Faqat raqam yuboring, masalan: 60 000")
        return
    await set_setting("hourly_price", str(value))
    await state.clear()
    await message.answer(
        f"1 soat narxi: <b>{format_sum(value)} so'm</b>\n"
        f"30 daqiqa: <b>{format_sum(value // 2)} so'm</b>\n"
        f"1 soat 30 daqiqa: <b>{format_sum(value + value // 2)} so'm</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "🕐 Ish vaqti")
async def admin_hours(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.open_hour)
    await message.answer(
        "Ish vaqtini <code>06:00-24:00</code> formatida yuboring.\n"
        "Masalan: <code>07:00-23:00</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.open_hour)
async def save_hours(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    raw = (message.text or "").replace(" ", "").replace("–", "-").replace("—", "-")
    if "-" not in raw:
        await message.answer("Format: 07:00-23:00")
        return
    left, right = raw.split("-", 1)
    try:
        open_min = hhmm_to_minutes(left)
        close_min = 24 * 60 if right.startswith("24") else hhmm_to_minutes(right)
    except (ValueError, IndexError):
        await message.answer("Vaqt noto'g'ri. Masalan: 06:00-24:00")
        return
    if close_min <= open_min:
        await message.answer("Yopilish vaqti ochilishdan keyin bo'lishi kerak.")
        return
    await set_setting("open_min", str(open_min))
    await set_setting("close_min", str(close_min))
    await state.clear()
    await message.answer(
        f"Ish vaqti: {minutes_to_hhmm(open_min)} – {minutes_to_hhmm(close_min)}",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "📍 Stadion manzili")
async def admin_address(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.stadium_name)
    await message.answer("Stadion nomini yuboring. Masalan: Mini Stadion Chirchiq", reply_markup=cancel_kb())


@router.message(AdminStates.stadium_name)
async def save_stadium_name(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    if message.location:
        await set_setting("stadium_lat", str(message.location.latitude))
        await set_setting("stadium_lon", str(message.location.longitude))
        await state.clear()
        await message.answer("Lokatsiya saqlandi.", reply_markup=admin_keyboard())
        return
    await set_setting("stadium_name", (message.text or "").strip())
    await state.set_state(AdminStates.stadium_address)
    await message.answer("Endi manzilni yozing (ko'cha, tuman, shahar).")


@router.message(AdminStates.stadium_address)
async def save_address(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    if message.location:
        await set_setting("stadium_lat", str(message.location.latitude))
        await set_setting("stadium_lon", str(message.location.longitude))
        await state.clear()
        await message.answer("Lokatsiya saqlandi.", reply_markup=admin_keyboard())
        return
    await set_setting("stadium_address", (message.text or "").strip())
    await state.set_state(AdminStates.stadium_location)
    await message.answer("Endi Telegram orqali lokatsiyani yuboring (📎 → Location).")


@router.message(AdminStates.stadium_location)
async def save_location_any(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    if not message.location:
        await message.answer("Iltimos, lokatsiyani yuboring (📎 → Location).")
        return
    await set_setting("stadium_lat", str(message.location.latitude))
    await set_setting("stadium_lon", str(message.location.longitude))
    await state.clear()
    await message.answer("Stadion lokatsiyasi saqlandi.", reply_markup=admin_keyboard())


@router.message(F.text == "⏳ Kutilayotgan bronlar")
async def admin_pending(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    rows = await pending_review_bookings()
    if not rows:
        await message.answer("Kutilayotgan bron yo'q.")
        return
    for b in rows:
        text = booking_card(b, b.get("username"), b.get("full_name"))
        if b.get("screenshot_file_id"):
            await message.answer_photo(
                b["screenshot_file_id"],
                caption=text,
                parse_mode="HTML",
                reply_markup=booking_admin_keyboard(b["id"]),
            )
        else:
            await message.answer(text + "\n\n<i>Skrinshot hali yuborilmagan.</i>", parse_mode="HTML", reply_markup=booking_admin_keyboard(b["id"]))


@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    s = await stats()
    await message.answer(
        "<b>Statistika</b>\n\n"
        f"Foydalanuvchilar: {s['users']}\n"
        f"Bugungi tasdiqlangan bronlar: {s['confirmed_today']}\n"
        f"Kutilayotgan: {s['pending']}\n"
        f"Jami tasdiqlangan: {s['confirmed_all']}",
        parse_mode="HTML",
    )


@router.message(F.text == "✍️ Yangilik qo'shish")
async def admin_news_start(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.news_title)
    await message.answer("Yangilik sarlavhasini yuboring.", reply_markup=cancel_kb())


@router.message(AdminStates.news_title)
async def admin_news_title(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminStates.news_body)
    await message.answer("Yangilik matnini yuboring.")


@router.message(AdminStates.news_body)
async def admin_news_body(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    title = data.get("title") or "Yangilik"
    body = (message.text or "").strip()
    news = await add_news(title, body)
    await state.update_data(news_id=news["id"], title=title, body=body)
    await state.set_state(AdminStates.news_broadcast)
    await message.answer(
        f"Yangilik saqlandi.\n\n<b>{title}</b>\n{body}\n\nBarchaga yuborilsinmi?",
        parse_mode="HTML",
        reply_markup=news_broadcast_kb(),
    )


@router.callback_query(F.data.in_({"news:send", "news:save"}))
async def admin_news_broadcast(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Faqat admin", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()
    await callback.answer()
    if callback.data == "news:save":
        if callback.message:
            await callback.message.answer("Saqlandi. Foydalanuvchilar «Yangiliklar» dan o'qiydi.", reply_markup=admin_keyboard())
        return
    title = data.get("title") or "Yangilik"
    body = data.get("body") or ""
    text = f"📰 <b>{title}</b>\n\n{body}"
    sent = 0
    failed = 0
    for uid in await list_user_ids():
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
    if callback.message:
        await callback.message.answer(
            f"Yuborildi: {sent} ta. Yetib bormadi: {failed} ta.",
            reply_markup=admin_keyboard(),
        )
