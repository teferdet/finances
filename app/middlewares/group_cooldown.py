"""
Group Cooldown Middleware — per-chat rate limiter for passive auto-conversion.

Prevents the bot from flooding active groups with conversion replies.
Only affects group/supergroup messages that trigger auto-conversion
(not explicit /rate commands or callback queries).

Separate from RateLimitMiddleware (which is per-user).
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from app.logger import get_logger

log = get_logger("group_cooldown")

# Default cooldown: 5 seconds between auto-conversion replies per chat
DEFAULT_COOLDOWN_SEC = 5


class GroupCooldownMiddleware(BaseMiddleware):
    """
    Per-chat cooldown for group auto-conversion messages.

    When a group message triggers auto-conversion, the chat_id is recorded.
    Subsequent auto-conversion attempts within the cooldown window are
    silently dropped.

    This middleware only fires for group/supergroup Message updates.
    It sets ``data["group_cooldown_ok"]`` to True/False so handlers can
    decide whether to proceed. Commands (text starting with "/") are
    always allowed through.
    """

    def __init__(self, cooldown_sec: int = DEFAULT_COOLDOWN_SEC) -> None:
        self.cooldown_sec = cooldown_sec
        # chat_id → last auto-conversion timestamp (monotonic)
        self._last_reply: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # Only apply to groups
        if event.chat.type not in ("group", "supergroup"):
            data["group_cooldown_ok"] = True
            return await handler(event, data)

        text = event.text or ""

        # Commands always pass through (e.g. /rate, /group_settings)
        if text.startswith("/"):
            data["group_cooldown_ok"] = True
            return await handler(event, data)

        # Check cooldown
        chat_id = event.chat.id
        now = time.monotonic()
        last = self._last_reply.get(chat_id, 0.0)

        if now - last < self.cooldown_sec:
            data["group_cooldown_ok"] = False
        else:
            data["group_cooldown_ok"] = True

        result = await handler(event, data)

        # If the handler actually replied (result is not None or handler ran),
        # update the timestamp. We mark it here so that only actual replies
        # reset the cooldown — if handler returned early (no currency found),
        # cooldown is not consumed.
        # The handler sets data["group_did_reply"] = True when it sends a message.
        if data.get("group_did_reply"):
            self._last_reply[chat_id] = now

        # Periodic cleanup of stale entries
        if len(self._last_reply) > 5000:
            cutoff = now - self.cooldown_sec * 10
            self._last_reply = {
                k: v for k, v in self._last_reply.items() if v > cutoff
            }

        return result
