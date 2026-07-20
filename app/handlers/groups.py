"""
Group message handler — auto-converts currencies mentioned in group chats.
Also handles bot being added to / removed from chats via my_chat_member.
"""

from __future__ import annotations

from time import strftime

from aiogram import F, Router
from aiogram.types import ChatMemberUpdated, Message

from app.config import get_currencies_data, get_settings
from app.db import get_db
from app.i18n import I18n
from app.keyboards.inline import group_delete_kb
from app.repositories.communities import add_group_to_community, get_or_create_community
from app.repositories.groups import toggle_group_active, upsert_group_from_chat_member
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.text_processing import TextProcessing

router = Router(name="groups")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(message: Message, i18n: I18n, lang: str) -> None:
    """Process currency mentions in group messages."""
    text = message.text or ""
    parsed = TextProcessing(text)
    data = parsed.get_results()
    if not data:
        return

    db = get_db()
    # Check both the legacy Groups collection and the new groups collection
    group = await db["groups"].find_one(
        {"chat_id": message.chat.id}, {"is_active": 1, "settings": 1}
    )
    if not group or not group.get("is_active", False):
        # Fallback: legacy uppercase collection
        legacy = await db["Groups"].find_one(
            {"_id": message.chat.id}, {"Input": 1, "Output": 1, "Status": 1}
        )
        if not legacy or legacy.get("Status") != "Active":
            return
        allowed_input = legacy.get("Input", [])
        output = legacy.get("Output", [])
    else:
        # Check if auto-conversion is disabled by group admin
        group_settings = group.get("settings", {})
        if not group_settings.get("auto_convert", True):
            return

        allowed_input = group.get("Input", ["USD", "EUR"])
        output = group.get("Output", ["UAH"])

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

        # Notify main admin
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
