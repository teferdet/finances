"""
Inline query handler — handles @bot_username <query> anywhere.
"""

from __future__ import annotations

import re
import hashlib
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.db import get_db
from app.utils.text_processing import TextProcessing
from app.services.parser_service import convert_currencies, get_currencies_info
from app.i18n import I18n

router = Router(name="inline_query")


@router.inline_query()
async def inline_calculator(inline_query: InlineQuery, i18n: I18n, lang: str) -> None:
    query = inline_query.query.strip()
    if not query:
        # Prompt user to type something
        return

    parsed = TextProcessing(query)
    data = parsed.get_results()

    if not data:
        # Not a valid currency request
        return

    user_id = inline_query.from_user.id
    db = get_db()

    # Try to get user's fiat output preferences
    user = await db["Users"].find_one({"_id": user_id}, {"Fiat currency": 1})
    output = (user or {}).get("Fiat currency", [])
    if not output:
        output = ["USD", "EUR", "UAH", "GBP", "PLN"]

    codes = parsed.get_codes()
    index = 0 if any(c in ["BTC", "ETH"] for c in codes) else 1

    import asyncio
    convert_task = asyncio.create_task(convert_currencies(data, output, index))
    done, pending = await asyncio.wait([convert_task], timeout=0.5)
    
    if not done:
        t_loading = str(i18n.get("exchange rate.loading_title", lang))
        t_desc = str(i18n.get("exchange rate.loading_desc", lang))
        t_msg = str(i18n.get("exchange rate.loading_msg", lang))
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id="loading_id",
                    title=t_loading,
                    description=t_desc,
                    input_message_content=InputTextMessageContent(
                        message_text=t_msg
                    ),
                )
            ],
            cache_time=0,
            is_personal=True,
        )
        return

    result = convert_task.result()

    if result in ("server error", "bad request"):
        return

    # Get emojis for the title
    all_info = await get_currencies_info()
    info_map = {i["code"]: i for i in all_info}

    articles = []

    for code, amount in data:
        ci = info_map.get(code, {})
        emoji = ci.get("emoji", "")
        symbol = ci.get("symbol", "")

        title = f"{emoji} {amount} {code}".strip()

        # Calculate result specifically for this one
        single_all_res = await convert_currencies([(code, amount)], output, index)
        if single_all_res in ("server error", "bad request"):
            continue

        desc_lines = [line for line in single_all_res.split("\n") if line.strip()]
        desc_all = " | ".join(desc_lines[:3]) + ("..." if len(desc_lines) > 3 else "")

        # 1. Option: All Currencies
        t_all = str(i18n.get("inline mode.all_currencies", lang) or "All Selected Currencies")

        articles.append(
            InlineQueryResultArticle(
                id=hashlib.sha256(f"{code}_{amount}_ALL".encode()).hexdigest()[:32],
                title=f"🌐 {t_all} ({len(output)})",
                description=desc_all,
                hide_url=True,
                thumbnail_url="https://flagcdn.com/w160/un.jpg",
                input_message_content=InputTextMessageContent(
                    message_text=f"💱 <b>{title}</b>\n\n{single_all_res}", parse_mode="HTML"
                ),
            )
        )

        # 2. Options: Individual currencies
        for line in desc_lines:
            match = re.search(r"([A-Z0-9]{2,10}):", line)
            if not match:
                continue
            target_code = match.group(1)
            target_ci = info_map.get(target_code, {})

            # Name of target currency for extra info
            target_name = target_ci.get("name", target_code)
            target_emoji = target_ci.get("emoji", "")

            # Format: 🇪🇺 EUR - Euro
            item_title = f"{target_emoji} {target_code} — {target_name}".strip()

            # Description: 🇪🇺 EUR: 92.40€
            item_desc = line.strip()

            articles.append(
                InlineQueryResultArticle(
                    id=hashlib.sha256(f"{code}_{amount}_{target_code}".encode()).hexdigest()[:32],
                    title=item_title,
                    description=item_desc,
                    hide_url=True,
                    thumbnail_url=f"https://flagcdn.com/w160/{target_code[:2].lower()}.jpg",
                    input_message_content=InputTextMessageContent(
                        message_text=f"💱 <b>{title}</b> ➡️ <b>{item_desc}</b>", parse_mode="HTML"
                    ),
                )
            )

    if articles:
        await inline_query.answer(
            articles,
            cache_time=5,  # Cache briefly
            is_personal=True,
        )
