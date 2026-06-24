"""
i18n middleware — resolves user language and injects it into handler data.

Every handler receives ``data["lang"]`` (str) and ``data["i18n"]`` (I18n obj).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.db import get_db
from app.i18n import get_i18n


class I18nMiddleware(BaseMiddleware):
    """Outer middleware that sets lang + i18n for every update."""

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
            # Add activity tracking in the background
            import asyncio
            from datetime import datetime

            async def _track_activity(uid: int) -> None:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                db_ = get_db()
                try:
                    await db_["Users"].update_one(
                        {"_id": uid},
                        {"$set": {"last_active": now}, "$inc": {"stats.total_requests": 1}}
                    )
                    await db_["DailyStats"].update_one(
                        {"_id": today_str},
                        {"$inc": {"requests": 1}},
                        upsert=True
                    )
                except Exception:
                    pass

            asyncio.create_task(_track_activity(user.id))

            # 1) Check DB for saved preference
            db = get_db()
            try:
                doc = await db["Users"].find_one({"_id": user.id}, {"Language": 1})
                if doc and doc.get("Language") in i18n.supported:
                    lang = doc["Language"]
                elif user.language_code and user.language_code in i18n.supported:
                    lang = user.language_code
            except Exception:
                if user.language_code and user.language_code in i18n.supported:
                    lang = user.language_code

        data["lang"] = lang
        return await handler(event, data)
