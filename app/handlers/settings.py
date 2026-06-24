"""
Settings handler — /settings, bot/group config, currency selection callbacks.
"""

from __future__ import annotations
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from app.db import get_db
from app.cache import cache
from app.config import get_settings, get_currencies_data
from app.i18n import I18n
from app.keyboards.inline import (
    settings_menu,
    about_keyboard,
    paginated_currency_keyboard,
)
from app.keyboards.main import get_main_keyboard

router = Router(name="settings")


async def _cache_key(uid: int) -> str:
    return f"settings:{uid}"


@router.message(Command("settings"))
async def cmd_settings(message: Message, i18n: I18n, lang: str) -> None:
    if message.chat.type != "private":
        await message.answer(i18n.get("settings.local error", lang))
        return
    text = i18n.get("settings.menu", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    uid = message.from_user.id
    await cache.json_set(await _cache_key(uid), {})
    await message.answer(text, reply_markup=settings_menu(i18n, lang))


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    text = i18n.get("settings.menu", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    await cache.json_set(await _cache_key(call.from_user.id), {})
    await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))


@router.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    s = get_settings()
    text = str(i18n.get("other.info", lang)).format(s.bot.version)
    kb = about_keyboard(i18n, lang)
    await call.message.edit_text(text, reply_markup=kb)


# cb_bot removed — items moved to main settings_menu


def _selected_text(stx: dict, data: list) -> str:
    """Build a dynamic 'currently selected' line for currency editors."""
    if data:
        # Make sure we only join strings, handle nested lists gracefully
        clean_data = [str(x[0]) if isinstance(x, list) and x else str(x) for x in data]
        return stx.get("current_selected", "<b>Selected:</b> {items}").format(items=", ".join(clean_data))
    return stx.get("current_selected_none", "<b>Selected:</b> <i>none</i>")


