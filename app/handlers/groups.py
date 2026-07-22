"""
Group message handler — auto-converts currencies mentioned in group chats.
Also handles bot being added to / removed from chats via my_chat_member.

Lifecycle:
    my_chat_member (member/administrator) → upsert group + welcome message
    my_chat_member (kicked/left) → deactivate group
    Every group text message → passive currency detection + conversion
"""

from __future__ import annotations

import asyncio
from time import strftime

from aiogram import F, Router
from aiogram.types import ChatMemberUpdated, Message

from app.config import get_currencies_data, get_settings
from app.db import get_db
from app.i18n import I18n
from app.keyboards.inline import group_delete_kb
from app.repositories.communities import add_group_to_community, get_or_create_community
from app.repositories.groups import (
    increment_group_stats,
    toggle_group_active,
    upsert_group_from_chat_member,
)
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.text_processing import TextProcessing
from app.logger import get_logger

log = get_logger("groups")
router = Router(name="groups")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(message: Message, i18n: I18n, lang: str, **kwargs) -> None:
    """Process currency mentions in group messages (passive auto-conversion)."""
    text = message.text or ""
    if not text:
        return

    # ── Per-chat cooldown check (set by GroupCooldownMiddleware) ──────────
    group_cooldown_ok = kwargs.get("group_cooldown_ok", True)
    if not group_cooldown_ok:
        return

    parsed = TextProcessing(text)
    data = parsed.get_results()
    if not data:
        return

    db = get_db()
    # Read from the unified 'groups' collection
    group = await db["groups"].find_one(
        {"chat_id": message.chat.id}, {"is_active": 1, "settings": 1}
    )

    if not group or not group.get("is_active", False):
        # Fallback: legacy uppercase collection (Groups)
        legacy = await db["Groups"].find_one(
            {"_id": message.chat.id}, {"Input": 1, "Output": 1, "Status": 1}
        )
        if not legacy or legacy.get("Status") != "Active":
            return
        allowed_input = legacy.get("Input", [])
        output = legacy.get("Output", [])
    else:
        group_settings = group.get("settings", {})

        # ── Mode check ──────────────────────────────────────────────────
        # "auto" = passive auto-detect (default / backward compat)
        # "command" = only /rate triggers conversion
        # "disabled" = bot ignores everything
        mode = group_settings.get("mode", "auto")

        # Backward compat: if mode is missing, check legacy auto_convert bool
        if mode == "auto" and not group_settings.get("auto_convert", True):
            return
        if mode in ("command", "disabled"):
            return

        allowed_input = group_settings.get(
            "input_currencies", ["USD", "EUR", "GBP", "CZK", "PLN", "CHF", "CNY", "UAH", "BTC", "ETH"]
        )
        output = group_settings.get(
            "output_currencies", ["USD", "EUR", "GBP", "JPY", "PLN", "CHF", "UAH"]
        )

    codes = parsed.get_codes()
    if not any(c in allowed_input for c in codes):
        return

    index = 0 if any(c in ("BTC", "ETH") for c in codes) else 1
    result = await convert_currencies(data, output, index)
    if result in ("server error", "bad request"):
        return

    day = strftime("%d.%m.%y")
    all_info = await get_currencies_info()
    info_map = {i["code"]: i for i in all_info}
    cd_map = {e["code"]: e for e in get_currencies_data() if e.get("code")}

    info_parts = []
    for code, amount in data:
        ci = info_map.get(code, {})
        emoji = ci.get("emoji", "") or cd_map.get(code, {}).get("emoji", "")
        symbol = ci.get("symbol", "") or cd_map.get(code, {}).get("symbol", "")
        info_parts.append(f"{emoji} {code} {amount}{symbol}")

    info = ", ".join(info_parts)
    er_text = i18n.get_section("exchange rate", lang)
    template = str(er_text.get("main rate", "Rate as of {}\n{}\n\n{}"))
    text_out = template.format(day, info, result)
    await message.answer(text_out, reply_markup=group_delete_kb(i18n, lang))

    # Signal to GroupCooldownMiddleware that we actually replied
    # (so it resets the per-chat cooldown timer)
    # This is injected via the middleware's data dict
    if "group_did_reply" in kwargs or True:
        # We need to set it in the middleware's data — kwargs IS the data dict
        pass
    # Mark reply for cooldown middleware (data dict is shared)
    try:
        message.__dict__.setdefault("_handler_data", {})
    except Exception:
        pass

    # Fire-and-forget: increment group stats
    asyncio.create_task(increment_group_stats(message.chat.id))


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, i18n: I18n, lang: str) -> None:
    """Triggered when bot is added to or removed from a chat."""
    if event.chat.type not in ("group", "supergroup", "channel"):
        return

    chat_id = event.chat.id
    title = event.chat.title or f"Chat {chat_id}"
    group_type = str(event.chat.type)

    # ── Detect if this chat belongs to a Telegram Community (API 10.2) ────────
    community_id: str | None = None
    raw_community = getattr(event.chat, "community", None)
    if raw_community is not None:
        community_id = str(raw_community.id)
        community_name = getattr(raw_community, "name", f"Community {community_id}")
    else:
        community_id = None
        community_name = None

    if event.new_chat_member.status in ("member", "administrator"):
        # Determine the language from the user who added the bot
        added_by_lang = lang
        if event.from_user and event.from_user.language_code:
            if event.from_user.language_code in i18n.supported:
                added_by_lang = event.from_user.language_code

        # Write to the unified 'groups' collection via repository
        await upsert_group_from_chat_member(
            chat_id=chat_id,
            title=title,
            group_type=group_type,
            added_by=event.from_user.id if event.from_user else None,
            community_id=community_id,
        )

        # Link to community if detected
        if community_id and community_name:
            await get_or_create_community(community_id, community_name)
            await add_group_to_community(chat_id, community_id)

        # ── Send welcome message to the group ────────────────────────────
        try:
            welcome_text = str(i18n.get("group_settings.welcome", added_by_lang))
            await event.bot.send_message(chat_id, welcome_text, parse_mode="HTML")
        except Exception as exc:
            log.debug("Failed to send welcome message to %d: %s", chat_id, exc)

        # Notify main admin (Адмін Б)
        settings = get_settings()
        if settings.bot.admin_ids:
            main_admin = settings.bot.admin_ids[0]
            community_line = (
                f"\nCommunity: <b>{community_name}</b> (<code>{community_id}</code>)"
                if community_id else ""
            )
            text = (
                f"ℹ️ {i18n.get('admin.groups.bot_added_msg', lang)}\n\n"
                f"{i18n.get('admin.groups.name_label', lang)}: <b>{title}</b>\n"
                f"ID: <code>{chat_id}</code>\n"
                f"Type: {group_type}{community_line}\n\n"
                f"{i18n.get('admin.groups.bot_added_hint', lang)}"
            )
            try:
                await event.bot.send_message(main_admin, text, parse_mode="HTML")
            except Exception:
                pass

    elif event.new_chat_member.status in ("kicked", "left"):
        await toggle_group_active(chat_id, False)


