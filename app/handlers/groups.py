"""
Group message handler — auto-converts currencies mentioned in group chats.
"""
from __future__ import annotations
from time import strftime
from aiogram import Router, F
from aiogram.types import Message
from app.db import get_db
from app.i18n import I18n
from app.keyboards.inline import group_delete_kb
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.text_processing import TextProcessing

router = Router(name="groups")

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(message: Message, i18n: I18n, lang: str) -> None:
    """Process currency mentions in group messages."""
    text = message.text or ""
    parsed = TextProcessing(text)
    data = parsed.get_results()
    if not data:
        return
    db = get_db()
    group = await db["Groups"].find_one(
        {"_id": message.chat.id}, {"Input": 1, "Output": 1, "Status": 1})
    if not group or group.get("Status") != "Active":
        return
    allowed_input = group.get("Input", [])
    codes = parsed.get_codes()
    if not any(c in allowed_input for c in codes):
        return
    output = group.get("Output", [])
    index = 0 if any(c in ["BTC", "ETH"] for c in codes) else 1
    result = await convert_currencies(data, output, index)
    if result in ("server error", "bad request"):
        return
    day = strftime("%d.%m.%y")
    all_info = await get_currencies_info()
    info_map = {i["code"]: i for i in all_info}
    info_parts = []
    for code, amount in data:
        ci = info_map.get(code, {})
        emoji = ci.get("emoji", "")
        symbol = ci.get("symbol", "")
        info_parts.append(f"{emoji} {code} {amount}{symbol}")
    info = ", ".join(info_parts)
    er_text = i18n.get_section("exchange rate", lang)
    template = str(er_text.get("main rate", "Rate as of {}\n{}\n\n{}"))
    text_out = template.format(day, info, result)
    await message.answer(text_out, reply_markup=group_delete_kb(i18n, lang))
