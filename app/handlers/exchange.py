"""
Exchange rate handler — handles currency conversion in private chats.
Includes callback for alternative conversion.
"""

from __future__ import annotations

import asyncio
from time import strftime

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery

from app.db import get_db
from app.i18n import I18n
from app.config import get_currencies_data
from app.keyboards.inline import er_keypad
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.draft import (
    finish_initial_message_draft,
    process_initial_message_draft,
)
from app.utils.text_processing import TextProcessing

router = Router(name="exchange")


async def _calculate_bulk_expenses(
    data: list[tuple[str, float]],
    user_id: int,
    i18n: I18n,
    lang: str,
) -> str:
    db = get_db()
    user_doc = await db["Users"].find_one({"_id": user_id}, {"BaseCurrency": 1, "Fiat currency": 1, "NumberFormat": 1})
    u = user_doc or {}

    bc = u.get("BaseCurrency")
    if isinstance(bc, list) and bc and bc[0]:
        target_curr = bc[0]
    elif isinstance(bc, str) and bc:
        target_curr = bc
    else:
        fiats = u.get("Fiat currency", [])
        if fiats and isinstance(fiats, list) and fiats[0]:
            target_curr = fiats[0]
        else:
            from app.config import get_settings
            st = get_settings()
            target_curr = getattr(st, "default_currency", "USD")

    num_fmt = u.get("NumberFormat", "commas")
    from app.handlers.portfolio import _format_number

    title_str = str(i18n.get("calc.title", lang, target=target_curr))
    lines = [title_str]
    total_sum = 0.0

    for code, amount in data:
        res = await convert_currencies([(code, amount)], [target_curr], index=1)
        conv_val = 0.0
        import re
        numbers = re.findall(r"[\d\s,]+(?:\.\d+)?", res)
        if numbers:
            try:
                clean_num = numbers[-1].replace(" ", "").replace(",", "")
                conv_val = float(clean_num)
            except ValueError:
                conv_val = 0.0

        total_sum += conv_val
        sub_str = _format_number(conv_val, 2, fmt=num_fmt)
        amt_str = _format_number(amount, 2 if code not in ("BTC", "ETH") else 4, fmt=num_fmt)
        lines.append(f"• <b>{amt_str} {code}</b> ➔ {sub_str} {target_curr}")

    tot_str = _format_number(total_sum, 2, fmt=num_fmt)
    total_text = str(i18n.get("calc.total", lang, total=tot_str, currency=target_curr))
    lines.append("\n━━━━━━━━━━━━━━━━━━")
    lines.append(total_text)

    return "\n".join(lines)


@router.message(Command("calc"))
async def cmd_calc(message: Message, command: CommandObject, i18n: I18n, lang: str) -> None:
    """Calculate bulk expenses in multiple currencies."""
    args = command.args or ""
    if not args.strip():
        help_text = str(i18n.get("calc.help", lang))
        await message.answer(help_text, parse_mode="HTML")
        return

    text = args
    parsed = TextProcessing(text)
    data = parsed.get_results()

    if not data:
        await message.answer(str(i18n.get("exchange rate.input error", lang)), parse_mode="HTML")
        return

    loading_text = str(i18n.get("exchange rate.loading", lang))
    task = asyncio.create_task(_calculate_bulk_expenses(data, message.from_user.id, i18n, lang))
    was_loading, text_out = await process_initial_message_draft(message, task, loading_text)

    await finish_initial_message_draft(message, text_out, was_loading)
    await message.answer(text_out, parse_mode="HTML")


async def _get_user_fiat_currencies(user_id: int) -> list[str]:
    db = get_db()
    doc = await db["Users"].find_one({"_id": user_id}, {"Fiat currency": 1})
    return doc.get("Fiat currency", []) if doc else []


def format_header_item(code: str, amount: float, emoji: str, symbol: str, include_symbol: bool) -> str:
    """
    Format header item:
      - amount == 1: omit number (e.g. "🇺🇦 UAH" or "🇺🇦 UAH₴")
      - integer amount (e.g. 10.0): format without .0 (e.g. "🇺🇦 UAH 10" or "🇺🇦 UAH 10₴")
      - float amount (e.g. 0.5): format cleanly (e.g. "🇺🇦 UAH 0.5" or "🇺🇦 UAH 0.5₴")
    """
    sym_str = symbol if include_symbol else ""
    if abs(amount - 1.0) < 1e-9:
        amt_str = ""
    elif amount == int(amount):
        amt_str = f" {int(amount)}"
    else:
        amt_str = f" {amount:g}"

    emoji_str = f"{emoji} " if emoji else ""
    return f"{emoji_str}{code}{amt_str}{sym_str}".strip()


