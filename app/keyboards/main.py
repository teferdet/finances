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


def _build_reply_keyboard(currencies: list[tuple[str, str]]) -> ReplyKeyboardMarkup:
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
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def get_main_keyboard(user_id: int | None = None) -> ReplyKeyboardMarkup:
    """Get the user's personalised main keyboard (or default)."""
    currencies = DEFAULT_MAIN_CURRENCIES

    if user_id:
        try:
            db = get_db()
            doc = await db["Users"].find_one({"_id": user_id}, {"MainMenu": 1})
            if doc and doc.get("MainMenu"):
                custom_codes: list[str] = doc["MainMenu"]
                currencies = _map_codes(custom_codes)
        except Exception:
            pass

    return _build_reply_keyboard(currencies)


def _map_codes(codes: list[str]) -> list[tuple[str, str]]:
    """Map currency codes → (emoji, code) using currencies_data.json."""
    data = get_currencies_data()
    code_to_emoji = {c["code"]: c.get("emoji", "") for c in data}
    result = [(code_to_emoji.get(c, ""), c) for c in codes]
    return result if result else DEFAULT_MAIN_CURRENCIES
