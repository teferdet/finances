"""
My Data handler — /my_data command to view user settings and reset them.
"""

from __future__ import annotations

import html

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from app.config import get_settings
from app.db import get_db
from app.i18n import I18n

router = Router(name="my_data")


def _format_list(items: list | str | None, fallback: str = "—") -> str:
    """Format a list or string of items into a comma-separated string."""
    if not items:
        return fallback
    if isinstance(items, str):
        return items
    if isinstance(items, list):
        return ", ".join(str(i) for i in items) if items else fallback
    return str(items)


from aiogram.filters import Command
from aiogram.types import Message


async def _build_my_data_text_and_kb(uid: int, i18n: I18n, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    db = get_db()
    md = i18n.get_section("my_data", lang)

    # Fetch user data
    user = await db["Users"].find_one({"_id": uid}) or {}

    # Count related data
    alerts_count = await db["Alerts"].count_documents({"user_id": uid, "triggered": False})
    groups_list = user.get("Groups", [])
    groups_count = len(groups_list) if isinstance(groups_list, list) else 0

    # Portfolio count
    portfolio_count = 0
    portfolio = user.get("portfolio", {})
    if isinstance(portfolio, dict):
        for category in portfolio.values():
            if isinstance(category, list):
                portfolio_count += len(category)

    # Build display text
    yes_text = md.get("yes", "Yes")
    no_text = md.get("no", "No")
    none_text = md.get("none", "not set")
    default_text = md.get("default", "default")

    fiat = user.get("Fiat currency", [])
    crypto = user.get("Crypto currency", [])
    stocks = user.get("Stocks", [])
    main_menu = user.get("MainMenu", [])
    base_currency = user.get("BaseCurrency", "")
    rate_mode = user.get("RateMode", "direct")
    rate_mode_label = md.get("rate_mode_direct", "Direct") if rate_mode == "direct" else md.get("rate_mode_reverse", "Reverse")
    view_mode = user.get("PortfolioView", "detailed")
    view_label = md.get("view_compact", "Compact") if view_mode == "compact" else md.get("view_detailed", "Detailed")
    digest = user.get("WeeklyDigest", True)
    num_fmt = user.get("NumberFormat", "commas")
    num_fmt_label = "1 000" if num_fmt == "spaces" else "1,000"
    volatility = user.get("VolatilityThreshold", 5)
    vol_label = "OFF" if volatility == 0 else f"{volatility}%"
    big_buttons = user.get("BigButtons", False)

    lines = [
        md.get("title", "📋 <b>Your Data</b>"),
        "",
        f"{md.get('name', '👤 Name')}: <b>{html.escape(str(user.get('Name', none_text)))}</b>",
        f"{md.get('username', '🆔 Username')}: @{html.escape(str(user.get('Username', none_text)))}",
        f"{md.get('language', '🌐 Language')}: <b>{html.escape(str(user.get('Language', none_text)))}</b>",
        f"{md.get('premium', '⭐ Premium')}: {yes_text if user.get('Premium') else no_text}",
        f"{md.get('signed_up', '📅 Signed up')}: <b>{html.escape(str(user.get('Sign up', none_text)))}</b>",
        "",
        f"{md.get('fiat', '💶 Fiat')}: {_format_list(fiat, default_text)}",
        f"{md.get('crypto', '💵 Crypto')}: {_format_list(crypto, default_text)}",
        f"{md.get('stocks_label', '📑 Stocks')}: {_format_list(stocks, default_text)}",
        f"{md.get('main_menu', '📱 Main Menu')}: {_format_list(main_menu, default_text)}",
        f"{md.get('base_currency', '💱 Base Currency')}: <b>{_format_list(base_currency, default_text)}</b>",
        f"{md.get('rate_mode', '🔄 Rate Mode')}: <b>{rate_mode_label}</b>",
        f"{md.get('view_mode', '📊 Portfolio View')}: <b>{view_label}</b>",
        f"{md.get('digest', '📅 Weekly Digest')}: <b>{yes_text if digest else no_text}</b>",
        f"{md.get('num_fmt', '🔢 Number Format')}: <b>{num_fmt_label}</b>",
        f"{md.get('volatility', '🔔 Volatility Threshold')}: <b>{vol_label}</b>",
        f"{md.get('big_buttons', '📏 Big Buttons')}: {yes_text if big_buttons else no_text}",
        "",
        f"{md.get('groups_count', '👥 Groups')}: <b>{groups_count}</b>",
        f"{md.get('alerts_count', '🔔 Alerts')}: <b>{alerts_count}</b>",
        f"{md.get('portfolio_count', '💼 Portfolio')}: <b>{portfolio_count}</b>",
    ]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=md.get("btn_reset", "🔄 Reset Settings"),
                    callback_data="my_data_reset",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("keyboard.settings.back", lang) or "◀️ Back",
                    callback_data="menu",
                )
            ],
        ]
    )

    return "\n".join(lines), kb


@router.message(Command("my_data"))
async def cmd_my_data(message: Message, i18n: I18n, lang: str) -> None:
    if message.chat.type != "private":
        md = i18n.get_section("my_data", lang)
        await message.answer(str(md.get("private_only", "⚠️ Private only!")))
        return

    text, kb = await _build_my_data_text_and_kb(message.from_user.id, i18n, lang)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "my_data_view")
async def cb_my_data_view(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if call.message.chat.type != "private":
        md = i18n.get_section("my_data", lang)
        await call.message.answer(md.get("private_only", "⚠️ Private only!"))
        return

    text, kb = await _build_my_data_text_and_kb(call.from_user.id, i18n, lang)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "my_data_reset")
async def cb_reset_settings(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    uid = call.from_user.id
    db = get_db()
    settings = get_settings()
    md = i18n.get_section("my_data", lang)

    # Reset to defaults
    await db["Users"].update_one(
        {"_id": uid},
        {
            "$set": {
                "Fiat currency": settings.small_convert_currencies,
                "Crypto currency": settings.default_crypto,
                "Stocks": settings.default_stocks,
            },
            "$unset": {
                "MainMenu": "",
                "BaseCurrency": "",
                "BigButtons": "",
            },
        },
    )

    await call.answer(md.get("reset_success", "✅ Reset!"), show_alert=True)

    from app.keyboards.inline import settings_menu

    text = i18n.get("settings.menu", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
