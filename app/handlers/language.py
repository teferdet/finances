"""
Language selection handler.
"""

from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.db import get_db
from app.i18n import I18n
from app.keyboards.inline import language_keyboard, LANGUAGE_INFO

router = Router(name="language")


async def _get_language_select_text(i18n: I18n, lang: str) -> str:
    text = i18n.get("language.select", lang)
    return str(text)


@router.message(Command("language", "lang"))
async def cmd_language(message: Message, i18n: I18n, lang: str) -> None:
    from app.utils.draft import finish_initial_message_draft, process_initial_message_draft
    import asyncio

    loading_text = str(i18n.get("language.loading", "Language loading..."))
    task = asyncio.create_task(_get_language_select_text(i18n, lang))
    was_loading, text = await process_initial_message_draft(message, task, loading_text)

    kb = language_keyboard(i18n.supported)
    await finish_initial_message_draft(message, text, was_loading)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


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