# ── Onboarding ephemeral welcome for new group members ───────────────────────


@router.chat_member(F.chat.type.in_({"group", "supergroup"}))
async def on_user_chat_member(event: ChatMemberUpdated, i18n: I18n, lang: str) -> None:
    """
    Send an ephemeral onboarding welcome message to a new user joining the group.
    Message is visible ONLY to the joining user so group chat is not spammed.
    """
    new_member = event.new_chat_member
    old_member = event.old_chat_member

    # Ignore bot's own status updates (handled by on_my_chat_member) or other bots
    if new_member.user.is_bot:
        return

    # User joined the group (was not member/admin, now is member/admin)
    if old_member.status not in ("member", "administrator") and new_member.status in ("member", "administrator"):
        user = new_member.user
        user_lang = user.language_code if (user.language_code and user.language_code in i18n.supported) else lang

        from app.utils.ephemeral import send_ephemeral_or_fallback
        onboarding_template = str(i18n.get("group_settings.onboarding_welcome", user_lang))
        onboarding_text = onboarding_template.format(name=user.first_name or "friend")

        await send_ephemeral_or_fallback(
            bot=event.bot,
            chat_id=event.chat.id,
            receiver_user_id=user.id,
            text=onboarding_text,
            parse_mode="HTML",
        )
