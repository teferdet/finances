"""
Chat admin verification — checks if a user is a Telegram group admin.

Uses bot.get_chat_member() with in-memory TTL caching (via app.cache)
to avoid excessive Telegram API calls.

This is completely independent from ADMIN_IDS / _is_admin() which controls
the global /admin panel.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from app.cache import cache
from app.logger import get_logger

log = get_logger("chat_admin")

# Cache key format and TTL
_CACHE_PREFIX = "chat_admin"
_CACHE_TTL = 60  # seconds


async def is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """
    Check whether *user_id* is a creator or administrator in *chat_id*.

    Results are cached for 60 seconds per (chat_id, user_id) pair
    using the project's existing MemoryCache singleton.

    Returns False on any Telegram API error (e.g. bot was removed from group).
    """
    cache_key = f"{_CACHE_PREFIX}:{chat_id}:{user_id}"

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        member = await bot.get_chat_member(chat_id, user_id)
        result = member.status in (
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
        )
    except Exception as exc:
        log.debug("get_chat_member failed for chat=%d user=%d: %s", chat_id, user_id, exc)
        result = False

    await cache.set(cache_key, result, ttl=_CACHE_TTL)
    return result


async def get_chat_admin_list(bot: Bot, chat_id: int) -> list[dict]:
    """
    Return a list of dicts with basic info about each admin in the chat.

    Each dict has keys: user_id, name, username, status.
    Returns an empty list on API error.
    """
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except Exception as exc:
        log.debug("get_chat_administrators failed for chat=%d: %s", chat_id, exc)
        return []

    result = []
    for member in admins:
        user = member.user
        name_parts = [user.first_name or ""]
        if user.last_name:
            name_parts.append(user.last_name)
        result.append(
            {
                "user_id": user.id,
                "name": " ".join(name_parts).strip() or str(user.id),
                "username": user.username,
                "status": member.status,
                "is_bot": user.is_bot,
            }
        )
    return result
