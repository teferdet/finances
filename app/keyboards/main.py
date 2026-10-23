"""
Reply keyboards — main currency keyboard and helpers.
"""

from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from app.config import get_currencies_data
from app.db import get_db

DEFAULT_MAIN_CURRENCIES = [
    ("🇺🇸", "USD"),
    ("🇪🇺", "EUR"),
    ("🇬🇧", "GBP"),
    ("🇨🇭", "CHF"),
    ("🇵🇱", "PLN"),
    ("🇺🇦", "UAH"),
]


def _build_reply_keyboard(currencies: list[tuple[str, str]], resize: bool = True) -> ReplyKeyboardMarkup:
    """Build a reply keyboard from (emoji, code) tuples — 3 per row."""
    buttons: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for emoji, code in currencies:
        text = f"{emoji} {code}" if emoji else code
        row.append(KeyboardButton(text=text))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=resize)


async def get_main_keyboard(user_id: int | None = None) -> ReplyKeyboardMarkup:
    """Get the user's personalised main keyboard (or default)."""
    currencies = DEFAULT_MAIN_CURRENCIES
    resize = True  # default: small buttons

    if user_id:
        try:
            from app.cqrs.read.users import get_user_view

            user_view = await get_user_view(user_id)
            if user_view.main_menu:
                currencies = _map_codes(user_view.main_menu)
            if user_view.big_buttons:
                resize = False  # big buttons = resize disabled
        except Exception:
            pass

    return _build_reply_keyboard(currencies, resize=resize)


def _map_codes(codes: list[str]) -> list[tuple[str, str]]:
    """Map currency codes → (emoji, code) using currencies_data.json."""
    data = get_currencies_data()
    code_to_emoji = {c["code"]: c.get("emoji", "") for c in data}
    result = [(code_to_emoji.get(c, ""), c) for c in codes]
    return result if result else DEFAULT_MAIN_CURRENCIES
