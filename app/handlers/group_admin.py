"""
Group admin handler — /group_settings command, /rate command, /group_stats, and inline controls.

Allows real Telegram group administrators (creator / administrator) to manage
bot settings for their specific group chat without needing global ADMIN_IDS.

Callback data prefix: ``grp_settings:`` (distinct from ``admin_groups:``).

ANONYMOUS ADMIN HANDLING:
  When an admin sends messages with "Remain Anonymous" turned on, Telegram sends
  the message on behalf of GroupAnonymousBot (user_id = 1087968824).
  For security-critical actions, we detect GroupAnonymousBot and inform the user
  to temporarily switch to their personal user profile to adjust group settings.

TODO: Privacy Mode — the /group_settings and /rate commands always work because Telegram
      delivers commands regardless of privacy mode. However, auto-conversion
      of plain text like "100 USD" requires Privacy Mode to be DISABLED via @BotFather.
"""

from __future__ import annotations

from time import strftime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.cache import cache
from app.config import get_settings, get_currencies_data
from app.db import get_db
from app.i18n import I18n
from app.logger import get_logger
from app.keyboards.group_admin import (
    group_deactivate_confirm_kb,
    group_language_kb,
    group_settings_menu_kb,
)
from app.keyboards.inline import paginated_currency_keyboard
from app.repositories.groups import (
    get_group,
    get_group_settings,
    increment_group_stats,
    toggle_group_active,
    update_group_currencies,
    update_group_settings,
)
from app.services.parser_service import convert_currencies, get_currencies_info
from app.utils.chat_admin import get_chat_admin_list, is_chat_admin
from app.utils.text_processing import TextProcessing, strip_html

from app.utils.ephemeral import (
    delete_ephemeral_or_fallback,
    edit_ephemeral_or_fallback,
    send_ephemeral_or_fallback,
)

log = get_logger("group_admin")
router = Router(name="group_admin")

GROUP_ANONYMOUS_BOT_ID = 1087968824


async def _cache_key(user_id: int) -> str:
    return f"group_admin_settings:{user_id}"


async def _check_admin_permissions(event: Message | CallbackQuery, chat_id: int, i18n: I18n, lang: str) -> bool:
    """
    Verify if event sender is a group admin.
    Handles anonymous admin check (GroupAnonymousBot).
    """
    user = event.from_user
    if not user:
        return False

    # Check for anonymous admin
    if user.id == GROUP_ANONYMOUS_BOT_ID:
        anon_msg = str(i18n.get("group_settings.anon_admin", lang))
        if isinstance(event, Message):
            await send_ephemeral_or_fallback(
                event.bot, chat_id, user.id, anon_msg, parse_mode="HTML", fallback_to_regular=True
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(strip_html(anon_msg), show_alert=True)
        return False

    if not await is_chat_admin(event.bot, chat_id, user.id):
        denied_msg = str(i18n.get("group_settings.access_denied", lang))
        if isinstance(event, Message):
            await send_ephemeral_or_fallback(
                event.bot, chat_id, user.id, denied_msg, fallback_to_regular=True
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(strip_html(denied_msg), show_alert=True)
        return False
        return False

    return True


# ── /rate command (Manual group conversion for all members) ─────────────────


@router.message(Command("rate"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_rate(message: Message, i18n: I18n, lang: str) -> None:
    """Manual currency conversion command for group members — sent ephemerally by default."""
    text = message.text or ""
    user_id = message.from_user.id if message.from_user else 0
    chat_id = message.chat.id

    # Strip command part: "/rate 100 USD" -> "100 USD"
    args = text.split(maxsplit=1)
    query_text = args[1] if len(args) > 1 else ""

    if not query_text:
        usage = str(i18n.get("group_settings.rate_usage", lang))
        await send_ephemeral_or_fallback(
            message.bot, chat_id, user_id, usage, parse_mode="HTML", fallback_to_regular=True
        )
        return

    parsed = TextProcessing(query_text)
    data = parsed.get_results()
    if not data:
        err = i18n.get("exchange rate.input error", lang)
        await send_ephemeral_or_fallback(
            message.bot, chat_id, user_id, str(err), parse_mode="HTML", fallback_to_regular=True
        )
        return

    group = await get_group(chat_id)
    group_settings = (group or {}).get("settings", {})
    output = group_settings.get(
        "output_currencies", ["USD", "EUR", "GBP", "JPY", "PLN", "CHF", "UAH"]
    )

    codes = parsed.get_codes()
    index = 0 if any(c in ("BTC", "ETH") for c in codes) else 1
    result = await convert_currencies(data, output, index)

    if result in ("server error", "bad request"):
        err_msg = str(i18n.get(f"exchange rate.{result}", lang))
        await send_ephemeral_or_fallback(
            message.bot, chat_id, user_id, err_msg, fallback_to_regular=True
        )
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

    # Attach "📢 Share to Group" button so user can share rate publicly
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    share_label = str(i18n.get("group_settings.share_to_group", lang) or "📢 Share to Group")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=share_label, callback_data="grp_rate:share")]]
    )

    # Deliver ephemerally to caller
    sent_eph = await send_ephemeral_or_fallback(
        bot=message.bot,
        chat_id=chat_id,
        receiver_user_id=user_id,
        text=text_out,
        reply_markup=kb,
        parse_mode="HTML",
        fallback_to_regular=True,
    )

    await increment_group_stats(chat_id)


