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
    mode = settings.get("mode", "auto")

    # Mode toggle button (cycles: auto -> command -> disabled -> auto)
    if mode == "command":
        mode_text = str(i18n.get("group_settings.mode_command", lang))
    elif mode == "disabled":
        mode_text = str(i18n.get("group_settings.mode_disabled", lang))
    else:
        mode_text = str(i18n.get("group_settings.mode_auto", lang))

    builder.row(
        InlineKeyboardButton(
            text=mode_text,
            callback_data=f"grp_settings:mode:{chat_id}",
        )
    )

    # Input Currencies (Triggers)
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.input_currencies", lang)),
            callback_data=f"grp_settings:input:{chat_id}",
        ),
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.output_currencies", lang)),
            callback_data=f"grp_settings:output:{chat_id}",
        ),
    )

    # Language & View admins
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.set_language", lang)),
            callback_data=f"grp_settings:lang:{chat_id}",
        ),
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.view_admins", lang)),
            callback_data=f"grp_settings:admins:{chat_id}",
        ),
    )

    # Deactivate bot in group
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.deactivate", lang)),
            callback_data=f"grp_settings:deactivate:{chat_id}",
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


def group_deactivate_confirm_kb(
    chat_id: int,
    i18n: I18n,
    lang: str,
) -> InlineKeyboardMarkup:
    """Confirmation keyboard before deactivating bot in a group."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=str(i18n.get("keyboard.settings.confirm", lang)),
            callback_data=f"grp_settings:confirm_deactivate:{chat_id}",
        ),
        InlineKeyboardButton(
            text=str(i18n.get("group_settings.back", lang)),
            callback_data=f"grp_settings:menu:{chat_id}",
        ),
    )
    return builder.as_markup()
