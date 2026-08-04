"""
Guest Mode Handler — Telegram Bot API 10.0+

Handles 'guest_message' updates — messages sent to chats where the bot is NOT
a member, via user @mention. The bot has access only to that single message.

Flow:
    User mentions @bot in a chat → Update.guest_message arrives
    → Bot parses the text for currency/crypto/stock requests
    → Responds via answerGuestQuery (InlineQueryResultArticle)

Constraints (Telegram API):
    - Response must be an InlineQueryResult object (not plain text)
    - Bot has NO access to chat history or member list
    - One response per guest_query_id
"""

from __future__ import annotations

import hashlib

from aiogram import F, Router
from aiogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)

from app.i18n import I18n
from app.logger import get_logger
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.text_processing import TextProcessing

log = get_logger("guest")
router = Router(name="guest")


def _short_id(seed: str) -> str:
    """Generate a deterministic short ID for InlineQueryResult."""
    return hashlib.md5(seed.encode(), usedforsecurity=False).hexdigest()[:8]


async def _build_currency_response(text: str, i18n: I18n, lang: str) -> str | None:
    """
    Attempt to parse currency conversion from message text.
    Returns formatted HTML response string, or None if nothing found.
    """
    parsed = TextProcessing(text)
    data = parsed.get_results()
    if not data:
        return None

    codes = parsed.get_codes()

    # Determine conversion index (0 = crypto, 1 = fiat)
    index = 0 if any(c in ("BTC", "ETH", "BNB", "SOL", "XRP") for c in codes) else 1

    # Try common output currencies
    output_candidates = [["USD", "EUR", "UAH"], ["UAH", "USD"], ["USD"]]
    result = None
    for output in output_candidates:
        r = await convert_currencies(data, output, index)
        if r not in ("server error", "bad request", None, ""):
            result = r
            break

    if not result:
        return None

    all_info = await get_currencies_info()
    info_map = {i["code"]: i for i in all_info}

    parts = []
    for code, amount in data:
        ci = info_map.get(code, {})
        emoji = ci.get("emoji", "")
        symbol = ci.get("symbol", "")
        parts.append(f"{emoji} {code} {amount}{symbol}")

    header = ", ".join(parts)
    return f"💱 {header}\n\n{result}"


# ── Guest Message Handler ─────────────────────────────────────────────────────


@router.guest_message(F.guest_query_id)
async def handle_guest_message(message: Message, i18n: I18n, lang: str) -> None:
    """
    Respond to a mention in a chat the bot is not a member of.
    Must reply via answerGuestQuery with an InlineQueryResult.
    """
    guest_query_id = message.guest_query_id
    text = message.text or message.caption or ""
    caller_user = message.guest_bot_caller_user
    caller_chat = message.guest_bot_caller_chat

    log.info(
        "Guest query: user=%s chat=%s query_id=%s text=%r",
        caller_user.id if caller_user else "?",
        caller_chat.id if caller_chat else "?",
        guest_query_id,
        text[:80],
    )

    # ── Try currency conversion ───────────────────────────────────────────────
    response_text = await _build_currency_response(text, i18n, lang)

    if response_text:
        title = str(i18n.get("guest.conversion_title", lang))
        description = str(i18n.get("guest.conversion_description", lang))
    else:
        # Generic help response
        response_text = str(i18n.get("guest.help_text", lang))
        title = str(i18n.get("guest.help_title", lang))
        description = str(i18n.get("guest.help_description", lang))

    result = InlineQueryResultArticle(
        id=_short_id(guest_query_id),
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=response_text,
            parse_mode="HTML",
        ),
    )

    try:
        await message.answer_guest_query(result=result)
    except Exception as exc:
        log.warning("answerGuestQuery failed for %s: %s", guest_query_id, exc)
