"""
Group admin handler — /group_settings command and inline controls.

Allows real Telegram group administrators (creator / administrator) to manage
bot settings for their specific group chat without needing global ADMIN_IDS.

Callback data prefix: ``grp_settings:`` (distinct from ``admin_groups:``).

TODO: Privacy Mode — the /group_settings command always works because Telegram
      delivers commands regardless of privacy mode.  However, auto-conversion
      of plain text like "100 USD" (handled by groups.py) requires Privacy Mode
      to be DISABLED via @BotFather for the bot to see non-command messages.

TODO: Group-level shared alerts (notifications visible to all group members)
      would require a new MongoDB collection and scheduler integration.
      Placeholder for a future version.
"""

from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.i18n import I18n
from app.logger import get_logger
from app.keyboards.group_admin import group_language_kb, group_settings_menu_kb
from app.repositories.groups import get_group, update_group_settings
from app.utils.chat_admin import get_chat_admin_list, is_chat_admin

log = get_logger("group_admin")
router = Router(name="group_admin")


# ── /group_settings ──────────────────────────────────────────────────────────


@router.message(Command("group_settings"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_group_settings(message: Message, i18n: I18n, lang: str) -> None:
    """Entry point — only real Telegram group admins may open this."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_chat_admin(message.bot, chat_id, user_id):
        await message.answer(str(i18n.get("group_settings.access_denied", lang)))
        return

    group = await get_group(chat_id)
    if not group:
        # Group may not be registered yet (edge case if bot was added before
        # the groups tracking was implemented).
        await message.answer(str(i18n.get("group_settings.access_denied", lang)))
        return

    settings = group.get("settings", {})
    group_lang = settings.get("language", lang)

    title = group.get("title", message.chat.title or f"Chat {chat_id}")
    text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
    kb = group_settings_menu_kb(chat_id, group, i18n, group_lang)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# Reject /group_settings in private chats
@router.message(Command("group_settings"), F.chat.type == "private")
async def cmd_group_settings_private(message: Message, i18n: I18n, lang: str) -> None:
    await message.answer(str(i18n.get("group_settings.not_in_group", lang)))


# ── Callback: re-open main menu ──────────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:menu:"))
async def cb_menu(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        await call.answer(str(i18n.get("group_settings.access_denied", lang)), show_alert=True)
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

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ── Callback: toggle auto-conversion ─────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:toggle_convert:"))
async def cb_toggle_convert(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        await call.answer(str(i18n.get("group_settings.access_denied", lang)), show_alert=True)
        return

    group = await get_group(chat_id)
    if not group:
        await call.answer("Group not found", show_alert=True)
        return

    settings = group.get("settings", {})
    current = settings.get("auto_convert", True)
    settings["auto_convert"] = not current
    await update_group_settings(chat_id, settings)

    # Refresh the group and re-render
    group = await get_group(chat_id)
    group_lang = group.get("settings", {}).get("language", lang)
    title = group.get("title", f"Chat {chat_id}")
    text = str(i18n.get("group_settings.title", group_lang)).format(title=title)
    kb = group_settings_menu_kb(chat_id, group, i18n, group_lang)

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ── Callback: language selection ──────────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:lang:"))
async def cb_lang_menu(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        await call.answer(str(i18n.get("group_settings.access_denied", lang)), show_alert=True)
        return

    group = await get_group(chat_id)
    group_lang = (group or {}).get("settings", {}).get("language", lang)

    text = str(i18n.get("group_settings.language_title", group_lang))
    supported = get_settings().i18n.supported_languages
    kb = group_language_kb(chat_id, supported, i18n, group_lang)

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("grp_settings:set_lang:"))
async def cb_set_lang(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    parts = call.data.split(":")
    chat_id = int(parts[2])
    new_lang = parts[3]

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        await call.answer(str(i18n.get("group_settings.access_denied", lang)), show_alert=True)
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
    await call.message.edit_text(menu_text, reply_markup=kb, parse_mode="HTML")


# ── Callback: view chat admins ────────────────────────────────────────────────


@router.callback_query(F.data.startswith("grp_settings:admins:"))
async def cb_view_admins(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    chat_id = int(call.data.split(":")[-1])

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        await call.answer(str(i18n.get("group_settings.access_denied", lang)), show_alert=True)
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

    await call.message.edit_text(
        "\n".join(lines), reply_markup=builder.as_markup(), parse_mode="HTML"
    )
    await call.answer()


# ── Callback: close ───────────────────────────────────────────────────────────


@router.callback_query(F.data == "grp_settings:close")
async def cb_close(call: CallbackQuery) -> None:
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()
