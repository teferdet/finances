"""
Alert handler — /alert command, inline CRUD, volatility threshold.

Usage:
    /alert                          → show alert menu
    /alert BTC USD below 50000      → quick-create alert
    /alert volatility 3             → set volatility threshold to 3%
"""

from __future__ import annotations

import re
import math
from datetime import datetime, timezone

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
from app.logger import get_logger

log = get_logger("alerts")
router = Router(name="alerts")

# ── FSM-like state via in-memory dict (per-user) ───────────────────
_waiting_for_alert: set[int] = set()


# ── Keyboards ──────────────────────────────────────────────────────


def _alert_menu_kb(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    t = lambda k: str(i18n.get(f"alerts.{k}", lang))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_my_alerts"), callback_data="alert_my"),
                InlineKeyboardButton(text=t("btn_new_alert"), callback_data="alert_new"),
            ],
            [
                InlineKeyboardButton(text=t("btn_clear_all"), callback_data="alert_clear"),
            ],
        ]
    )


def _alert_back_kb(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    t = lambda k: str(i18n.get(f"alerts.{k}", lang))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_back"), callback_data="alert_back")],
        ]
    )


def _alert_list_kb(alerts: list[dict], i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    """Build keyboard with a delete button per alert + back button."""

    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    rows = []
    for a in alerts[:10]:  # Max 10 shown
        aid = str(a["_id"])
        pair = f"{a['currency_from']}/{a['currency_to']}"
        cond = "📈" if a["condition"] == "above" else "📉"
        label = f"🗑 {pair} {cond} {a['target_price']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"alert_del:{aid}")])
    rows.append([InlineKeyboardButton(text=t("btn_back"), callback_data="alert_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── /alert command ─────────────────────────────────────────────────


async def _get_alert_menu_text(i18n: I18n, lang: str) -> str:
    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    return (
        f"{t('menu_title')}\n\n"
        f"{t('menu_description')}\n\n"
        f"{t('menu_how_to')}\n"
        f"<code>/alert BTC USD below 50000</code>\n"
        f"<code>/alert USD EUR above 0.95</code>\n\n"
        f"{t('menu_buttons_hint')}"
    )


@router.message(Command("alert"))
async def cmd_alert(message: Message, command: CommandObject, i18n: I18n, lang: str) -> None:
    from app.utils.draft import finish_initial_message_draft, process_initial_message_draft
    import asyncio

    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    args = command.args

    if not args:
        # Show menu
        loading_text = str(i18n.get("alerts.loading", "Alerts loading..."))
        task = asyncio.create_task(_get_alert_menu_text(i18n, lang))
        was_loading, text = await process_initial_message_draft(message, task, loading_text)

        await finish_initial_message_draft(message, text, was_loading)
        await message.answer(text, reply_markup=_alert_menu_kb(i18n, lang), parse_mode="HTML")
        return

    parts = args.strip().split()

    # /alert volatility <pct>
    if parts[0].lower() == "volatility":
        if len(parts) < 2:
            await message.answer(t("volatility_format_hint"), parse_mode="HTML")
            return
        try:
            pct = float(parts[1])
            if pct <= 0 or pct > 100 or math.isnan(pct) or math.isinf(pct):
                raise ValueError
        except ValueError:
            await message.answer(t("volatility_invalid_pct"), parse_mode="HTML")
            return

        db = get_db()
        await db["Users"].update_one(
            {"_id": message.from_user.id},
            {"$set": {"volatility_threshold_pct": pct}},
        )
        text = t("volatility_set").replace("{pct}", f"{pct}")
        await message.answer(text, parse_mode="HTML")
        return

    # /alert <BASE> <TARGET> above|below <price>
    await _create_alert_from_text(" ".join(parts), message.from_user.id, message, i18n, lang)


# ── Inline callback handlers ──────────────────────────────────────


@router.callback_query(F.data == "alert_back")
async def cb_alert_back(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    _waiting_for_alert.discard(call.from_user.id)
    text = (
        f"{t('menu_title')}\n\n"
        f"{t('menu_description')}\n\n"
        f"{t('menu_how_to')}\n"
        f"<code>/alert BTC USD below 50000</code>\n"
        f"<code>/alert USD EUR above 0.95</code>\n\n"
        f"{t('menu_buttons_hint')}"
    )
    await call.message.edit_text(text, reply_markup=_alert_menu_kb(i18n, lang), parse_mode="HTML")


@router.callback_query(F.data == "alert_my")
async def cb_alert_my(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    db = get_db()
    alerts = await db["Alerts"].find({"user_id": call.from_user.id, "triggered": False}).to_list(length=50)

    if not alerts:
        await call.message.edit_text(
            t("callback_no_alerts"),
            reply_markup=_alert_back_kb(i18n, lang),
            parse_mode="HTML",
        )
        return

    lines = [t("callback_active_alerts"), ""]
    for a in alerts[:10]:
        pair = f"{a['currency_from']}/{a['currency_to']}"
        cond_key = a["condition"]
        cond_text = t(cond_key)
        lines.append(f"• <b>{pair}</b> {cond_text} <code>{a['target_price']}</code>")
    text = "\n".join(lines)

    await call.message.edit_text(
        text,
        reply_markup=_alert_list_kb(alerts, i18n, lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "alert_new")
async def cb_alert_new(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    _waiting_for_alert.add(call.from_user.id)
    await call.message.edit_text(
        t("callback_new_prompt"),
        reply_markup=_alert_back_kb(i18n, lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "alert_clear")
async def cb_alert_clear(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    db = get_db()
    result = await db["Alerts"].delete_many({"user_id": call.from_user.id})
    text = t("callback_cleared")
    await call.message.edit_text(text, reply_markup=_alert_back_kb(i18n, lang), parse_mode="HTML")
    await call.answer(t("callback_deleted").replace("{count}", str(result.deleted_count)))


@router.callback_query(F.data.startswith("alert_del:"))
async def cb_alert_delete(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    def t(k):
        return str(i18n.get(f"alerts.{k}", lang))

    alert_id = call.data.split(":")[1]
    db = get_db()
    from bson import ObjectId

    try:
        await db["Alerts"].delete_one({"_id": ObjectId(alert_id), "user_id": call.from_user.id})
    except Exception:
        pass

    # Refresh list
    await cb_alert_my(call, i18n, lang)


# ── Text message handler (for FSM: waiting_for_alert) ──────────────


@router.message(F.text & ~F.text.startswith("/"), lambda msg: msg.from_user.id in _waiting_for_alert)
async def msg_alert_input(message: Message, i18n: I18n, lang: str) -> None:
    """Catch free-text alert creation when user is in 'new alert' flow."""
    _waiting_for_alert.discard(message.from_user.id)
    await _create_alert_from_text(message.text.strip(), message.from_user.id, message, i18n, lang)


# ── Shared alert creation logic ────────────────────────────────────

_CONDITION_RE = re.compile(
    r"^([A-Za-z]{2,10})\s+([A-Za-z]{2,10})\s+(above|below)\s+([\d.,]+)$",
    re.IGNORECASE,
)


async def _create_alert_from_text(text: str, user_id: int, message: Message, i18n: I18n, lang: str) -> None:
    t = lambda k: str(i18n.get(f"alerts.{k}", lang))

    m = _CONDITION_RE.match(text)
    if not m:
        await message.answer(
            t("invalid_format") + "\n<code>/alert BTC USD below 50000</code>",
            parse_mode="HTML",
        )
        return

    currency_from = m.group(1).upper()
    currency_to = m.group(2).upper()
    condition = m.group(3).lower()
    try:
        target_price = float(m.group(4).replace(",", ""))
        if target_price <= 0 or math.isnan(target_price) or math.isinf(target_price):
            raise ValueError
    except ValueError:
        await message.answer(t("invalid_format"), parse_mode="HTML")
        return

    db = get_db()

    # Limit: max 20 active alerts per user
    count = await db["Alerts"].count_documents({"user_id": user_id, "triggered": False})
    if count >= 20:
        await message.answer(t("max_alerts_reached"), parse_mode="HTML")
        return

    doc = {
        "user_id": user_id,
        "currency_from": currency_from,
        "currency_to": currency_to,
        "condition": condition,
        "target_price": target_price,
        "triggered": False,
        "created_at": datetime.now(timezone.utc),
        "triggered_at": None,
    }
    await db["Alerts"].insert_one(doc)

    cond_text = t(condition)
    result_text = (
        t("process_created")
        .replace("{currency_from}", currency_from)
        .replace("{currency_to}", currency_to)
        .replace("{condition}", cond_text)
        .replace("{target_price}", str(target_price))
    )
    await message.answer(result_text, parse_mode="HTML")
    log.info(
        "Alert created: user=%d %s/%s %s %s",
        user_id,
        currency_from,
        currency_to,
        condition,
        target_price,
    )
