"""
Exchange API handler — binds Binance/Bybit API keys and syncs portfolio.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.db import get_db
from app.i18n import I18n
from app.services.security import encrypt_data
from app.services.exchange_sync import sync_exchange_portfolio
from app.handlers.portfolio import cb_portfolio_refresh

router = Router(name="exchange_api")


class ExchangeStates(StatesGroup):
    waiting_for_exchange = State()
    waiting_for_api_key = State()
    waiting_for_api_secret = State()


def select_exchange_keyboard() -> InlineKeyboardMarkup:
    """Generate inline keyboard for selecting exchange."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Binance", callback_data="exchange_select:Binance"),
            InlineKeyboardButton(text="Bybit", callback_data="exchange_select:Bybit")
        ]
    ])


@router.callback_query(F.data == "exchange_bind")
async def cb_exchange_bind(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"exchange.{k}", lang))
    await call.answer()

    text = f"{t('menu_title')}\n\n{t('menu_desc')}"
    await call.message.edit_text(text, reply_markup=select_exchange_keyboard(), parse_mode="HTML")
    await state.set_state(ExchangeStates.waiting_for_exchange)


@router.callback_query(ExchangeStates.waiting_for_exchange, F.data.startswith("exchange_select:"))
async def cb_exchange_select(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"exchange.{k}", lang))
    await call.answer()

    exchange_name = call.data.split(":")[1]
    await state.update_data(exchange_name=exchange_name)

    text = t("prompt_api_key").replace("{exchange}", exchange_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_cancel"), callback_data="exchange_cancel")
    ]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(ExchangeStates.waiting_for_api_key)


@router.message(ExchangeStates.waiting_for_api_key)
async def process_api_key(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"exchange.{k}", lang))
    api_key = message.text.strip()

    # Delete the user's message with the API key for security
    try:
        await message.delete()
    except Exception:
        pass

    await state.update_data(api_key=api_key)

    data = await state.get_data()
    exchange_name = data["exchange_name"]

    text = t("prompt_api_secret").replace("{exchange}", exchange_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_cancel"), callback_data="exchange_cancel")
    ]])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(ExchangeStates.waiting_for_api_secret)


@router.message(ExchangeStates.waiting_for_api_secret)
async def process_api_secret(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"exchange.{k}", lang))
    api_secret = message.text.strip()

    # Delete the user's message with the secret key for security
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    exchange_name = data["exchange_name"]
    api_key = data["api_key"]

    encrypted_secret = encrypt_data(api_secret)

    # Save to DB
    db = get_db()
    await db["ApiKeys"].update_one(
        {"user_id": message.from_user.id, "exchange": exchange_name},
        {"$set": {
            "api_key": api_key,
            "api_secret": encrypted_secret,
        }},
        upsert=True
    )

    await state.clear()
    text = t("success_bind").replace("{exchange}", exchange_name)
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "exchange_cancel")
async def cb_exchange_cancel(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"exchange.{k}", lang))
    await call.answer()
    await state.clear()
    text = t("cancel_msg")
    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "exchange_sync")
async def cb_exchange_sync(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"exchange.{k}", lang))
    await call.answer()

    db = get_db()
    keys = await db["ApiKeys"].find({"user_id": call.from_user.id}).to_list(length=10)

    if not keys:
        await call.message.answer(t("no_keys"), parse_mode="HTML")
        return

    for key_doc in keys:
        exchange_name = key_doc["exchange"]
        msg = await call.message.answer(t("syncing").replace("{exchange}", exchange_name), parse_mode="HTML")

        result = await sync_exchange_portfolio(call.from_user.id, exchange_name)

        if result["status"] == "cooldown":
            text = t("sync_cooldown").replace("{minutes}", str(result["minutes"]))
            await msg.edit_text(text, parse_mode="HTML")
        elif result["status"] == "error":
            text = t("sync_error").replace("{exchange}", exchange_name).replace("{error}", result["message"])
            await msg.edit_text(text, parse_mode="HTML")
        elif result["status"] == "success":
            text = t("sync_success").replace("{count}", str(result["count"]))
            await msg.edit_text(text, parse_mode="HTML")

    # Automatically refresh the portfolio view after sync
    await cb_portfolio_refresh(call, i18n, lang)
