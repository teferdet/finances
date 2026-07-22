"""
Start / Help / Donate / Privacy handlers.
"""

from __future__ import annotations

from time import strftime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import get_settings
from app.db import get_db
from app.i18n import I18n
from app.keyboards.main import get_main_keyboard
from app.keyboards.inline import donate_keyboard, help_keyboard

router = Router(name="start")


# ── /start ──────────────────────────────────────────────────────────


@router.message(Command("start"))
async def cmd_start(message: Message, i18n: I18n, lang: str) -> None:
    user = message.from_user
    name_parts = [user.first_name]
    if user.last_name:
        name_parts.append(user.last_name)
    name = " ".join(name_parts)

    # Time-of-day greeting
    hour = int(strftime("%H"))
    if 6 <= hour <= 12:
        period = "morning"
    elif 13 <= hour <= 18:
        period = "day"
    elif 19 <= hour <= 21:
        period = "evening"
    else:
        period = "night"

    time_text = i18n.get_section("time", lang)
    hello = time_text.get(period, "Good day")
    greeting_text = str(i18n.get("other.greeting", lang)).format(hello=hello, name=name)
    await message.answer(greeting_text)

    # Menu
    if message.chat.type == "private":
        menu_lines = i18n.get("menu.private", lang)
        kb = await get_main_keyboard(user.id)
    else:
        menu_lines = i18n.get("menu.group", lang)
        kb = None

    menu_text = "".join(menu_lines) if isinstance(menu_lines, list) else str(menu_lines)
    await message.answer(menu_text, reply_markup=kb, parse_mode="HTML")

    # Ensure user in DB
    db = get_db()
    exists = await db["Users"].find_one({"_id": user.id}, {"_id": 1})
    if not exists:
        settings = get_settings()
        await db["Users"].insert_one(
            {
                "_id": user.id,
                "Name": name,
                "Username": user.username,
                "Language": user.language_code,
                "Premium": user.is_premium,
                "Sign up": strftime("%d.%m.%y %H:%M:%S"),
                "Fiat currency": settings.small_convert_currencies,
                "Crypto currency": settings.default_crypto,
                "Stocks": settings.default_stocks,
                "Groups": [],
            }
        )


# ── /help ───────────────────────────────────────────────────────────


@router.message(Command("help"))
async def cmd_help(message: Message, i18n: I18n, lang: str) -> None:
    text = i18n.get("other.help.main", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    kb = help_keyboard(i18n, lang, show_qa=True)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── /donate ─────────────────────────────────────────────────────────


@router.message(Command("donate"))
async def cmd_donate(message: Message, i18n: I18n, lang: str) -> None:
    text = i18n.get("other.donate", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    await message.answer(text, reply_markup=donate_keyboard(), parse_mode="HTML")


# ── /privacy ────────────────────────────────────────────────────────


@router.message(Command("privacy"))
async def cmd_privacy(message: Message, i18n: I18n, lang: str) -> None:
    content = i18n.get_section("other.privacy", lang)
    privacy_text = "".join(content.get("text", []))
    update_line = content.get("update", "")
    version = "2.0"
    text = f"{privacy_text}\n\n{update_line}".format(version)
    await message.answer(text, parse_mode="HTML")


# ── /expense_manager ────────────────────────────────────────────────


@router.message(Command("expense_manager"))
async def cmd_expense_manager(message: Message, i18n: I18n, lang: str) -> None:
    settings = get_settings()
    if message.from_user.id in settings.bot.admin_ids or settings.features.mini_app_enabled:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        text = i18n.get("other.mini app", lang)
        text = "".join(text) if isinstance(text, list) else str(text)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(i18n.get("other.mini_app_open", lang, default="🌐 Open")), url=settings.urls.mini_app
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=kb)