@router.callback_query(F.data == "fiat")
async def cb_fiat(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    uid = call.from_user.id
    cd = (await cache.json_get(await _cache_key(uid))) or {}
    db = get_db()
    user = await db["Users"].find_one({"_id": uid}, {"Fiat currency": 1})
    cd["update data"] = (user or {}).get("Fiat currency", [])
    cd["update type"] = "Fiat currency"
    cd["page"] = 0
    await cache.json_set(await _cache_key(uid), cd)
    currencies = get_currencies_data()
    stx = i18n.get_section("settings", lang)
    desc = str(i18n.get("settings.output", lang))
    selected_line = _selected_text(stx, cd["update data"])
    text = f"{desc}\n\n{selected_line}"
    await call.message.edit_text(
        text, reply_markup=paginated_currency_keyboard(currencies, 0, "Output", i18n, lang, selected=cd["update data"])
    )


@router.callback_query(F.data == "settings_base_currency")
async def cb_base_currency(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    uid = call.from_user.id
    cd = (await cache.json_get(await _cache_key(uid))) or {}
    db = get_db()
    user = await db["Users"].find_one({"_id": uid}, {"BaseCurrency": 1})
    base_val = (user or {}).get("BaseCurrency") or "USD"
    if isinstance(base_val, list):
        base_val = base_val[0] if base_val else "USD"
    cd["update data"] = [str(base_val)]
    cd["update type"] = "BaseCurrency"
    cd["page"] = 0
    await cache.json_set(await _cache_key(uid), cd)
    currencies = get_currencies_data()
    stx = i18n.get_section("settings", lang)
    desc = str(stx.get("base_currency_desc", "Select your default base currency:"))
    selected_line = _selected_text(stx, cd["update data"])
    await call.message.edit_text(
        f"{desc}\n\n{selected_line}",
        reply_markup=paginated_currency_keyboard(currencies, 0, "BaseCurrency", i18n, lang, selected=cd["update data"]),
    )


@router.callback_query(F.data.in_({"settings_crypto", "stocks"}))
async def cb_crypto_stocks(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    uid = call.from_user.id
    cd = (await cache.json_get(await _cache_key(uid))) or {}
    s = get_settings()
    db = get_db()
    user = await db["Users"].find_one({"_id": uid}, {"Crypto currency": 1, "Stocks": 1})

    if call.data == "settings_crypto":
        cd["update data"] = (user or {}).get("Crypto currency", [])
        cd["update type"] = "Crypto currency"
        items = [{"code": c, "emoji": ""} for c in s.crypto_list]
    else:
        cd["update data"] = (user or {}).get("Stocks", [])
        cd["update type"] = "Stocks"
        items = [{"code": c, "emoji": ""} for c in s.company_list]
    cd["page"] = 0
    await cache.json_set(await _cache_key(uid), cd)
    stx = i18n.get_section("settings", lang)
    desc = str(i18n.get("settings.output", lang))
    selected_line = _selected_text(stx, cd["update data"])
    text = f"{desc}\n\n{selected_line}"
    await call.message.edit_text(
        text, reply_markup=paginated_currency_keyboard(items, 0, "CSK", i18n, lang, selected=cd["update data"])
    )


# ── Generic data processing callbacks ──────────────────────────────


@router.callback_query(F.data.regexp(r"^(Output|Input|CSK|BaseCurrency) "))
async def cb_data_processing(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    parts = call.data.split()
    prefix = parts[0]
    command = parts[1] if len(parts) > 1 else ""
    uid = call.from_user.id
    key = await _cache_key(uid)
    cd = (await cache.json_get(key)) or {}
    data = cd.get("update data", [])
    stx = i18n.get_section("settings", lang)
    db = get_db()

    if command == "save":
        update_type = cd.get("update type")
        if "group" in cd:
            await db["Groups"].update_one({"_id": cd["group"]}, {"$set": {prefix: data}})
        elif update_type:
            await db["Users"].update_one({"_id": uid}, {"$set": {update_type: data}})
        await call.answer(stx.get("success", "Saved"), show_alert=False)
        cd["update data"] = []
        await cache.json_set(key, cd)
        text = i18n.get("settings.menu", lang)
        text = "".join(text) if isinstance(text, list) else str(text)
        await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
        return

    if command == "cancel":
        cd["update data"] = []
        await cache.json_set(key, cd)
        await call.answer(stx.get("exit", "Cancelled"), show_alert=False)
        text = i18n.get("settings.menu", lang)
        text = "".join(text) if isinstance(text, list) else str(text)
        await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
        return

    if command == "position":
        page = int(parts[2]) if len(parts) > 2 else 0
        cd["page"] = page
        await cache.json_set(key, cd)
        if prefix == "CSK":
            s = get_settings()
            option = parts[3] if len(parts) > 3 else "crypto"
            items_list = s.crypto_list if option == "crypto" else s.company_list
            items = [{"code": c, "emoji": ""} for c in items_list]
        else:
            items = get_currencies_data()
        await call.message.edit_text(
            call.message.text or "Select:",
            reply_markup=paginated_currency_keyboard(items, page, prefix, i18n, lang, selected=data),
        )
        return

    # Toggle currency
    item = " ".join(parts[1:])
    if prefix == "BaseCurrency":
        data = [item]  # Only one selection allowed
        await call.answer(stx.get("alert add", "Added"), show_alert=False)
    else:
        if item in data:
            data.remove(item)
            await call.answer(stx.get("alert remove", "Removed"), show_alert=False)
        else:
            data.append(item)
            await call.answer(stx.get("alert add", "Added"), show_alert=False)

    cd["update data"] = data
    await cache.json_set(key, cd)

    # Re-render keyboard with dynamic selected list
    page = cd.get("page", 0)
    if prefix == "CSK":
        s = get_settings()
        update_type = cd.get("update type")
        items_list = s.crypto_list if update_type == "Crypto currency" else s.company_list
        items = [{"code": c, "emoji": ""} for c in items_list]
    else:
        items = get_currencies_data()

    # Build text with current selected list
    base_text = str(i18n.get("settings.output", lang))
    if prefix == "BaseCurrency":
        base_text = str(stx.get("base_currency_desc", "Select:"))
    selected_line = _selected_text(stx, data)
    display_text = f"{base_text}\n\n{selected_line}"

    try:
        await call.message.edit_text(
            display_text, reply_markup=paginated_currency_keyboard(items, page, prefix, i18n, lang, selected=data)
        )
    except Exception:
        pass


# ── Big Buttons toggle ─────────────────────────────────────────────


@router.callback_query(F.data == "toggle_big_buttons")
async def cb_toggle_big_buttons(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    uid = call.from_user.id
    db = get_db()
    user = await db["Users"].find_one({"_id": uid}, {"BigButtons": 1})
    current = (user or {}).get("BigButtons", False)
    new_value = not current
    await db["Users"].update_one({"_id": uid}, {"$set": {"BigButtons": new_value}})

    stx = i18n.get_section("settings", lang)
    if new_value:
        msg = stx.get("big_buttons_on", "📏 Big buttons enabled!")
    else:
        msg = stx.get("big_buttons_off", "📏 Big buttons disabled.")

    await call.answer(show_alert=False)
    text = i18n.get("settings.menu", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    try:
        await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
    except TelegramBadRequest:
        pass

    # Refresh the reply keyboard with new size
    kb = await get_main_keyboard(uid)
    await call.message.answer(msg, reply_markup=kb)


# ── Main Menu customisation ────────────────────────────────────────


@router.callback_query(F.data == "settings_main_menu")
async def cb_main_menu(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    uid = call.from_user.id
    key = await _cache_key(uid)
    cd = (await cache.json_get(key)) or {}
    db = get_db()
    user = await db["Users"].find_one({"_id": uid}, {"MainMenu": 1})
    cd["update type"] = "MainMenu"
    cd["update data"] = (user or {}).get("MainMenu", [])
    cd["page"] = 0
    await cache.json_set(key, cd)
    currencies = get_currencies_data()
    stx = i18n.get_section("settings", lang)
    title = stx.get("main_menu_title", "Main Menu Settings")
    desc = stx.get("main_menu_description", "Select up to 9 currencies:")
    selected_line = _selected_text(stx, cd["update data"])
    await call.message.edit_text(
        f"{title}\n\n{desc}\n\n{selected_line}",
        reply_markup=paginated_currency_keyboard(currencies, 0, "MainMenu", i18n, lang, selected=cd["update data"]),
    )


@router.callback_query(F.data.regexp(r"^MainMenu "))
async def cb_main_menu_action(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    parts = call.data.split()
    command = parts[1] if len(parts) > 1 else ""
    uid = call.from_user.id
    key = await _cache_key(uid)
    cd = (await cache.json_get(key)) or {}
    data = cd.get("update data", [])
    stx = i18n.get_section("settings", lang)
    db = get_db()

    if command == "save":
        await db["Users"].update_one({"_id": uid}, {"$set": {"MainMenu": data}})
        await call.answer(stx.get("success", "Saved"))
        cd["update data"] = []
        await cache.json_set(key, cd)
        text = i18n.get("settings.menu", lang)
        text = "".join(text) if isinstance(text, list) else str(text)
        await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
        kb = await get_main_keyboard(uid)
        await call.message.answer(stx.get("success", "Done!"), reply_markup=kb)
        return

    if command == "cancel":
        cd["update data"] = []
        await cache.json_set(key, cd)
        await call.answer(stx.get("exit", "Cancelled"))
        text = i18n.get("settings.menu", lang)
        text = "".join(text) if isinstance(text, list) else str(text)
        await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
        return

    if command == "reset":
        await db["Users"].update_one({"_id": uid}, {"$unset": {"MainMenu": ""}})
        await call.answer(stx.get("success", "Reset!"))
        cd["update data"] = []
        await cache.json_set(key, cd)
        text = i18n.get("settings.menu", lang)
        text = "".join(text) if isinstance(text, list) else str(text)
        await call.message.edit_text(text, reply_markup=settings_menu(i18n, lang))
        kb = await get_main_keyboard(uid)
        await call.message.answer(stx.get("success", "Reset!"), reply_markup=kb)
        return

    if command == "position":
        page = int(parts[2]) if len(parts) > 2 else 0
        cd["page"] = page
        await cache.json_set(key, cd)
        currencies = get_currencies_data()
        await call.message.edit_text(
            call.message.text or "Select:",
            reply_markup=paginated_currency_keyboard(currencies, page, "MainMenu", i18n, lang, selected=data),
        )
        return

    # Toggle
    code = command
    if code in data:
        data.remove(code)
        await call.answer(stx.get("alert remove", "Removed"))
    else:
        if len(data) >= 9:
            await call.answer(stx.get("main_menu_limit", "Max 9!"), show_alert=True)
            return
        data.append(code)
        await call.answer(stx.get("alert add", "Added"))
    cd["update data"] = data
    await cache.json_set(key, cd)

    # Re-render keyboard with dynamic selected list
    page = cd.get("page", 0)
    currencies = get_currencies_data()
    title = stx.get("main_menu_title", "Main Menu Settings")
    desc = stx.get("main_menu_description", "Select up to 9 currencies:")
    selected_line = _selected_text(stx, data)
    display_text = f"{title}\n\n{desc}\n\n{selected_line}"
    try:
        await call.message.edit_text(
            display_text,
            reply_markup=paginated_currency_keyboard(currencies, page, "MainMenu", i18n, lang, selected=data),
        )
    except Exception:
        pass


# ── Help Q&A callback ──────────────────────────────────────────────


@router.callback_query(F.data == "q&a")
async def cb_qa(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    from app.keyboards.inline import help_keyboard

    text = i18n.get("other.help.q&a", lang)
    text = "".join(text) if isinstance(text, list) else str(text)
    await call.message.edit_text(text, reply_markup=help_keyboard(i18n, lang, False), parse_mode="HTML")


@router.callback_query(F.data == "delete")
async def cb_delete(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    try:
        await call.message.delete()
    except Exception:
        await call.answer(str(i18n.get("other.error", lang)), show_alert=False)
