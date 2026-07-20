"""
Ephemeral Message Service — Bot API 10.2

Provides helpers for sending, editing, and deleting ephemeral messages
(messages visible only to a specific user in a group chat).

API surface used:
    bot.send_message(..., receiver_user_id=user_id)      → ephemeral_message_id
    bot.edit_ephemeral_message_text(...)
    bot.delete_ephemeral_message(...)

EphemeralTracker keeps an in-memory map of active ephemeral messages
so callers can update/remove them without storing IDs themselves.
"""

from __future__ import annotations

import asyncio
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.logger import get_logger

log = get_logger("ephemeral")

# ── In-memory tracker ─────────────────────────────────────────────────────────


class EphemeralTracker:
    """
    Tracks active ephemeral messages per (chat_id, user_id) slot.

    Usage:
        tracker = EphemeralTracker()

        eph_id = await tracker.send(bot, chat_id, user_id, "Fetching data…")
        await asyncio.sleep(3)
        await tracker.edit(bot, chat_id, user_id, "Done ✅")
        await tracker.delete(bot, chat_id, user_id)
    """

    def __init__(self) -> None:
        # key: (chat_id, user_id)  value: ephemeral_message_id
        self._store: dict[tuple[int, int], int] = {}
        self._lock = asyncio.Lock()

    def _key(self, chat_id: int, user_id: int) -> tuple[int, int]:
        return (chat_id, user_id)

    async def send(
        self,
        bot: Bot,
        chat_id: int,
        user_id: int,
        text: str,
        *,
        parse_mode: str = "HTML",
        reply_markup: Any = None,
        auto_delete_prev: bool = True,
    ) -> int | None:
        """
        Send an ephemeral message to a specific user in a group.
        If auto_delete_prev=True, deletes any previously tracked ephemeral
        for this (chat_id, user_id) pair before sending the new one.

        Returns the ephemeral_message_id or None on failure.
        """
        async with self._lock:
            if auto_delete_prev:
                await self._delete_stored(bot, chat_id, user_id)

        try:
            sent = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                receiver_user_id=user_id,
            )
            eph_id: int | None = getattr(sent, "ephemeral_message_id", None)
            if eph_id is not None:
                async with self._lock:
                    self._store[self._key(chat_id, user_id)] = eph_id
            return eph_id
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            log.warning("send_ephemeral failed chat=%d user=%d: %s", chat_id, user_id, exc)
            return None

    async def edit(
        self,
        bot: Bot,
        chat_id: int,
        user_id: int,
        text: str,
        *,
        parse_mode: str = "HTML",
        reply_markup: Any = None,
        ephemeral_id: int | None = None,
    ) -> bool:
        """
        Edit a tracked (or explicitly provided) ephemeral message.
        Returns True on success.
        """
        eph_id = ephemeral_id
        if eph_id is None:
            async with self._lock:
                eph_id = self._store.get(self._key(chat_id, user_id))
        if eph_id is None:
            log.debug("edit_ephemeral: no tracked message for chat=%d user=%d", chat_id, user_id)
            return False

        try:
            await bot.edit_ephemeral_message_text(
                chat_id=chat_id,
                receiver_user_id=user_id,
                ephemeral_message_id=eph_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            log.debug("edit_ephemeral failed chat=%d user=%d: %s", chat_id, user_id, exc)
            return False

    async def delete(
        self,
        bot: Bot,
        chat_id: int,
        user_id: int,
        *,
        ephemeral_id: int | None = None,
    ) -> bool:
        """
        Delete a tracked (or explicitly provided) ephemeral message.
        Removes it from the tracker on success.
        Returns True on success.
        """
        async with self._lock:
            eph_id = ephemeral_id or self._store.get(self._key(chat_id, user_id))
        if eph_id is None:
            return False

        try:
            await bot.delete_ephemeral_message(
                chat_id=chat_id,
                receiver_user_id=user_id,
                ephemeral_message_id=eph_id,
            )
            async with self._lock:
                self._store.pop(self._key(chat_id, user_id), None)
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            log.debug("delete_ephemeral failed chat=%d user=%d: %s", chat_id, user_id, exc)
            async with self._lock:
                self._store.pop(self._key(chat_id, user_id), None)
            return False

    async def _delete_stored(self, bot: Bot, chat_id: int, user_id: int) -> None:
        """Internal: delete stored ephemeral without acquiring lock (caller holds it)."""
        key = self._key(chat_id, user_id)
        eph_id = self._store.get(key)
        if eph_id is None:
            return
        try:
            await bot.delete_ephemeral_message(
                chat_id=chat_id,
                receiver_user_id=user_id,
                ephemeral_message_id=eph_id,
            )
        except Exception:
            pass
        self._store.pop(key, None)

    def get_id(self, chat_id: int, user_id: int) -> int | None:
        """Synchronously get tracked ephemeral_message_id without I/O."""
        return self._store.get(self._key(chat_id, user_id))

    def clear(self, chat_id: int, user_id: int) -> None:
        """Remove tracking entry without sending any API call."""
        self._store.pop(self._key(chat_id, user_id), None)


# ── Module-level singleton — shared across all services ───────────────────────

ephemeral_tracker = EphemeralTracker()


# ── Standalone helpers (no tracker) ──────────────────────────────────────────


async def send_ephemeral(
    bot: Bot,
    chat_id: int,
    user_id: int,
    text: str,
    *,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
) -> int | None:
    """
    Fire-and-forget ephemeral send. Does NOT track the message.
    Returns ephemeral_message_id or None.
    """
    try:
        sent = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            receiver_user_id=user_id,
        )
        return getattr(sent, "ephemeral_message_id", None)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        log.warning("send_ephemeral failed chat=%d user=%d: %s", chat_id, user_id, exc)
        return None


async def delete_ephemeral(
    bot: Bot,
    chat_id: int,
    user_id: int,
    ephemeral_id: int,
) -> bool:
    """Delete an ephemeral message by its ID."""
    try:
        await bot.delete_ephemeral_message(
            chat_id=chat_id,
            receiver_user_id=user_id,
            ephemeral_message_id=ephemeral_id,
        )
        return True
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