@router.callback_query(F.data == "grp_rate:share")
async def cb_rate_share(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    """Share ephemeral rate response publicly to the group chat."""
    text = call.message.text or call.message.caption or ""
    chat_id = call.message.chat.id
    from app.keyboards.inline import group_delete_kb

    try:
        await call.bot.send_message(chat_id, text, reply_markup=group_delete_kb(i18n, lang), parse_mode="HTML")
        await call.answer("Published to group!", show_alert=False)
        # Clean up ephemeral message if tracked
        if call.from_user:
            await delete_ephemeral_or_fallback(call.bot, chat_id, call.from_user.id)
    except Exception as exc:
        log.warning("cb_rate_share failed: %s", exc)
        await call.answer()


# ── /group_stats command ──────────────────────────────────────────────────────


@router.message(Command("group_stats"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_group_stats(message: Message, i18n: I18n, lang: str) -> None:
    """Show lightweight group usage stats (Адмін А only) — sent ephemerally."""
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0

    if not await _check_admin_permissions(message, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        denied = str(i18n.get("group_settings.access_denied", lang))
        await send_ephemeral_or_fallback(message.bot, chat_id, user_id, denied, fallback_to_regular=True)
        return

    title = group.get("title", message.chat.title or f"Chat {chat_id}")
    stats = group.get("stats", {})
    total_reqs = stats.get("total_requests", 0)
    is_active = "✅ Active" if group.get("is_active") else "⛔ Inactive"

    g_settings = group.get("settings", {})
    mode = g_settings.get("mode", "auto")
    in_curr = ", ".join(g_settings.get("input_currencies", [])) or "—"
    out_curr = ", ".join(g_settings.get("output_currencies", [])) or "—"

    template = str(i18n.get("group_settings.stats_title", lang))
    text = (
        f"{template}\n\n"
        f"<b>{title}</b>\n"
        f"Status: {is_active}\n"
        f"Mode: <code>{mode}</code>\n"
        f"Total conversions: <b>{total_reqs}</b>\n\n"
        f"📥 Triggers: {in_curr}\n"
        f"📤 Outputs: {out_curr}"
    )

    await send_ephemeral_or_fallback(
        message.bot, chat_id, user_id, text, parse_mode="HTML", fallback_to_regular=True
    )


# ── /group_settings ──────────────────────────────────────────────────────────


@router.message(Command("group_settings"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_group_settings(message: Message, i18n: I18n, lang: str) -> None:
    """Entry point — only real Telegram group admins may open this. Sent ephemerally."""
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0

    if not await _check_admin_permissions(message, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        denied = str(i18n.get("group_settings.access_denied", lang))
        await send_ephemeral_or_fallback(message.bot, chat_id, user_id, denied, fallback_to_regular=True)
        return

    settings = group.get("settings", {})
    group_lang = settings.get("language", lang)

    title = group.get("title", message.chat.title or f"Chat {chat_id}")
    text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
    kb = group_settings_menu_kb(chat_id, group, i18n, group_lang)

    await send_ephemeral_or_fallback(
        message.bot, chat_id, user_id, text, reply_markup=kb, parse_mode="HTML", fallback_to_regular=True
    )


# Reject /group_settings in private chats
@router.message(Command("group_settings"), F.chat.type == "private")
async def cmd_group_settings_private(message: Message, i18n: I18n, lang: str) -> None:
    await message.answer(str(i18n.get("group_settings.not_in_group", lang)))


# ── Callback: re-open main menu ──────────────────────────────────────────────


async def _edit_message_or_ephemeral(
    call: CallbackQuery,
    text: str,
    reply_markup: Any = None,
    parse_mode: str = "HTML",
) -> None:
    """Edit message or ephemeral message cleanly without raising Bad Request."""
    user_id = call.from_user.id if call.from_user else 0
    chat_id = call.message.chat.id if call.message else 0

    try:
        if call.message:
            await call.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
    except TelegramBadRequest as exc:
        msg_err = str(exc)
        if "message is not modified" in msg_err:
            return
        if "message to edit not found" not in msg_err:
            log.warning("edit_text TelegramBadRequest chat=%d: %s", chat_id, exc)

    edited = await edit_ephemeral_or_fallback(
        bot=call.bot,
        chat_id=chat_id,
        receiver_user_id=user_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    if not edited:
        await send_ephemeral_or_fallback(
            bot=call.bot,
            chat_id=chat_id,
            receiver_user_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            fallback_to_regular=False,
        )


@router.callback_query(F.data.startswith("grp_settings:menu:"))
async def cb_menu(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        await call.answer("Group not found", show_alert=True)
        return

    settings = group.get("settings", {})
    group_lang = settings.get("language", lang)

    title = group.get("title", f"Chat {chat_id}")
    text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
    kb = group_settings_menu_kb(chat_id, group, i18n, group_lang)

    await _edit_message_or_ephemeral(call, text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ── Callback: cycle operation mode ───────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:mode:"))
async def cb_cycle_mode(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    """Cycle mode: auto -> command -> disabled -> auto"""
    chat_id = int(call.data.split(":")[-1])

    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        await call.answer("Group not found", show_alert=True)
        return

    settings = group.get("settings", {})
    current_mode = settings.get("mode", "auto")

    # Cycle progression
    mode_order = ["auto", "command", "disabled"]
    next_index = (mode_order.index(current_mode) + 1) % len(mode_order) if current_mode in mode_order else 0
    new_mode = mode_order[next_index]

    settings["mode"] = new_mode
    # Sync auto_convert bool for backward compatibility
    settings["auto_convert"] = (new_mode == "auto")
    await update_group_settings(chat_id, settings)

    group = await get_group(chat_id)
    group_lang = group.get("settings", {}).get("language", lang)
    title = group.get("title", f"Chat {chat_id}")
    text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
    kb = group_settings_menu_kb(chat_id, group, i18n, group_lang)

    await _edit_message_or_ephemeral(call, text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ── Callback: Input / Output currencies selection ───────────────────────────


@router.callback_query(F.data.startswith("grp_settings:input:"))
async def cb_input_currencies(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])
    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        await call.answer("Group not found", show_alert=True)
        return

    settings = group.get("settings", {})
    selected = settings.get("input_currencies", [])

    uid = call.from_user.id
    cache_key = await _cache_key(uid)
    await cache.json_set(
        cache_key,
        {
            "chat_id": chat_id,
            "field": "input_currencies",
            "update data": list(selected),
            "page": 0,
        },
    )

    currencies = get_currencies_data()
    stx = i18n.get_section("settings", lang)
    desc = str(i18n.get("group_settings.input_currencies", lang))
    text = f"{desc}\n\nSelected: {', '.join(selected) if selected else 'none'}"

    kb = paginated_currency_keyboard(
        currencies, 0, "GRP_CURR", i18n, lang, selected=selected
    )
    await _edit_message_or_ephemeral(call, text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("grp_settings:output:"))
async def cb_output_currencies(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])
    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        await call.answer("Group not found", show_alert=True)
        return

    settings = group.get("settings", {})
    selected = settings.get("output_currencies", [])

    uid = call.from_user.id
    cache_key = await _cache_key(uid)
    await cache.json_set(
        cache_key,
        {
            "chat_id": chat_id,
            "field": "output_currencies",
            "update data": list(selected),
            "page": 0,
        },
    )

    currencies = get_currencies_data()
    desc = str(i18n.get("group_settings.output_currencies", lang))
    text = f"{desc}\n\nSelected: {', '.join(selected) if selected else 'none'}"

    kb = paginated_currency_keyboard(
        currencies, 0, "GRP_CURR", i18n, lang, selected=selected
    )
    await _edit_message_or_ephemeral(call, text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("GRP_CURR "))
async def cb_grp_curr_action(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    """Handle pagination and selection for group Input/Output currencies."""
    parts = call.data.split()
    command = parts[1] if len(parts) > 1 else ""

    uid = call.from_user.id
    cache_key = await _cache_key(uid)
    cd = (await cache.json_get(cache_key)) or {}

    chat_id = cd.get("chat_id")
    field = cd.get("field")
    data = cd.get("update data", [])

    if not chat_id or not field:
        await call.answer("Session expired", show_alert=True)
        return

    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    stx = i18n.get_section("settings", lang)

    if command == "save":
        await update_group_currencies(chat_id, field, data)
        await cache.delete(cache_key)
        await call.answer(stx.get("success", "Saved"), show_alert=False)

        # Return to main group settings menu
        group = await get_group(chat_id)
        group_lang = (group or {}).get("settings", {}).get("language", lang)
        title = (group or {}).get("title", f"Chat {chat_id}")
        menu_text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
        kb = group_settings_menu_kb(chat_id, group or {}, i18n, group_lang)
        await _edit_message_or_ephemeral(call, menu_text, reply_markup=kb, parse_mode="HTML")
        return

    if command == "cancel":
        await cache.delete(cache_key)
        await call.answer(stx.get("exit", "Cancelled"), show_alert=False)

        group = await get_group(chat_id)
        group_lang = (group or {}).get("settings", {}).get("language", lang)
        title = (group or {}).get("title", f"Chat {chat_id}")
        menu_text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
        kb = group_settings_menu_kb(chat_id, group or {}, i18n, group_lang)
        await _edit_message_or_ephemeral(call, menu_text, reply_markup=kb, parse_mode="HTML")
        return

    if command == "position":
        page = int(parts[2]) if len(parts) > 2 else 0
        cd["page"] = page
        await cache.json_set(cache_key, cd)
        currencies = get_currencies_data()
        pos_kb = paginated_currency_keyboard(currencies, page, "GRP_CURR", i18n, lang, selected=data)
        await _edit_message_or_ephemeral(call, call.message.text or "Select:", reply_markup=pos_kb, parse_mode="HTML")
        return

    # Toggle currency code
    code = command
    if code in data:
        data.remove(code)
        await call.answer(stx.get("alert remove", "Removed"))
    else:
        data.append(code)
        await call.answer(stx.get("alert add", "Added"))

    cd["update data"] = data
    await cache.json_set(cache_key, cd)

    page = cd.get("page", 0)
    currencies = get_currencies_data()
    desc_key = "group_settings.input_currencies" if field == "input_currencies" else "group_settings.output_currencies"
    desc = str(i18n.get(desc_key, lang))
    display_text = f"{desc}\n\nSelected: {', '.join(data) if data else 'none'}"

    try:
        toggle_kb = paginated_currency_keyboard(currencies, page, "GRP_CURR", i18n, lang, selected=data)
        await _edit_message_or_ephemeral(call, display_text, reply_markup=toggle_kb, parse_mode="HTML")
    except Exception:
        pass


# ── Callback: Language selection ────────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:lang:"))
async def cb_lang_menu(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    group_lang = (group or {}).get("settings", {}).get("language", lang)

    text = str(i18n.get("group_settings.language_title", group_lang))
    supported = get_settings().i18n.supported_languages
    kb = group_language_kb(chat_id, supported, i18n, group_lang)

    await _edit_message_or_ephemeral(call, text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("grp_settings:set_lang:"))
async def cb_set_lang(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    parts = call.data.split(":")
    chat_id = int(parts[2])
    new_lang = parts[3]

    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    if not group:
        await call.answer("Group not found", show_alert=True)
        return

    settings = group.get("settings", {})
    settings["language"] = new_lang
    await update_group_settings(chat_id, settings)

    from app.keyboards.inline import LANGUAGE_INFO
    lang_info = LANGUAGE_INFO.get(new_lang, {"native": new_lang})
    lang_name = lang_info.get("native", new_lang)

    text = str(i18n.get("group_settings.language_set", new_lang)).format(language=lang_name)
    await call.answer(text, show_alert=True)

    # Re-render main menu in new language
    group = await get_group(chat_id)
    title = group.get("title", f"Chat {chat_id}")
    menu_text = str(i18n.get("group_settings.title", new_lang)).format(title=title)
    kb = group_settings_menu_kb(chat_id, group, i18n, new_lang)
    await _edit_message_or_ephemeral(call, menu_text, reply_markup=kb, parse_mode="HTML")


# ── Callback: Deactivate bot in group ────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:deactivate:"))
async def cb_deactivate(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])
    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    text = str(i18n.get("settings.remove", lang))
    kb = group_deactivate_confirm_kb(chat_id, i18n, lang)
    await _edit_message_or_ephemeral(call, text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("grp_settings:confirm_deactivate:"))
async def cb_confirm_deactivate(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])
    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    await toggle_group_active(chat_id, False)
    msg = str(i18n.get("group_settings.deactivated", lang))
    await _edit_message_or_ephemeral(call, msg, parse_mode="HTML")
    await call.answer()

    # Leave the Telegram group chat
    try:
        await call.bot.leave_chat(chat_id)
    except Exception as exc:
        log.warning("Failed to leave chat %d on deactivation: %s", chat_id, exc)


# ── Callback: view chat admins ────────────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:admins:"))
async def cb_view_admins(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await _check_admin_permissions(call, chat_id, i18n, lang):
        return

    group = await get_group(chat_id)
    group_lang = (group or {}).get("settings", {}).get("language", lang)

    admins = await get_chat_admin_list(call.bot, chat_id)

    lines = [str(i18n.get("group_settings.admins_title", group_lang)), ""]
    if admins:
        lines.append(str(i18n.get("group_settings.admins_list", group_lang)))
        for a in admins:
            bot_badge = " 🤖" if a["is_bot"] else ""
            username = f" @{a['username']}" if a["username"] else ""
            status_emoji = "👑" if a["status"] == "creator" else "⭐"
            lines.append(f"{status_emoji} {a['name']}{username}{bot_badge}")
    else:
        lines.append("—")

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.back", group_lang)),
            callback_data=f"grp_settings:menu:{chat_id}",
        )
    )

    await _edit_message_or_ephemeral(call, "\n".join(lines), reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


# ── Callback: close ───────────────────────────────────────────────────────────


@router.callback_query(F.data == "grp_settings:close")
async def cb_close(call: CallbackQuery) -> None:
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()
