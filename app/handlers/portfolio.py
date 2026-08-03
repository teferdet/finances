"""
Portfolio handler — allows users to track their assets (crypto, stocks, fiat)
with cost-basis tracking and P&L calculation.
"""

from __future__ import annotations

import re
import math
import html
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from app.db import get_db
from app.i18n import I18n
from app.config import get_currencies_data
from app.keyboards.inline import paginated_currency_keyboard
from app.services.portfolio_service import (
    add_asset,
    remove_asset,
    clear_portfolio,
    get_portfolio_with_pnl,
)

router = Router(name="portfolio")


def portfolio_keyboard(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    """Generate inline keyboard for portfolio."""
    t_port = lambda k: str(i18n.get(f"portfolio.{k}", lang))
    t_exch = lambda k: str(i18n.get(f"exchange.{k}", lang))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t_port("refresh"), callback_data="portfolio_refresh"),
                InlineKeyboardButton(text=t_port("clear"), callback_data="portfolio_clear"),
            ],
            [InlineKeyboardButton(text=t_port("btn_change_base"), callback_data="portfolio_change_base")],
            [
                InlineKeyboardButton(text=t_exch("btn_bind"), callback_data="exchange_bind"),
                InlineKeyboardButton(text=t_exch("btn_sync"), callback_data="exchange_sync"),
            ],
        ]
    )


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message, command: CommandObject, i18n: I18n, lang: str) -> None:
    """Manage and view portfolio. Usage: /portfolio [currency | add ... | remove ...]"""
    from app.utils.draft import finish_initial_message_draft, process_initial_message_draft
    import asyncio

    def t(k):
        return str(i18n.get(f"portfolio.{k}", lang))

    args = command.args

    if not args:
        db = get_db()
        user = await db["Users"].find_one({"_id": message.from_user.id}, {"BaseCurrency": 1})
        bc_data = (user or {}).get("BaseCurrency", ["USD"])
        default_bc = bc_data[0] if bc_data and isinstance(bc_data, list) else "USD"

        loading_text = str(i18n.get("portfolio.loading", "Portfolio loading..."))
        task = asyncio.create_task(_build_portfolio_text_and_kb(message.from_user.id, default_bc, i18n, lang))
        was_loading, (text, kb) = await process_initial_message_draft(message, task, loading_text)

        await finish_initial_message_draft(message, text, was_loading)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    parts = args.strip().split()
    subcmd = parts[0].lower()

    if subcmd == "add":
        # Format: /portfolio add <type> <ticker> <amount> [buy_price]
        if len(parts) < 4:
            await message.answer(t("invalid_format") + "\n" + t("format_add"), parse_mode="HTML")
            return

        asset_type = parts[1].lower()
        symbol = parts[2].upper()
        try:
            amount = float(parts[3])
            if math.isnan(amount) or math.isinf(amount) or amount <= 0:
                raise ValueError
        except ValueError:
            await message.answer(t("invalid_amount"), parse_mode="HTML")
            return

        if asset_type not in ("crypto", "stock", "fiat"):
            await message.answer(t("invalid_type"), parse_mode="HTML")
            return

        # Optional buy price (5th argument)
        buy_price: float | None = None
        if len(parts) >= 5:
            try:
                buy_price = float(parts[4])
                if math.isnan(buy_price) or math.isinf(buy_price) or buy_price <= 0:
                    raise ValueError
            except ValueError:
                await message.answer(t("invalid_buy_price"), parse_mode="HTML")
                return

        used_price = await add_asset(
            user_id=message.from_user.id,
            asset_type=asset_type,
            ticker=symbol,
            amount=amount,
            buy_price_usd=buy_price,
        )

        safe_amount = html.escape(str(amount))
        safe_symbol = html.escape(symbol)

        if buy_price is not None:
            # User explicitly provided the price
            text = (
                t("added_with_price")
                .replace("{amount}", safe_amount)
                .replace("{symbol}", safe_symbol)
                .replace("{price}", f"{buy_price:,.2f}")
            )
        elif used_price is not None:
            # Auto-detected price
            text = (
                t("added_with_price")
                .replace("{amount}", safe_amount)
                .replace("{symbol}", safe_symbol)
                .replace("{price}", f"{used_price:,.2f}")
            )
            text += "\n" + t("auto_price_used").replace("{price}", f"{used_price:,.2f}")
        else:
            # No price available at all
            text = t("added").replace("{amount}", safe_amount).replace("{symbol}", safe_symbol)

        await message.answer(text, parse_mode="HTML")

    elif subcmd == "remove":
        if len(parts) < 2:
            await message.answer(t("format_remove"), parse_mode="HTML")
            return

        symbol = parts[1].upper()
        removed = await remove_asset(message.from_user.id, symbol)

        safe_symbol = html.escape(symbol)

        if not removed:
            await message.answer(t("not_found").replace("{symbol}", safe_symbol), parse_mode="HTML")
            return

        text = t("removed").replace("{symbol}", safe_symbol)
        await message.answer(text, parse_mode="HTML")

    else:
        # Treat the argument as a base currency (e.g. /portfolio EUR)
        base_currency = subcmd[:3].upper()
        await _show_portfolio(message, message.from_user.id, base_currency, i18n, lang)


