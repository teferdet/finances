"""
Keyboards for the group admin settings panel (/group_settings).

Callback data prefix: ``grp_settings:`` to avoid collisions with the
bot-wide ``admin_groups:`` prefix used by the global admin panel.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import I18n


def group_settings_menu_kb(
    chat_id: int,
    group: dict,
    i18n: I18n,
    lang: str,
) -> InlineKeyboardMarkup:
    """Main settings menu shown to a chat admin inside a group."""
    builder = InlineKeyboardBuilder()

    settings = group.get("settings", {})
    auto_convert = settings.get("auto_convert", True)

    # Toggle auto-conversion
    if auto_convert:
        toggle_text = str(i18n.get("group_settings.auto_convert_on", lang))
    else:
        toggle_text = str(i18n.get("group_settings.auto_convert_off", lang))
    builder.row(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=f"grp_settings:toggle_convert:{chat_id}",
        )
    )

    # Language
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.set_language", lang)),
            callback_data=f"grp_settings:lang:{chat_id}",
        )
    )

    # View admins (diagnostic)
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.view_admins", lang)),
            callback_data=f"grp_settings:admins:{chat_id}",
        )
    )

    # Close
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.close", lang)),
            callback_data="grp_settings:close",
        )
    )

    return builder.as_markup()


def group_language_kb(
    chat_id: int,
    supported: list[str],
    i18n: I18n,
    lang: str,
) -> InlineKeyboardMarkup:
    """Language selection for the group."""
    from app.keyboards.inline import LANGUAGE_INFO

    builder = InlineKeyboardBuilder()
    row: list[InlineKeyboardButton] = []

    for code in supported:
        info = LANGUAGE_INFO.get(code, {"flag": "", "native": code})
        row.append(
            InlineKeyboardButton(
                text=f"{info['flag']} {info['native']}",
                callback_data=f"grp_settings:set_lang:{chat_id}:{code}",
            )
        )
        if len(row) >= 2:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.back", lang)),
            callback_data=f"grp_settings:menu:{chat_id}",
        )
    )

    return builder.as_markup()
