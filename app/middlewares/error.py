"""
Error-catching middleware — wraps every handler in a try/except
so that no unhandled exception crashes the bot.
"""

from __future__ import annotations

import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.logger import get_logger

log = get_logger("error_mw")


class ErrorMiddleware(BaseMiddleware):
    """Global error catcher — logs exceptions, sends user a friendly message."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            log.error(
                "Unhandled exception in handler: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            # Try to notify the user
            try:
                if isinstance(event, Message):
                    await event.answer("😖 An error occurred. Please try again later.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("😖 Error. Try again.", show_alert=True)
            except Exception:
                pass
            return None
