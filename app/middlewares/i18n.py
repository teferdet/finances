"""
i18n middleware — resolves user language and injects it into handler data.

Every handler receives ``data["lang"]`` (str) and ``data["i18n"]`` (I18n obj).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.cqrs.read.users import get_user_view
from app.cqrs.write.activity import activity_buffer
from app.i18n import get_i18n


class I18nMiddleware(BaseMiddleware):
    """Outer middleware that sets lang + i18n for every update using CQRS read model and write-behind."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        i18n = get_i18n()
        data["i18n"] = i18n

        # Determine user
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        lang = i18n.default_lang
        if user:
            # 1) Non-blocking in-memory activity tracking (write-behind)
            await activity_buffer.record_activity(user.id)

            # 2) Fast in-memory UserView read model (CQRS)
            try:
                user_view = await get_user_view(user.id)
                data["user_view"] = user_view
                if user_view.language in i18n.supported:
                    lang = user_view.language
                elif user.language_code and user.language_code in i18n.supported:
                    lang = user.language_code
            except Exception:
                if user.language_code and user.language_code in i18n.supported:
                    lang = user.language_code

        data["lang"] = lang
        return await handler(event, data)
