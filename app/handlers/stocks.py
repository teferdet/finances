"""
Stocks handler — /stocks command.
"""

from __future__ import annotations


from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import get_db
from app.i18n import I18n

router = Router(name="stocks")


@router.message(Command("stocks"))
async def cmd_stocks(message: Message, i18n: I18n, lang: str) -> None:
    db = get_db()
    user_doc = await db["Users"].find_one({"_id": message.from_user.id}, {"Stocks": 1})
    user_stocks = (user_doc or {}).get("Stocks", [])

    stocks_doc = await db["Crypto&Stocks"].find_one({"_id": "stocks"})
    if not stocks_doc:
        await message.answer(str(i18n.get("stocks.not_available", lang)))
        return

    lines: list[str] = []
    for symbol in user_stocks:
        if symbol in stocks_doc and isinstance(stocks_doc[symbol], (list, tuple)):
            item = stocks_doc[symbol]
            if len(item) >= 4:
                name, _, price, currency_sym = item
                lines.append(f"💵 {name}: {round(float(price), 4)}{currency_sym}")

    if not lines:
        await message.answer(str(i18n.get("stocks.empty_portfolio", lang)))
        return

    update = stocks_doc.get("update", [])
    header = str(i18n.get("stocks.header", lang))
    if update and len(update) >= 2:
        header += f" ({update[0]}, {update[1]})"

    text = f"{header}\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="HTML")
