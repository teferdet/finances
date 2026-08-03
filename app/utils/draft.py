"""
Telegram Bot API sendMessageDraft utility helper.

Official API: https://core.telegram.org/bots/api#sendmessagedraft

Key facts from the official docs:
- draft_id: required, non-zero, stable per animation session. Changes with the same
  draft_id are animated smoothly. NOT the same as reply_to_message_id.
- text: optional. Passing empty string shows a "Thinking..." placeholder.
- The draft is ephemeral: auto-expires after 30 seconds.
- There is NO explicit clear/delete draft API. The intended flow is:
    sendMessageDraft(draft_id, animated text...) -> sendMessage(final text)
  The client hides the draft automatically when the real sendMessage arrives.
- DO NOT use message.message_id as draft_id. Generate a unique non-zero int instead.

Rules:
- Animation only applies to private chats for the first (non-inline) user message.
- Inline callbacks (CallbackQuery) must NOT use these helpers.
- All config parameters come from DraftSettings (config/settings.json -> "draft" section).
- Message is a frozen Pydantic model, so draft_id is stored in a module-level dict
  keyed by (chat_id, message_id), NOT as an attribute on the Message object.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from aiogram.types import Message
from app.config import get_settings

log = logging.getLogger("draft")

# Module-level store: (chat_id, message_id) -> draft_id
# Message is frozen (Pydantic), so we cannot store state on it directly.
_draft_id_store: dict[tuple[int, int], int] = {}


def _new_draft_id() -> int:
    """Generate a unique non-zero draft_id per animation session."""
    return int(time.monotonic() * 1000) & 0x7FFF_FFFF or 1


def _store_draft_id(message: Message, draft_id: int) -> None:
    _draft_id_store[(message.chat.id, message.message_id)] = draft_id


def _pop_draft_id(message: Message) -> int | None:
    return _draft_id_store.pop((message.chat.id, message.message_id), None)


async def send_message_draft(
    bot,
    chat_id: int,
    draft_id: int,
    text: str,
    parse_mode: str = "HTML",
) -> bool:
    """
    Send draft text via Telegram Bot API sendMessageDraft method.
    draft_id must be non-zero and stable for the whole animation session.
    Returns True if successful, False otherwise.
    """
    params: dict = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    # 1. Try native aiogram method if available (future-proof)
    if hasattr(bot, "send_message_draft"):
        try:
            await bot.send_message_draft(**params)
            return True
        except Exception:
            pass  # fall through to raw request

    # 2. Raw Bot API request via make_request
    try:
        await bot.make_request("sendMessageDraft", params)
        return True
    except Exception as exc:
        log.debug("sendMessageDraft failed: %s", exc)
        return False


async def _animate_loading_draft(
    bot,
    chat_id: int,
    draft_id: int,
    loading_text: str,
    task: asyncio.Task,
    interval: float = 0.25,
) -> None:
    """Animate draft text smoothly while task is pending."""
    base_text = re.sub(r"^[^\w\s]+", "", loading_text).strip().rstrip(".")
    states = [
        f"🔄 {base_text}...",
        f"⏳ {base_text}.",
        f"✨ {base_text}..",
        f"📊 {base_text}...",
    ]
    idx = 0
    try:
        while not task.done():
            await send_message_draft(
                bot,
                chat_id=chat_id,
                draft_id=draft_id,
                text=states[idx % len(states)],
            )
            idx += 1
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass  # cancelled normally when main task finishes


async def process_initial_message_draft(
    message: Message,
    task: asyncio.Task,
    loading_text: str = "Loading...",
) -> tuple[bool, Any]:
    """
    Process async task for initial user messages (Message only, NOT CallbackQuery).

    If task finishes within loading_threshold_sec -> no animation, returns immediately.
    If it takes longer AND chat is private AND draft.enabled:
      - Generates a unique draft_id for this animation session.
      - Stores draft_id in module-level dict (Message is frozen, can't set attributes).
      - Animates the draft field while waiting.

    Returns (was_loading, result).
    Re-raises task exception if the task failed.
    """
    cfg = get_settings().draft
    is_private = message.chat.type == "private"

    done, _ = await asyncio.wait([task], timeout=cfg.loading_threshold_sec)

    was_loading = False
    anim_task: asyncio.Task | None = None

    if not done:
        was_loading = True
        if is_private and cfg.enabled:
            draft_id = _new_draft_id()
            _store_draft_id(message, draft_id)
            # Keep a strong reference so GC does not collect the task
            anim_task = asyncio.create_task(
                _animate_loading_draft(
                    message.bot,
                    message.chat.id,
                    draft_id,
                    loading_text,
                    task,
                    interval=cfg.animation_interval_sec,
                )
            )

        try:
            await task
        except Exception:
            raise
        finally:
            # Always cancel the animation task once the main work is done
            if anim_task is not None and not anim_task.done():
                anim_task.cancel()
                try:
                    await anim_task
                except asyncio.CancelledError:
                    pass

    # Propagate any exception from the task (covers was_loading=False path too)
    exc = task.exception()
    if exc is not None:
        raise exc

    return was_loading, task.result()


async def finish_initial_message_draft(
    message: Message,
    text_out: str,
    was_loading: bool,
) -> None:
    """
    If was_loading in a private chat:
      1. Retrieves the draft_id stored by process_initial_message_draft.
      2. Sends text_out as a final draft preview (the "streaming complete" moment).
      3. Sleeps preview_delay_sec so the user sees the full text briefly.
      4. The caller then calls message.answer() which causes the client to auto-hide
         the ephemeral draft (no manual clearing needed per official docs).
    """
    cfg = get_settings().draft
    if not (was_loading and message.chat.type == "private" and cfg.enabled):
        return

    draft_id = _pop_draft_id(message)
    if draft_id is None:
        return

    # Show the final complete text as streaming preview
    await send_message_draft(
        message.bot,
        chat_id=message.chat.id,
        draft_id=draft_id,
        text=text_out,
    )
    # Brief pause so the user sees the full result before the real message lands
    await asyncio.sleep(cfg.preview_delay_sec)
