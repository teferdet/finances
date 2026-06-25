"""
Crypto handler — /crypto command and crypto callback conversion.
"""

from __future__ import annotations

import re
from time import strftime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.db import get_db
from app.i18n import I18n
from app.keyboards.inline import crypto_keypad

router = Router(name="crypto")


async def _get_crypto_data(currency: str, amount: float, user_id: int, i18n: I18n, lang: str) -> str:
    """Retrieve and format cryptocurrency data for a user."""
    db = get_db()
    crypto_doc = await db["Crypto&Stocks"].find_one({"_id": "crypto"})
    if not crypto_doc:
        return str(i18n.get("crypto.no_data", lang))

    if currency not in crypto_doc:
        return str(i18n.get("crypto.not_found", lang)).format(currency=currency)

    currency_data = crypto_doc[currency]

    user_doc = await db["Users"].find_one({"_id": user_id}, {"Crypto currency": 1})
    user_crypto = (user_doc or {}).get("Crypto currency", ["BTC", "ETH"])

    lines: list[str] = []
    for coin_code, item in currency_data.items():
        if coin_code in user_crypto and isinstance(item, list) and len(item) >= 3:
            name, price, symbol = item[0], float(item[1]), item[2]
            calc = round(price * amount, 4)
            lines.append(f"💵 {name}/{currency.upper()} {calc}{symbol}")

    return "\n".join(lines) if lines else str(i18n.get("crypto.empty", lang))


@router.message(Command("crypto"))
async def cmd_crypto(message: Message, i18n: I18n, lang: str) -> None:
    from app.utils.text_processing import TextProcessing

    text = message.text or ""
    parsed = TextProcessing(text)

    amount = 1.0
    currency = "USD"

    if parsed.results:
        # Avoid picking up the command itself as a code if it wasn't valid, but TextProcessing handles that.
        # However, TextProcessing might not detect USD if they just type `/crypto 100`
        amount = parsed.results[0].amount
        currency = parsed.results[0].code
    else:
        nums = re.findall(r"\d+\.*\d*", text)
        if nums:
            amount = float(nums[0])

    value = await _get_crypto_data(currency, amount, message.from_user.id, i18n, lang)
    day = strftime("%d.%m.%y")
    text = i18n.get("exchange rate.sub rate", lang)
    text = str(text).format(day, value)

    await message.answer(text, reply_markup=crypto_keypad(amount, currency))


@router.callback_query(F.data.startswith("crypto "))
async def cb_crypto(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    await call.answer()
    parts = call.data.split()
    if len(parts) < 3:
        return
    currency = parts[1]
    amount = float(parts[2])

    value = await _get_crypto_data(currency, amount, call.from_user.id, i18n, lang)
    day = strftime("%d.%m.%y")
    text = i18n.get("exchange rate.sub rate", lang)
    text = str(text).format(day, value)

    try:
        await call.message.edit_text(text, reply_markup=crypto_keypad(amount, currency))
    except Exception:
        pass
