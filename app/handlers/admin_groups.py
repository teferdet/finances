"""
Admin groups handler — managing Telegram groups and push notifications.

Fixed bugs vs. previous version:
  - call.fromuser typo  → call.from_user
  - FSMContext(storage=None, key=None) anti-pattern replaced by _render_settings()
  - Add-by-invite-link flow (new FSM state + handler)
  - Dual-collection issue fixed (all reads/writes go through repository → 'groups' collection)
"""

from __future__ import annotations

import re

from aiogram import Router, F
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import I18n
from app.logger import get_logger
from app.keyboards.admin_groups import (
    admin_group_errors_level_kb,
    admin_group_settings_kb,
    admin_groups_add_kb,
    admin_groups_confirm_kb,
    admin_groups_list_kb,
)
from app.repositories.groups import (
    add_group,
    get_all_groups,
    get_group,
    remove_group,
    toggle_group_active,
    update_group_notifications,
)
from app.repositories.communities import get_community

log = get_logger("admin_groups")
router = Router(name="admin_groups")


# ── FSM states ────────────────────────────────────────────────────────────────


class AdminGroupsFSM(StatesGroup):
    waiting_for_chat_id = State()  # manual numeric ID entry
    waiting_for_invite_link = State()  # invite-link / username entry
    waiting_for_analytics_time = State()  # HH:MM input


# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_admin(user_id: int) -> bool:
    from app.config import get_settings
    from app.state import dynamic_admin_ids

    return user_id in get_settings().bot.admin_ids or user_id in dynamic_admin_ids


async def _group_settings_text(group: dict, i18n: I18n, lang: str) -> str:
    """Build the settings card text for a group — used by every settings refresh."""
    chat_id = group.get("chat_id")
    title = group.get("title", "Unknown")
    is_active = group.get("is_active", False)
    community_id = group.get("community_id")

    if is_active:
        status = "✅ " + str(i18n.get("admin.groups.status_active", lang))
    else:
        status = "⛔ " + str(i18n.get("admin.groups.status_inactive", lang))

    notifs = group.get("notifications", {})
    err_conf = notifs.get("errors", {})
    anl_conf = notifs.get("analytics", {})

    if err_conf.get("enabled"):
        err_status = (
            f"🟢 {i18n.get('admin.groups.on', lang)} "
            f"| {i18n.get('admin.groups.level', lang)}: {err_conf.get('min_level', 'ERROR')}"
        )
    else:
        err_status = f"🔴 {i18n.get('admin.groups.off', lang)}"

    if anl_conf.get("enabled"):
        schedule_key = (
            "admin.groups.analytics_daily"
            if anl_conf.get("schedule", "daily") == "daily"
            else "admin.groups.analytics_weekly"
        )
        sch_text = i18n.get(schedule_key, lang)
        eph_text = " (🔒 Ephemeral)" if anl_conf.get("ephemeral") else ""
        anl_status = (
            f"🟢 {i18n.get('admin.groups.on', lang)} "
            f"| {sch_text} {i18n.get('admin.groups.at_time', lang)} "
            f"{anl_conf.get('send_time', '09:00')} UTC{eph_text}"
        )
    else:
        anl_status = f"🔴 {i18n.get('admin.groups.off', lang)}"

    added_at = group.get("added_at")
    added_str = added_at.strftime("%Y-%m-%d") if added_at else "—"

    community_str = ""
    if community_id:
        comm = await get_community(community_id)
        if comm:
            community_str = f"Community: {comm.get('name', community_id)}\n"

    return (
        f"⚙️ <b>{title}</b>\n\n"
        f"ID: <code>{chat_id}</code>\n"
        f"Type: {group.get('type', '—')}\n"
        f"{community_str}"
        f"Added: {added_str}\n"
        f"{i18n.get('admin.groups.status', lang)}: {status}\n\n"
        f"── {i18n.get('admin.groups.errors_header', lang)} ──\n"
        f"{err_status}\n\n"
        f"── {i18n.get('admin.groups.analytics_header', lang)} ──\n"
        f"{anl_status}"
    )


async def _render_settings(call: CallbackQuery, chat_id: int, i18n: I18n, lang: str) -> None:
    """
    Fetch the group from DB and edit the current message to show settings.
    Replaces the anti-pattern of calling handlers with fake FSMContext.
    """
    group = await get_group(chat_id)
    if not group:
        await call.answer(str(i18n.get("admin.groups.not_found", lang)), show_alert=True)
        return
    text = await _group_settings_text(group, i18n, lang)
    kb = admin_group_settings_kb(group, i18n, lang)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ── List & Entry ──────────────────────────────────────────────────────────────


