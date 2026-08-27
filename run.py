from __future__ import annotations

import asyncio
import logging
import sys

import uvicorn

from app.config import BOT_TOKEN, HOST, PORT
from app.db import expire_old_pending, init_db

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stadion")


async def expire_loop() -> None:
    from app.bot.bot import bot
    from app.utils import display_range, format_uz_date

    while True:
        try:
            expired = await expire_old_pending()
            for b in expired:
                try:
                    await bot.send_message(
                        b["telegram_id"],
                        "⏰ Vaqt tugadi: skrinshot yuborilmagani uchun bron bekor qilindi.\n"
                        f"{format_uz_date(b['book_date'])}  {display_range(b['start_min'], b['end_min'])}\n"
                        "Vaqt yana bo'sh (yashil).",
                    )
                except Exception:
                    logger.exception("Muddati o'tgan bron xabari yuborilmadi")
        except Exception:
            logger.exception("Expire loop xatosi")
        await asyncio.sleep(60)


async def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN.startswith("123456"):
        logger.error("BOT_TOKEN ni .env faylida yozing")
        sys.exit(1)

    await init_db()

    from app.db import set_on_change
    from app.snapshot import publish_snapshot, schedule_publish

    set_on_change(schedule_publish)
    try:
        await publish_snapshot()
    except Exception:
        logger.exception("Birinchi snapshot yozilmadi")

    from app.api.server import app as fastapi_app
    from app.bot.bot import bot, dp, setup_menu

    await setup_menu()

    config = uvicorn.Config(fastapi_app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)

    logger.info("Mini Stadion ishga tushdi  http://%s:%s", HOST, PORT)
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot),
        expire_loop(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
