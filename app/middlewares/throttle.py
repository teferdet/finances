"""
Throttle middleware — rate-limits users to prevent abuse.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import get_settings
from app.logger import get_logger

log = get_logger("throttle")


class ThrottleMiddleware(BaseMiddleware):
    """Simple per-user rate limiter (in-memory)."""

    def __init__(self) -> None:
        super().__init__()
        s = get_settings().security
        self.max_requests = s.rate_limit_requests
        self.window = s.rate_limit_window_sec
        self._hits: Dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            uid = user.id
            now = time.monotonic()
            hits = self._hits.setdefault(uid, [])
            # Purge old hits
            hits[:] = [t for t in hits if now - t < self.window]
            if len(hits) >= self.max_requests:
                log.warning("Throttled user %d (%d reqs in %ds)", uid, len(hits), self.window)
                return  # silently drop
            hits.append(now)

            # Periodic cleanup
            if len(self._hits) > 5000:
                self._cleanup(now)

        return await handler(event, data)

    def _cleanup(self, now: float) -> None:
        stale = [k for k, v in self._hits.items() if not v or now - v[-1] > self.window * 2]
        for k in stale:
            del self._hits[k]
