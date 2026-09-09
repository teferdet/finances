"""
Rate Limiting Middleware for aiogram 3.x.

M-4 fix: upgraded from in-memory-only to a Redis-backed sliding window.
• When Redis is available: uses sorted sets (ZREMRANGEBYSCORE + ZADD + ZCARD)
  for a true sliding window that persists across restarts and works correctly
  with multiple bot instances.
• When Redis is unavailable: falls back to the original in-process deque,
  providing the same behaviour as before with zero configuration change needed.

Admin users (static and dynamic) are always exempt from rate limiting.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """
    Sliding-window rate limiter middleware.
    Default: 20 requests per 60-second window per user.

    Backend selection (evaluated on every request):
    • Redis available   → Redis sorted-set sliding window (distributed, persistent).
    • Redis unavailable → in-process deque (resets on restart, single-instance only).
    """

    def __init__(
        self,
        limit: int = 20,
        window: int = 60,
        admin_ids: list[int] | None = None,
        max_message_length: int = 1000,
    ) -> None:
        self.limit = limit
        self.window = window
        self.admin_ids: set[int] = set(admin_ids or [])
        self.max_message_length = max_message_length
        # Fallback in-memory buckets: user_id → deque of monotonic timestamps
        self._buckets: dict[int, deque] = defaultdict(deque)
        # Track users who already received a rate-limit warning (suppress repeats)
        self._warned: set[int] = set()

    # ── In-memory fallback ───────────────────────────────────────────────────

    def _mem_is_allowed(self, user_id: int) -> bool:
        """Sliding window using an in-process deque. Not persistent across restarts."""
        now = time.monotonic()
        bucket = self._buckets[user_id]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True

    # ── Redis sliding window ─────────────────────────────────────────────────

    async def _redis_is_allowed(self, user_id: int) -> bool:
        """
        Sliding-window check using a Redis sorted set (M-4 fix).

        Key schema : ``rl:<user_id>``
        Each request adds an entry scored by the current epoch timestamp.
        Old entries outside the window are pruned atomically in the same pipeline.
        Falls back to _mem_is_allowed() if Redis is unavailable or errors.
        """
        try:
            from app import redis_client as _rc  # import module to read live _redis ref

            r = _rc._redis  # None when Redis was not configured or connection failed
            if r is None:
                return self._mem_is_allowed(user_id)

            key = f"rl:{user_id}"
            now = time.time()
            cutoff = now - self.window
            member = f"{now:.6f}"  # unique member per request

            async with r.pipeline(transaction=False) as pipe:
                pipe.zremrangebyscore(key, 0, cutoff)   # evict expired entries
                pipe.zadd(key, {member: now})            # record this request
                pipe.zcard(key)                          # count in-window entries
                pipe.expire(key, self.window + 1)        # auto-expire the key
                results = await pipe.execute()

            count: int = results[2]
            if count > self.limit:
                # Over limit — roll back the zadd we just performed
                await r.zrem(key, member)
                return False
            return True

        except Exception as exc:
            logger.debug(
                "Redis rate-limit error for user %s: %s — falling back to memory",
                user_id, exc,
            )
            return self._mem_is_allowed(user_id)

    # ── Middleware entry point ────────────────────────────────────────────────

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

        # Exempt admins (static settings list + runtime dynamic admins)
        from app.state import dynamic_admin_ids

        if user_id is None or user_id in self.admin_ids or user_id in dynamic_admin_ids:
            return await handler(event, data)

        # Enforce max message length for incoming user messages
        if isinstance(event, Message) and event.text:
            if self.max_message_length > 0 and len(event.text) > self.max_message_length:
                logger.warning(
                    "Message dropped: length %d exceeds max_message_length=%d for user_id=%s",
                    len(event.text),
                    self.max_message_length,
                    user_id,
                )
                return None

        allowed = await self._redis_is_allowed(user_id)

        if allowed:
            self._warned.discard(user_id)
            return await handler(event, data)

        # ── Rate limit exceeded ──────────────────────────────────────────────
        logger.warning("Rate limit exceeded for user_id=%s", user_id)

        if user_id not in self._warned:
            self._warned.add(user_id)
            bot = data.get("bot")
            if bot:
                chat_id: int | None = None
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
                        await bot.send_message(chat_id, text)
                    except Exception as exc:
                        logger.debug("Failed to send rate limit warning: %s", exc)

        return None  # Drop the update silently
