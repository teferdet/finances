"""
Exchange rate handler — handles currency conversion in private chats.
Includes callback for alternative conversion.
"""

from __future__ import annotations

from time import strftime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app.db import get_db
from app.i18n import I18n
from app.config import get_currencies_data
from app.keyboards.inline import er_keypad
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.text_processing import TextProcessing

router = Router(name="exchange")


async def _get_user_fiat_currencies(user_id: int) -> list[str]:
    db = get_db()
    doc = await db["Users"].find_one({"_id": user_id}, {"Fiat currency": 1})
    return doc.get("Fiat currency", []) if doc else []


async def _format_info(currencies_data: list, i18n: I18n, lang: str) -> str:
    """Build info string like '🇺🇸 USD 100$, 🇪🇺 EUR 50€'."""
    info_parts: list[str] = []
    all_info = await get_currencies_info()
    info_map = {i["code"]: i for i in all_info}
    # Fallback from currencies_data.json
    cd_map = {e["code"]: e for e in get_currencies_data() if e.get("code")}

    for code, amount in currencies_data:
        ci = info_map.get(code, {})
        emoji = ci.get("emoji", "") or cd_map.get(code, {}).get("emoji", "")
        symbol = ci.get("symbol", "") or cd_map.get(code, {}).get("symbol", "")
        info_parts.append(f"{emoji} {code} {amount}{symbol}")

    return ", ".join(info_parts)


async def handle_exchange(message: Message, i18n: I18n, lang: str) -> None:
    """Process currency conversion for a message."""
    text = message.text or ""
    parsed = TextProcessing(text)
    data = parsed.get_results()
    codes = parsed.get_codes()

    if not data:
        if text.startswith("/"):
            err = i18n.get("exchange rate.unknown command", lang)
        else:
            err = i18n.get("exchange rate.input error", lang)
        await message.answer(str(err), parse_mode="HTML")
        return

    user_id = message.from_user.id
    output = await _get_user_fiat_currencies(user_id)
    keypad = None
    index = 1

    is_crypto = any(c in ["BTC", "ETH"] for c in codes)
    if is_crypto:
        index = 0

    if len(codes) == 1 and not is_crypto:
        keypad = er_keypad(i18n, lang, data[0][0], data[0][1], index)

    result = await convert_currencies(data, output, index)

    day = strftime("%d.%m.%y")
    er_text = i18n.get_section("exchange rate", lang)

    if result in ("server error", "bad request"):
        text_out = str(er_text.get(result, result))
    else:
        info = await _format_info(data, i18n, lang)
        template = str(er_text.get("main rate", "Rate as of {}\n{}\n\n{}"))
        text_out = template.format(day, info, result)

    await message.answer(text_out, reply_markup=keypad)


# ── Callback for alternative conversion ─────────────────────────────


@router.callback_query(F.data.startswith("er "))
async def cb_alternative_convert(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    await call.answer()
    parts = call.data.split()
    if len(parts) < 4:
        return
    currency = parts[1]
    amount = float(parts[2])
    index = int(parts[3])

    user_id = call.from_user.id
    output = await _get_user_fiat_currencies(user_id)

    # Flip the index
    new_index = 0 if index == 1 else 1
    result = await convert_currencies([(currency, amount)], output, new_index)

    day = strftime("%d.%m.%y")
    er_text = i18n.get_section("exchange rate", lang)

    if result == "server error":
        text_out = str(er_text.get("server error", "Server error"))
        keypad = None
    else:
        all_info = await get_currencies_info()
        info_map = {i["code"]: i for i in all_info}
        cd_map = {e["code"]: e for e in get_currencies_data() if e.get("code")}
        ci = info_map.get(currency, {})
        emoji = ci.get("emoji", "") or cd_map.get(currency, {}).get("emoji", "")
        symbol = ci.get("symbol", "") or cd_map.get(currency, {}).get("symbol", "")
        info = f"{emoji} {currency} {amount}{symbol}"

        template = str(er_text.get("main rate", "Rate as of {}\n{}\n\n{}"))
        text_out = template.format(day, info, result)
        keypad = er_keypad(i18n, lang, currency, amount, new_index)

    try:
        await call.message.edit_text(text_out, reply_markup=keypad)
    except Exception:
        pass


@router.message(F.chat.type == "private")
async def private_fallback(message: Message, i18n: I18n, lang: str) -> None:
    await handle_exchange(message, i18n, lang)
