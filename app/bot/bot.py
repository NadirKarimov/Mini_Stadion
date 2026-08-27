from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.bot.handlers import router
from app.config import BOT_TOKEN, WEBAPP_URL

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)


async def setup_menu() -> None:
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Bron qilish", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    except Exception:
        logger.exception("Menu button o'rnatilmadi — WEBAPP_URL HTTPS bo'lishi kerak")


async def notify_user_payment(telegram_id: int, text: str) -> None:
    try:
        from app.bot.keyboards import main_keyboard

        await bot.send_message(telegram_id, text, reply_markup=main_keyboard(telegram_id))
    except Exception:
        logger.exception("Foydalanuvchiga to'lov xabari yuborilmadi")


async def notify_admins(text: str) -> None:
    from app.config import ADMIN_IDS

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception("Admin %s ga xabar yuborilmadi", admin_id)
