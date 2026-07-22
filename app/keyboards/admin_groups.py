"""
Keyboards for the admin groups module.
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.i18n import I18n


def admin_groups_list_kb(groups: list[dict], i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for group in groups:
        chat_id = group.get("chat_id")
        title = group.get("title", f"Group {chat_id}")
        is_active = group.get("is_active", False)

        status_emoji = "✅" if is_active else "⛔"

        notifs = group.get("notifications", {})
        errors_enabled = notifs.get("errors", {}).get("enabled", False)
        analytics_enabled = notifs.get("analytics", {}).get("enabled", False)

        badges = []
        if errors_enabled:
            badges.append("ERR")
        if analytics_enabled:
            badges.append("ANL")

        badge_text = f" [{'/'.join(badges)}]" if badges else ""
        # Truncate long titles so callback_data stays within 64 bytes
        short_title = title[:28] + "…" if len(title) > 30 else title
        btn_text = f"{status_emoji} {short_title}{badge_text}"

        builder.row(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"admin_groups:settings:{chat_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.add_by_id", lang)),
            callback_data="admin_groups:add_id",
        ),
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.add_by_link", lang)),
            callback_data="admin_groups:add_link",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.back", lang)),
            callback_data="admin_back",
        )
    )

    return builder.as_markup()


def admin_groups_add_kb(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.cancel", lang)),
            callback_data="admin_groups:list",
        )
    )
    return builder.as_markup()


def admin_groups_confirm_kb(chat_id: int, i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.configure", lang)),
            callback_data=f"admin_groups:settings:{chat_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.back_to_list", lang)),
            callback_data="admin_groups:list",
        )
    )
    return builder.as_markup()


def admin_group_settings_kb(group: dict, i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    chat_id = group.get("chat_id")
    is_active = group.get("is_active", False)
    notifs = group.get("notifications", {})

    errors_config = notifs.get("errors", {})
    analytics_config = notifs.get("analytics", {})

    # ── Errors notification block ─────────────────────────────────────────────
    if errors_config.get("enabled", False):
        builder.row(
            InlineKeyboardButton(
                text=str(i18n.get("admin.groups.errors_change_level", lang)),
                callback_data=f"admin_groups:errors:level:{chat_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=str(i18n.get("admin.groups.errors_disable", lang)),
                callback_data=f"admin_groups:errors:toggle:{chat_id}:0",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=str(i18n.get("admin.groups.errors_enable", lang)),
                callback_data=f"admin_groups:errors:toggle:{chat_id}:1",
            )
        )

    # ── Analytics notification block ──────────────────────────────────────────
    if analytics_config.get("enabled", False):
        schedule = analytics_config.get("schedule", "daily")
        daily_label = str(i18n.get("admin.groups.analytics_daily", lang))
        weekly_label = str(i18n.get("admin.groups.analytics_weekly", lang))
        sch_daily = ("✅ " + daily_label) if schedule == "daily" else daily_label
        sch_weekly = ("✅ " + weekly_label) if schedule == "weekly" else weekly_label
        is_ephemeral = analytics_config.get("ephemeral", False)

        builder.row(
            InlineKeyboardButton(
                text=sch_daily,
                callback_data=f"admin_groups:analytics:schedule:{chat_id}:daily",
            ),
            InlineKeyboardButton(
                text=sch_weekly,
                callback_data=f"admin_groups:analytics:schedule:{chat_id}:weekly",
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text=str(i18n.get("admin.groups.analytics_change_time", lang)),
                callback_data=f"admin_groups:analytics:time:{chat_id}",
            )
        )
        if is_ephemeral:
            builder.row(
                InlineKeyboardButton(
                    text="🔒 Ephemeral: ON",
                    callback_data=f"admin_groups:analytics:ephemeral:{chat_id}:0",
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="🔓 Ephemeral: OFF",
                    callback_data=f"admin_groups:analytics:ephemeral:{chat_id}:1",
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=str(i18n.get("admin.groups.analytics_disable", lang)),
                callback_data=f"admin_groups:analytics:toggle:{chat_id}:0",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=str(i18n.get("admin.groups.analytics_enable", lang)),
                callback_data=f"admin_groups:analytics:toggle:{chat_id}:1",
            )
        )

    # ── Activate / Deactivate + Delete ────────────────────────────────────────
    toggle_text = (
        str(i18n.get("admin.groups.deactivate", lang)) if is_active else str(i18n.get("admin.groups.activate", lang))
    )
    builder.row(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=f"admin_groups:toggle_active:{chat_id}",
        ),
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.delete", lang)),
            callback_data=f"admin_groups:delete:{chat_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.back", lang)),
            callback_data="admin_groups:list",
        )
    )

    return builder.as_markup()


def admin_group_errors_level_kb(chat_id: int, current_level: str, i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in ("WARNING", "ERROR", "CRITICAL"):
        label = ("✅ " + level) if level == current_level else level
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin_groups:errors:set_level:{chat_id}:{level}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("admin.groups.back_to_settings", lang)),
            callback_data=f"admin_groups:settings:{chat_id}",
        )
    )
    return builder.as_markup()
