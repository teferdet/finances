"""
Language selection handler.
"""

from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.db import get_db
from app.i18n import I18n, get_i18n
from app.keyboards.inline import language_keyboard, LANGUAGE_INFO

router = Router(name="language")


@router.message(Command("language", "lang"))
async def cmd_language(message: Message, i18n: I18n, lang: str) -> None:
    text = i18n.get("language.select", lang)
    kb = language_keyboard(i18n.supported)
    await message.answer(str(text), reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("lang_set_"))
async def cb_set_language(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    code = call.data.replace("lang_set_", "")
    if code not in i18n.supported:
        await call.answer(str(i18n.get("language.unknown", lang)))
        return
    db = get_db()
    await db["Users"].update_one(
        {"_id": call.from_user.id},
        {"$set": {"Language": code}},
        upsert=True,
    )
    info = LANGUAGE_INFO.get(code, {"native": code})
    confirm = i18n.get("language.changed", code, language=info["native"])
    await call.message.edit_text(str(confirm), parse_mode="HTML")
    await call.answer(f"{info['native']}")


@router.callback_query(F.data == "lang_cancel")
async def cb_lang_cancel(call: CallbackQuery) -> None:
    await call.message.delete()
    await call.answer()


@router.callback_query(F.data == "settings_language")
async def cb_settings_language(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    text = i18n.get("language.select", lang)
    kb = language_keyboard(i18n.supported, back_cb="menu")
    await call.message.edit_text(str(text), reply_markup=kb, parse_mode="HTML")
