from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    hourly_price = State()
    card_click = State()
    card_payme = State()
    card_uzcard = State()
    card_other_name = State()
    card_other = State()
    card_holder = State()
    stadium_name = State()
    stadium_address = State()
    stadium_location = State()
    open_hour = State()
    news_title = State()
    news_body = State()
    news_broadcast = State()


class UserStates(StatesGroup):
    waiting_screenshot = State()
