"""
Ephemeral Messages Service Utility — Bot API 10.2

Unified helper for sending, editing, and deleting ephemeral messages in Telegram groups.
Messages sent ephemerally are visible ONLY to the receiver_user_id and the bot.

Features:
- Wraps `app.services.ephemeral_service.ephemeral_tracker`
- Graceful fallback: if chat is private, or ephemeral send fails (e.g. older library/API version or restriction),
  optionally falls back to a regular message or logs cleanly without throwing exceptions.
- Handles ephemeral_message_id for editing and deletion.
"""

from __future__ import annotations

from typing import Any

from aiogram import Bot

from app.logger import get_logger
from app.services.ephemeral_service import ephemeral_tracker

log = get_logger("utils.ephemeral")


async def send_ephemeral_or_fallback(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    text: str,
    *,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
    fallback_to_regular: bool = False,
    auto_delete_prev: bool = True,
) -> int | None:
    """
    Send an ephemeral message to receiver_user_id in chat_id.

    Args:
        bot: Aiogram Bot instance
        chat_id: Target group chat ID
        receiver_user_id: Target user ID who will see the message
        text: Message text (HTML/Markdown)
        parse_mode: Formatting mode (default "HTML")
        reply_markup: Optional InlineKeyboardMarkup
        fallback_to_regular: If True and ephemeral fails (e.g., private chat), send standard message
        auto_delete_prev: If True, auto-delete previously tracked ephemeral for this (chat, user)

    Returns:
        ephemeral_message_id (int) if sent as ephemeral, or None.
    """
    if not receiver_user_id or not chat_id:
        return None

    try:
        # Use ephemeral_tracker for tracking and sending
        eph_id = await ephemeral_tracker.send(
            bot=bot,
            chat_id=chat_id,
            user_id=receiver_user_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            auto_delete_prev=auto_delete_prev,
        )
        if eph_id is not None:
            return eph_id

    except Exception as exc:
        log.debug("send_ephemeral_or_fallback error chat=%d user=%d: %s", chat_id, receiver_user_id, exc)

    # Fallback to standard message if requested (or in private chat)
    if fallback_to_regular:
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return msg.message_id
        except Exception as exc:
            log.warning("Fallback send_message failed chat=%d: %s", chat_id, exc)

    return None


async def edit_ephemeral_or_fallback(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    text: str,
    *,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
    ephemeral_id: int | None = None,
) -> bool:
    """Edit an ephemeral message for receiver_user_id in chat_id."""
    try:
        return await ephemeral_tracker.edit(
            bot=bot,
            chat_id=chat_id,
            user_id=receiver_user_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            ephemeral_id=ephemeral_id,
        )
    except Exception as exc:
        log.debug("edit_ephemeral_or_fallback failed chat=%d user=%d: %s", chat_id, receiver_user_id, exc)
        return False


async def delete_ephemeral_or_fallback(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    *,
    ephemeral_id: int | None = None,
) -> bool:
    """Delete an ephemeral message for receiver_user_id in chat_id."""
    try:
        return await ephemeral_tracker.delete(
            bot=bot,
            chat_id=chat_id,
            user_id=receiver_user_id,
            ephemeral_id=ephemeral_id,
        )
    except Exception as exc:
        log.debug("delete_ephemeral_or_fallback failed chat=%d user=%d: %s", chat_id, receiver_user_id, exc)
        return False
