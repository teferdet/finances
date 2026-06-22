"""
My Data handler — /my_data command to view user settings and reset them.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import get_settings
from app.db import get_db
from app.i18n import I18n
from app.keyboards.main import get_main_keyboard

router = Router(name="my_data")


def _format_list(items: list | None, fallback: str = "—") -> str:
    """Format a list of items into a comma-separated string."""
    if not items:
        return fallback
    return ", ".join(str(i) for i in items)


@router.message(Command("my_data"))
async def cmd_my_data(message: Message, i18n: I18n, lang: str) -> None:
    if message.chat.type != "private":
        md = i18n.get_section("my_data", lang)
        await message.answer(md.get("private_only", "⚠️ Private only!"))
        return

    uid = message.from_user.id
    db = get_db()
    md = i18n.get_section("my_data", lang)

    # Fetch user data
    user = await db["Users"].find_one({"_id": uid})
    if not user:
        user = {}

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
    big_buttons = user.get("BigButtons", False)

    lines = [
        md.get("title", "📋 <b>Your Data</b>"),
        "",
        f"{md.get('name', '👤 Name')}: <b>{user.get('Name', none_text)}</b>",
        f"{md.get('username', '🆔 Username')}: @{user.get('Username', none_text)}",
        f"{md.get('language', '🌐 Language')}: <b>{user.get('Language', none_text)}</b>",
        f"{md.get('premium', '⭐ Premium')}: {yes_text if user.get('Premium') else no_text}",
        f"{md.get('signed_up', '📅 Signed up')}: <b>{user.get('Sign up', none_text)}</b>",
        "",
        f"{md.get('fiat', '💶 Fiat')}: {_format_list(fiat, default_text)}",
        f"{md.get('crypto', '💵 Crypto')}: {_format_list(crypto, default_text)}",
        f"{md.get('stocks_label', '📑 Stocks')}: {_format_list(stocks, default_text)}",
        f"{md.get('main_menu', '📱 Main Menu')}: {_format_list(main_menu, default_text)}",
        f"{md.get('base_currency', '💱 Base Currency')}: <b>{base_currency or default_text}</b>",
        f"{md.get('big_buttons', '📏 Big Buttons')}: {yes_text if big_buttons else no_text}",
        "",
        f"{md.get('groups_count', '👥 Groups')}: <b>{groups_count}</b>",
        f"{md.get('alerts_count', '🔔 Alerts')}: <b>{alerts_count}</b>",
        f"{md.get('portfolio_count', '💼 Portfolio')}: <b>{portfolio_count}</b>",
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=md.get("btn_reset", "🔄 Reset Settings"),
            callback_data="my_data_reset",
        )],
    ])

    await message.answer("\n".join(lines), reply_markup=kb)


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

    # Refresh the reply keyboard
    kb = await get_main_keyboard(uid)
    await call.message.answer(
        md.get("reset_success", "✅ Settings reset!"),
        reply_markup=kb,
    )

    # Remove inline keyboard from the old message
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