# ── Portfolio display with P&L ─────────────────────────────────────


def _format_number(value: float, decimals: int = 2) -> str:
    """Format a number with thousands separators."""
    if abs(value) >= 1:
        return f"{value:,.{decimals}f}"
    elif abs(value) >= 0.01:
        return f"{value:,.4f}"
    else:
        return f"{value:,.6f}"


def _format_pnl(pnl_abs: float | None, pnl_pct: float | None, i18n: I18n, lang: str) -> str:
    """Format P&L line with emoji indicator."""

    def t(k):
        return str(i18n.get(f"portfolio.{k}", lang))

    if pnl_abs is None or pnl_pct is None:
        return f"  <i>{t('no_buy_price')}</i>"

    if pnl_abs > 0:
        return t("pnl_positive").replace("{abs}", f"+{_format_number(pnl_abs)}").replace("{pct}", f"{pnl_pct:+.2f}")
    elif pnl_abs < 0:
        return t("pnl_negative").replace("{abs}", f"{_format_number(pnl_abs)}").replace("{pct}", f"{pnl_pct:.2f}")
    else:
        return t("pnl_neutral")


async def _build_portfolio_text_and_kb(
    user_id: int,
    base_currency: str,
    i18n: I18n,
    lang: str,
) -> tuple[str, InlineKeyboardMarkup | None]:
    def t(k):
        return str(i18n.get(f"portfolio.{k}", lang))

    pnl_data = await get_portfolio_with_pnl(user_id, base_currency)
    sections = pnl_data["sections"]

    if not sections:
        return f"{t('title')}\n\n{t('empty')}\n\n{t('add_hint')}", None

    base_sym = pnl_data["base_symbol"]
    lines = [f"{t('title')} (<b>{base_currency}</b> {base_sym})\n"]

    for sec in sections:
        header_name = t(f"section_{sec['type']}")
        lines.append(f"<b>{header_name}</b> ({sec['count']}):")

        for item in sec["items"]:
            safe_symbol = html.escape(item["symbol"])
            amt_str = _format_number(item["amount"], 4 if item["asset_type"] in ("crypto", "stock") else 2)
            lines.append(f"• <b>{safe_symbol}</b>: {amt_str}")

            if item.get("current_val_base") is not None:
                val_str = _format_number(item["current_val_base"])
                lines.append(f"  └ ≈ {val_str} {base_sym}")

            pnl_line = _format_pnl(item.get("pnl_abs_base"), item.get("pnl_pct"), i18n, lang)
            lines.append(pnl_line)

        tot_str = _format_number(sec["total_val_base"])
        lines.append(f"<i>{t('subtotal')}: {tot_str} {base_sym}</i>\n")

    grand_str = _format_number(pnl_data["grand_total_base"])
    lines.append(f"💰 <b>{t('grand_total')}: {grand_str} {base_sym}</b>")

    pnl_line = _format_pnl(pnl_data["grand_pnl_abs_base"], pnl_data["grand_pnl_pct"], i18n, lang)
    lines.append(f"📊 <b>{t('total_pnl')}:</b>\n{pnl_line}")

    kb = portfolio_keyboard(i18n, lang)
    return "\n".join(lines), kb


