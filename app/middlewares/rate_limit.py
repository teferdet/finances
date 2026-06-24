"""
Rate Limiting Middleware for aiogram 3.x.
Limits message frequency per user to prevent spam and DDoS-like behavior.
"""
import logging
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """
    Sliding window rate limiter.
    Default: max 20 requests per 60 seconds per user.
    Admin users are exempt.
    """

    def __init__(
        self,
        limit: int = 20,
        window: int = 60,
        admin_ids: list[int] | None = None,
    ) -> None:
        self.limit = limit
        self.window = window
        self.admin_ids: set[int] = set(admin_ids or [])
        # user_id -> deque of timestamps
        self._buckets: dict[int, deque] = defaultdict(deque)
        self._warned: set[int] = set()  # users who already got the warning message

    def _is_allowed(self, user_id: int) -> bool:
        now = time.monotonic()
        bucket = self._buckets[user_id]

        # Remove timestamps outside the window
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()

        if len(bucket) >= self.limit:
            return False

        bucket.append(now)
        return True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        # Skip rate limiting for admins or unknown users
        from app.state import dynamic_admin_ids
        if user_id is None or user_id in self.admin_ids or user_id in dynamic_admin_ids:
            return await handler(event, data)

        if self._is_allowed(user_id):
            # Reset warning flag once they're back under limit
            self._warned.discard(user_id)
            return await handler(event, data)

        # Rate limit exceeded
        logger.warning(f"Rate limit exceeded for user_id={user_id}")

        # Send warning only once per rate-limit episode
        if user_id not in self._warned:
            self._warned.add(user_id)
            bot = data.get("bot")
            if bot:
                chat_id = None
                if isinstance(event, Message):
                    chat_id = event.chat.id
                elif isinstance(event, CallbackQuery) and event.message:
                    chat_id = event.message.chat.id

                if chat_id:
                    try:
                        i18n = data.get("i18n")
                        lang = data.get("lang", "en")
                        text = "⚠️ Too many requests. Please slow down."
                        if i18n:
                            text = str(i18n.get("rate_limit.exceeded", lang))

                        await bot.send_message(
                            chat_id,
                            text,
                        )
                    except Exception as e:
                        logger.error(f"Failed to send rate limit warning: {e}")

        return None  # Drop the update
