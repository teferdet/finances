"""
Stocks handler — /stocks command.
"""

import asyncio

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import get_db
from app.i18n import I18n
from app.utils.draft import finish_initial_message_draft, process_initial_message_draft

router = Router(name="stocks")


async def _get_stocks_text(user_id: int, i18n: I18n, lang: str) -> str:
    db = get_db()
    user_doc = await db["Users"].find_one({"_id": user_id}, {"Stocks": 1})
    user_stocks = (user_doc or {}).get("Stocks", [])

    stocks_doc = await db["Crypto&Stocks"].find_one({"_id": "stocks"})
    if not stocks_doc:
        return str(i18n.get("stocks.not_available", lang))

    lines: list[str] = []
    for symbol in user_stocks:
        if symbol in stocks_doc and isinstance(stocks_doc[symbol], (list, tuple)):
            item = stocks_doc[symbol]
            if len(item) >= 4:
                name, _, price, currency_sym = item
                lines.append(f"💵 {name}: {round(float(price), 4)}{currency_sym}")

    if not lines:
        return str(i18n.get("stocks.empty_portfolio", lang))

    update = stocks_doc.get("update", [])
    header = str(i18n.get("stocks.header", lang))
    if update and len(update) >= 2:
        header += f" ({update[0]}, {update[1]})"

    return f"{header}\n\n" + "\n".join(lines)


@router.message(Command("stocks"))
async def cmd_stocks(message: Message, i18n: I18n, lang: str) -> None:
    loading_text = str(i18n.get("stocks.loading", "Stocks loading..."))
    task = asyncio.create_task(_get_stocks_text(message.from_user.id, i18n, lang))
    was_loading, text_out = await process_initial_message_draft(message, task, loading_text)

    await finish_initial_message_draft(message, text_out, was_loading)
    await message.answer(text_out, parse_mode="HTML")