async def _show_portfolio(
    message: Message | CallbackQuery,
    user_id: int,
    base_currency: str,
    i18n: I18n,
    lang: str,
    is_edit: bool = False,
) -> None:
    text, kb = await _build_portfolio_text_and_kb(user_id, base_currency, i18n, lang)
    if isinstance(message, Message):
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


# ── Callbacks ──────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("portfolio_refresh"))
async def cb_portfolio_refresh(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    await call.answer()

    db = get_db()
    user = await db["Users"].find_one({"_id": call.from_user.id}, {"BaseCurrency": 1})
    bc_data = (user or {}).get("BaseCurrency", ["USD"])
    base_currency = bc_data[0] if bc_data and isinstance(bc_data, list) else "USD"

    # If currency passed in callback data
    parts = call.data.split(":")
    if len(parts) > 1:
        base_currency = parts[1]
    elif call.message.text:
        match = re.search(r"\(([A-Z]{3})\)", call.message.text)
        if match:
            base_currency = match.group(1)

    await _show_portfolio(call, call.from_user.id, base_currency, i18n, lang, is_edit=True)


@router.callback_query(F.data == "portfolio_change_base")
async def cb_portfolio_change_base(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    await call.answer()

    db = get_db()
    user = await db["Users"].find_one({"_id": call.from_user.id}, {"BaseCurrency": 1})
    bc_data = (user or {}).get("BaseCurrency", ["USD"])
    base_currency = bc_data[0] if bc_data and isinstance(bc_data, list) else "USD"

    if call.message.text:
        match = re.search(r"\(([A-Z]{3})\)", call.message.text)
        if match:
            base_currency = match.group(1)

    currencies = get_currencies_data()
    title = str(i18n.get("portfolio.select_base_title", lang))

    kb = paginated_currency_keyboard(currencies, 0, "PortfolioBase", i18n, lang, selected=[base_currency])
    await call.message.edit_text(title, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^PortfolioBase "))
async def cb_portfolio_base_action(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    parts = call.data.split()
    command = parts[1] if len(parts) > 1 else ""

    if command == "cancel":
        await cb_portfolio_refresh(call, i18n, lang)
        return

    if command == "save":
        # The user's selection is in parts[2] if it was a toggle, but actually paginated_currency_keyboard
        # doesn't pass the selected state back in "save" directly, it expects us to read from cache.
        # But we can just avoid using "save" and directly trigger portfolio_refresh:CURRENCY when toggling.
        pass

    if command == "position":
        page = int(parts[2]) if len(parts) > 2 else 0
        currencies = get_currencies_data()

        # We need to know current selected from message text maybe? Or default USD.
        # Let's extract from DB.
        db = get_db()
        user = await db["Users"].find_one({"_id": call.from_user.id}, {"BaseCurrency": 1})
        bc_data = (user or {}).get("BaseCurrency", ["USD"])
        base_currency = bc_data[0] if bc_data and isinstance(bc_data, list) else "USD"

        kb = paginated_currency_keyboard(currencies, page, "PortfolioBase", i18n, lang, selected=[base_currency])
        await call.message.edit_reply_markup(reply_markup=kb)
        return

    # If it's a currency toggle (e.g. PortfolioBase USD)
    currency = " ".join(parts[1:])
    if currency and currency not in ["save", "cancel", "position"]:
        # Instead of saving state, immediately refresh portfolio with this currency
        call.data = f"portfolio_refresh:{currency}"
        await cb_portfolio_refresh(call, i18n, lang)


@router.callback_query(F.data == "portfolio_clear")
async def cb_portfolio_clear(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    await clear_portfolio(call.from_user.id)

    def t(k):
        return str(i18n.get(f"portfolio.{k}", lang))

    await call.message.edit_text(t("portfolio_cleared"), parse_mode="HTML")
    await call.answer(t("cleared"))