@router.callback_query(F.data.in_({"admin_groups", "admin_groups:list"}))
async def cb_groups_list(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return

    await state.clear()
    groups = await get_all_groups()
    text = str(i18n.get("admin.groups.list_title", lang))
    kb = admin_groups_list_kb(groups, i18n, lang)

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ── Add by numeric ID ─────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin_groups:add_id")
async def cb_add_by_id(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return

    await state.set_state(AdminGroupsFSM.waiting_for_chat_id)
    text = str(i18n.get("admin.groups.add_prompt", lang))
    await call.message.edit_text(text, reply_markup=admin_groups_add_kb(i18n, lang), parse_mode="HTML")
    await call.answer()


@router.message(StateFilter(AdminGroupsFSM.waiting_for_chat_id))
async def process_add_by_id(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return

    raw = message.text.strip()
    try:
        chat_id = int(raw)
    except ValueError:
        await message.answer(
            str(i18n.get("admin.groups.invalid_id", lang)),
            reply_markup=admin_groups_add_kb(i18n, lang),
        )
        return

    await _finalize_add(message, state, i18n, lang, chat_id)


# ── Add by invite link / username ─────────────────────────────────────────────


@router.callback_query(F.data == "admin_groups:add_link")
async def cb_add_by_link(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return

    await state.set_state(AdminGroupsFSM.waiting_for_invite_link)
    text = str(i18n.get("admin.groups.add_link_prompt", lang))
    await call.message.edit_text(text, reply_markup=admin_groups_add_kb(i18n, lang), parse_mode="HTML")
    await call.answer()


@router.message(StateFilter(AdminGroupsFSM.waiting_for_invite_link))
async def process_add_by_link(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return

    raw = message.text.strip()

    # Extract username from @username or t.me/username style
    username: str | None = None
    if raw.startswith("@"):
        username = raw[1:]
    elif "t.me/" in raw:
        username = raw.split("t.me/")[-1].split("?")[0].strip("/")
    elif re.match(r"^-?\d+$", raw):
        # They entered a numeric ID after all
        await process_add_by_id.__wrapped__(message, state, i18n, lang)  # type: ignore[attr-defined]
        return

    if not username:
        await message.answer(
            str(i18n.get("admin.groups.invalid_link", lang)),
            reply_markup=admin_groups_add_kb(i18n, lang),
        )
        return

    try:
        chat_info = await message.bot.get_chat(f"@{username}")
        chat_id = chat_info.id
    except (TelegramForbiddenError, TelegramBadRequest):
        await message.answer(
            str(i18n.get("admin.groups.no_access", lang)),
            reply_markup=admin_groups_add_kb(i18n, lang),
        )
        return

    await _finalize_add(message, state, i18n, lang, chat_id)


# ── Shared add logic ──────────────────────────────────────────────────────────


async def _finalize_add(
    message: Message,
    state: FSMContext,
    i18n: I18n,
    lang: str,
    chat_id: int,
) -> None:
    """
    Validate, resolve, and persist a group. Called from both add-by-ID
    and add-by-link flows so logic is never duplicated.
    """
    existing = await get_group(chat_id)
    if existing:
        await message.answer(
            str(i18n.get("admin.groups.already_exists", lang)),
            reply_markup=admin_groups_add_kb(i18n, lang),
        )
        return

    try:
        chat_info = await message.bot.get_chat(chat_id)
    except (TelegramForbiddenError, TelegramBadRequest):
        await message.answer(
            str(i18n.get("admin.groups.no_access", lang)),
            reply_markup=admin_groups_add_kb(i18n, lang),
        )
        return

    title = chat_info.title or f"Group {chat_id}"
    group_type = str(chat_info.type)

    success = await add_group(chat_id, title, group_type, message.from_user.id)
    if success:
        text = str(i18n.get("admin.groups.add_success", lang)).format(title=title, chat_id=chat_id, type=group_type)
        await message.answer(text, reply_markup=admin_groups_confirm_kb(chat_id, i18n, lang), parse_mode="HTML")
        await state.clear()
        log.info("Admin %d added group '%s' (%d)", message.from_user.id, title, chat_id)
    else:
        await message.answer(str(i18n.get("admin.groups.already_exists", lang)))


# ── Settings card ─────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin_groups:settings:"))
async def cb_group_settings(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return

    await state.clear()
    chat_id = int(call.data.split(":")[-1])
    await _render_settings(call, chat_id, i18n, lang)


# ── Error notifications ───────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin_groups:errors:toggle:"))
async def cb_errors_toggle(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    chat_id = int(parts[3])
    enabled = parts[4] == "1"

    group = await get_group(chat_id)
    if group:
        notifs = group.get("notifications", {})
        notifs.setdefault("errors", {})["enabled"] = enabled
        await update_group_notifications(chat_id, notifs)

    await _render_settings(call, chat_id, i18n, lang)


@router.callback_query(F.data.startswith("admin_groups:errors:level:"))
async def cb_errors_level(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    chat_id = int(call.data.split(":")[-1])

    group = await get_group(chat_id)
    current_level = "ERROR"
    if group:
        current_level = group.get("notifications", {}).get("errors", {}).get("min_level", "ERROR")

    text = str(i18n.get("admin.groups.errors_choose_level", lang))
    kb = admin_group_errors_level_kb(chat_id, current_level, i18n, lang)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("admin_groups:errors:set_level:"))
async def cb_errors_set_level(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    chat_id = int(parts[3])
    level = parts[4]

    group = await get_group(chat_id)
    if group:
        notifs = group.get("notifications", {})
        notifs.setdefault("errors", {})["min_level"] = level
        await update_group_notifications(chat_id, notifs)

    await _render_settings(call, chat_id, i18n, lang)


# ── Analytics notifications ───────────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin_groups:analytics:toggle:"))
async def cb_analytics_toggle(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    chat_id = int(parts[3])
    enabled = parts[4] == "1"

    group = await get_group(chat_id)
    if group:
        notifs = group.get("notifications", {})
        notifs.setdefault("analytics", {})["enabled"] = enabled
        await update_group_notifications(chat_id, notifs)

    await _render_settings(call, chat_id, i18n, lang)


@router.callback_query(F.data.startswith("admin_groups:analytics:schedule:"))
async def cb_analytics_schedule(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    chat_id = int(parts[3])
    schedule = parts[4]

    group = await get_group(chat_id)
    if group:
        notifs = group.get("notifications", {})
        notifs.setdefault("analytics", {})["schedule"] = schedule
        await update_group_notifications(chat_id, notifs)

    await _render_settings(call, chat_id, i18n, lang)


@router.callback_query(F.data.startswith("admin_groups:analytics:time:"))
async def cb_analytics_time(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    chat_id = int(call.data.split(":")[-1])
    await state.set_state(AdminGroupsFSM.waiting_for_analytics_time)
    await state.update_data(chat_id=chat_id)

    text = str(i18n.get("admin.groups.analytics_time_prompt", lang))
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.cancel", lang)),
            callback_data=f"admin_groups:settings:{chat_id}",
        )
    )
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("admin_groups:analytics:ephemeral:"))
async def cb_analytics_ephemeral(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    chat_id = int(parts[3])
    enabled = parts[4] == "1"

    group = await get_group(chat_id)
    if group:
        notifs = group.get("notifications", {})
        notifs.setdefault("analytics", {})["ephemeral"] = enabled
        await update_group_notifications(chat_id, notifs)

    await _render_settings(call, chat_id, i18n, lang)


@router.message(StateFilter(AdminGroupsFSM.waiting_for_analytics_time))
async def process_analytics_time(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return

    raw = message.text.strip()
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", raw):
        await message.answer(str(i18n.get("admin.groups.invalid_time", lang)))
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")

    group = await get_group(chat_id)
    if group:
        notifs = group.get("notifications", {})
        notifs.setdefault("analytics", {})["send_time"] = raw
        await update_group_notifications(chat_id, notifs)

    await state.clear()
    await message.answer(
        str(i18n.get("admin.groups.time_saved", lang)),
        parse_mode="HTML",
    )
    log.info("Admin %d set analytics time %s for group %d", message.from_user.id, raw, chat_id)


# ── Activate / Deactivate / Delete ────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin_groups:toggle_active:"))
async def cb_toggle_active(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        return
    chat_id = int(call.data.split(":")[-1])

    group = await get_group(chat_id)
    if group:
        await toggle_group_active(chat_id, not group.get("is_active", False))

    await _render_settings(call, chat_id, i18n, lang)


@router.callback_query(F.data.startswith("admin_groups:delete:"))
async def cb_delete_group(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    chat_id = int(call.data.split(":")[-1])
    await remove_group(chat_id)
    log.info("Admin %d deleted group %d", call.from_user.id, chat_id)

    # Return to the list
    await state.clear()
    groups = await get_all_groups()
    text = str(i18n.get("admin.groups.list_title", lang))
    kb = admin_groups_list_kb(groups, i18n, lang)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()