async def _format_info(currencies_data: list, i18n: I18n, lang: str, include_symbol: bool = True) -> str:
    """Build info string like '🇺🇦 UAH 10₴' (direct mode) or '🇺🇦 UAH 10' (reverse mode)."""
    info_parts: list[str] = []
    all_info = await get_currencies_info()
    info_map = {i["code"]: i for i in all_info}
    # Fallback from currencies_data.json
    cd_map = {e["code"]: e for e in get_currencies_data() if e.get("code")}

    for code, amount in currencies_data:
        ci = info_map.get(code, {})
        emoji = ci.get("emoji", "") or cd_map.get(code, {}).get("emoji", "")
        symbol = ci.get("symbol", "") or cd_map.get(code, {}).get("symbol", "")
        info_parts.append(format_header_item(code, amount, emoji, symbol, include_symbol))

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
    db = get_db()
    user_doc = await db["Users"].find_one({"_id": user_id}, {"Fiat currency": 1, "RateMode": 1})
    output = (user_doc or {}).get("Fiat currency", [])
    rate_mode = (user_doc or {}).get("RateMode", "direct")
    index = 0 if rate_mode == "reverse" else 1

    is_crypto = any(c in ["BTC", "ETH"] for c in codes)
    if is_crypto:
        index = 0

    if len(data) > 1:
        loading_text = str(i18n.get("exchange rate.loading", lang))
        task = asyncio.create_task(_calculate_bulk_expenses(data, message.from_user.id, i18n, lang))
        was_loading, text_out = await process_initial_message_draft(message, task, loading_text)
        await finish_initial_message_draft(message, text_out, was_loading)
        await message.answer(text_out, parse_mode="HTML")
        return

    keypad = None
    if len(codes) == 1 and not is_crypto:
        keypad = er_keypad(i18n, lang, data[0][0], data[0][1], index)

    loading_text = str(i18n.get("exchange rate.loading", lang))
    convert_task = asyncio.create_task(convert_currencies(data, output, index))
    was_loading, result = await process_initial_message_draft(message, convert_task, loading_text)

    day = strftime("%d.%m.%y")
    er_text = i18n.get_section("exchange rate", lang)

    if result in ("server error", "bad request"):
        text_out = str(er_text.get(result, result))
    else:
        include_sym = (index == 1)
        info = await _format_info(data, i18n, lang, include_symbol=include_sym)
        template = str(er_text.get("main rate", "Rate as of {}\n{}\n\n{}"))
        text_out = template.format(day, info, result)

    await finish_initial_message_draft(message, text_out, was_loading)
    await message.answer(text_out, reply_markup=keypad, parse_mode="HTML")


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

    if result in ("server error", "bad request"):
        text_out = str(er_text.get(result, result))
        keypad = None
    else:
        all_info = await get_currencies_info()
        info_map = {i["code"]: i for i in all_info}
        cd_map = {e["code"]: e for e in get_currencies_data() if e.get("code")}
        ci = info_map.get(currency, {})
        emoji = ci.get("emoji", "") or cd_map.get(currency, {}).get("emoji", "")
        symbol = ci.get("symbol", "") or cd_map.get(currency, {}).get("symbol", "")
        info = format_header_item(currency, amount, emoji, symbol, include_symbol=(new_index == 1))

        template = str(er_text.get("main rate", "Rate as of {}\n{}\n\n{}"))
        text_out = template.format(day, info, result)
        keypad = er_keypad(i18n, lang, currency, amount, new_index)

    try:
        await call.message.edit_text(text_out, reply_markup=keypad, parse_mode="HTML")
    except Exception:
        pass


@router.message(F.chat.type == "private")
async def private_fallback(message: Message, i18n: I18n, lang: str) -> None:
    await handle_exchange(message, i18n, lang)
