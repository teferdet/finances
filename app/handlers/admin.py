"""
Admin panel handler — admin-only commands and inline controls.
"""

from __future__ import annotations
import os
import sys
import time
import platform
import json
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import StateFilter
import asyncio

from app.config import get_settings, save_settings, CONFIG_DIR
from app.db import get_db, get_broadcast_audience_stats
from app.i18n import I18n
from app.logger import get_logger
from app.state import active_broadcast_tasks
from app.services.export_service import export_stats_csv, export_stats_markdown

log = get_logger("admin")
router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_parser_interval = State()

class BroadcastStates(StatesGroup):
    choosing_target = State()
    waiting_for_text = State()
    confirming = State()

class AdminManagementStates(StatesGroup):
    waiting_for_new_admin_id = State()
    waiting_for_remove_admin_id = State()


def _is_admin(user_id: int) -> bool:
    from app.state import dynamic_admin_ids
    return user_id in get_settings().bot.admin_ids or user_id in dynamic_admin_ids


def _admin_kb(i18n: I18n, lang: str, user_id: int) -> InlineKeyboardMarkup:
    t = lambda k: str(i18n.get(f"admin.{k}", lang))
    
    builder = InlineKeyboardBuilder()
    builder.button(text=t("dashboard_btn"), callback_data="admin_dashboard")
    builder.button(text=t("config"), callback_data="admin_config")
    builder.button(text=t("errors"), callback_data="admin_errors")
    builder.button(text=t("broadcast"), callback_data="admin_broadcast")
    builder.button(text=t("diagnostics_btn"), callback_data="admin_diagnostics")
    
    if user_id in get_settings().bot.admin_ids:
        builder.button(text=str(i18n.get("admin.manage_admins_btn", lang)), callback_data="admin_manage_admins")
        
    builder.button(text=t("restart_bot"), callback_data="admin_restart")
    builder.button(text=t("shutdown_bot"), callback_data="admin_shutdown")
    
    builder.adjust(2)
    return builder.as_markup()


def _get_recent_errors(hours: int = 3) -> str:
    from app.config import LOGS_DIR
    import re

    error_log_path = LOGS_DIR / "errors.log"
    if not error_log_path.exists():
        return ""

    cutoff_time = datetime.now() - timedelta(hours=hours)
    recent_errors = []
    # format: 2026-06-20 16:15:26 [ERROR] ...
    time_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

    try:
        with open(error_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                match = time_pattern.match(line)
                if match:
                    try:
                        log_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                        if log_time >= cutoff_time:
                            # shorten line to max 100 chars
                            short_line = line.strip()[:100]
                            recent_errors.append(short_line)
                    except ValueError:
                        pass
        return "\n".join(recent_errors[-10:])  # max 10 lines
    except Exception as e:
        log.warning("Failed to read errors: %s", e)
        return ""


@router.message(Command("admin"))
async def cmd_admin(message: Message, i18n: I18n, lang: str, state: FSMContext) -> None:
    await state.clear()
    if not _is_admin(message.from_user.id):
        await message.answer(str(i18n.get("admin.access_denied", lang)))
        return
    await message.answer(str(i18n.get("admin.panel", lang)), reply_markup=_admin_kb(i18n, lang, message.from_user.id), parse_mode="HTML")


@router.message(Command("ping"))
async def cmd_ping(message: Message, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return
    start_time = time.time()
    msg = await message.answer(str(i18n.get("admin.pong", lang)))
    end_time = time.time()
    ping_ms = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(
        str(i18n.get("admin.pong_details", lang)).format(ping_ms=ping_ms),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_"))
async def cb_admin(call: CallbackQuery, i18n: I18n, lang: str, state: FSMContext) -> None:
    callback_start_time = time.time()

    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return

    action = call.data.replace("admin_", "")

    def t(k):
        return str(i18n.get(f"admin.{k}", lang))

    db = get_db()

    # Restart logic
    if action == "restart":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=t("restart_yes"), callback_data="admin_confirm_restart"),
                    InlineKeyboardButton(text=t("restart_no"), callback_data="admin_cancel_restart"),
                ]
            ]
        )
        await call.message.edit_text(t("restart_prompt"), reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "confirm_restart":
        await call.message.edit_text(t("restarting"), parse_mode="HTML")
        log.info("Restart command initiated by admin %s", call.from_user.id)

        state_path = CONFIG_DIR / ".restart_state.json"
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "chat_id": call.message.chat.id,
                        "message_id": call.message.message_id,
                    },
                    f,
                )
        except Exception as e:
            log.error("Failed to save restart state: %s", e)

        try:
            from app.db import close_db

            await close_db()
        except Exception as exc:
            log.warning("Error during pre-restart cleanup: %s", exc)

        try:
            await call.bot.session.close()
        except Exception:
            pass

        os.execv(sys.executable, [sys.executable, "-m", "app"] + sys.argv[1:])
        await call.answer()
        return

    if action == "shutdown":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=t("restart_yes"), callback_data="admin_confirm_shutdown"),
                    InlineKeyboardButton(text=t("restart_no"), callback_data="admin_cancel_restart"),
                ]
            ]
        )
        await call.message.edit_text(t("shutdown_prompt"), reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "confirm_shutdown":
        await call.message.edit_text(t("shutting_down"), parse_mode="HTML")
        log.info("Shutdown command initiated by admin %s", call.from_user.id)

        try:
            from app.db import close_db
            await close_db()
        except Exception as exc:
            log.warning("Error during pre-shutdown cleanup: %s", exc)

        try:
            await call.bot.session.close()
        except Exception:
            pass

        os._exit(0)
        await call.answer()
        return

    if action == "manage_admins":
        if call.from_user.id not in get_settings().bot.admin_ids:
            await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
            return
            
        from app.state import dynamic_admin_ids
        admin_list = "\n".join(f"• <code>{admin_id}</code>" for admin_id in dynamic_admin_ids)
        if not admin_list:
            admin_list = "—"
            
        text = f"<b>{i18n.get('admin.manage_admins_title', lang)}</b>\n\n{admin_list}"
        
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=str(i18n.get("admin.add_admin_btn", lang)), callback_data="admin_add_admin"),
                    InlineKeyboardButton(text=str(i18n.get("admin.remove_admin_btn", lang)), callback_data="admin_remove_admin"),
                ],
                [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
            ]
        )
        
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if action == "add_admin":
        if call.from_user.id not in get_settings().bot.admin_ids:
            await call.answer()
        return
        await state.set_state(AdminManagementStates.waiting_for_new_admin_id)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
        await call.message.edit_text(str(i18n.get("admin.add_admin_prompt", lang)), reply_markup=kb, parse_mode="HTML")
        return

    if action == "remove_admin":
        if call.from_user.id not in get_settings().bot.admin_ids:
            await call.answer()
        return
        await state.set_state(AdminManagementStates.waiting_for_remove_admin_id)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
        await call.message.edit_text(str(i18n.get("admin.remove_admin_prompt", lang)), reply_markup=kb, parse_mode="HTML")
        return

    if action == "cancel_restart":
        await call.message.edit_text(t("panel"), reply_markup=_admin_kb(i18n, lang, call.from_user.id), parse_mode="HTML")
        await call.answer()
        return

    if action == "back":
        await state.clear()
        await call.message.edit_text(t("panel"), reply_markup=_admin_kb(i18n, lang, call.from_user.id), parse_mode="HTML")
        await call.answer()
        return

    if action == "dashboard":
        today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_users = await db["Users"].count_documents({})
        dau = await db["Users"].count_documents({"last_active": {"$gte": today_midnight}})

        errors_today = 0
        from app.config import LOGS_DIR

        error_log_path = LOGS_DIR / "errors.log"
        if error_log_path.exists():
            today_str = datetime.now().strftime("%Y-%m-%d")
            try:
                with open(error_log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    errors_today = sum(1 for line in lines if line.startswith(today_str))
            except Exception:
                pass

        cycles_today = 0
        bot_log_path = LOGS_DIR / "bot.log"
        if bot_log_path.exists():
            today_str = datetime.now().strftime("%Y-%m-%d")
            try:
                with open(bot_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith(today_str) and "Cycle done in" in line:
                            cycles_today += 1
            except Exception:
                pass

        text = (
            f"{t('dashboard_title')}\n\n"
            f"👥 Users Total: <code>{total_users}</code>\n"
            f"🔥 Active Today (DAU): <code>{dau}</code>\n"
            f"🔄 Parser Cycles Today: <code>{cycles_today}</code>\n"
            f"❌ Errors Today: <code>{errors_today}</code>\n"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=t("dashboard_requests"), callback_data="admin_dash_reqs"),
                    InlineKeyboardButton(text=t("dashboard_db"), callback_data="admin_dash_db"),
                ],
                [
                    InlineKeyboardButton(text=t("dashboard_problems"), callback_data="admin_dash_probs"),
                    InlineKeyboardButton(text=t("dashboard_export"), callback_data="admin_dash_export"),
                ],
                [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
            ]
        )
        try:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
        await call.answer()
        return

    if action == "dash_reqs":
        wau_time = datetime.now() - timedelta(days=7)
        mau_time = datetime.now() - timedelta(days=30)
        wau = await db["Users"].count_documents({"last_active": {"$gte": wau_time}})
        mau = await db["Users"].count_documents({"last_active": {"$gte": mau_time}})

        users_list = await db["Users"].find().to_list(length=None)
        total_reqs = sum(u.get("stats", {}).get("total_requests", 0) for u in users_list)

        # Daily/Weekly stats
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_doc = await db["DailyStats"].find_one({"_id": today_str})
        daily_reqs = daily_doc.get("requests", 0) if daily_doc else 0

        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        cursor = db["DailyStats"].find({"_id": {"$in": dates}})
        weekly_reqs = sum(doc.get("requests", 0) for doc in await cursor.to_list(length=7))

        text = (
            f"📅 <b>Requests & Activity</b>\n\n"
            f"Requests Today: <code>{daily_reqs}</code>\n"
            f"Requests This Week: <code>{weekly_reqs}</code>\n\n"
            f"Weekly Active (WAU): <code>{wau}</code>\n"
            f"Monthly Active (MAU): <code>{mau}</code>\n"
            f"Total Lifetime Requests: <code>{total_reqs}</code>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]]
        )
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "dash_db":
        collections = await db.list_collection_names()
        db_stats = await db.command("dbstats")
        size_mb = db_stats.get("dataSize", 0) / (1024 * 1024)

        col_text = ""
        for c in collections:
            cnt = await db[c].count_documents({})
            col_text += f" - {c}: <code>{cnt}</code>\n"

        text = (
            f"🗄️ <b>Database Statistics</b>\n\nTotal Data Size: <code>{size_mb:.2f} MB</code>\nCollections:\n{col_text}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]]
        )
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "dash_probs":
        from app.services.error_tracking import get_active_errors
        errors = await get_active_errors()
        
        if not errors:
            text = "⚠️ <b>Problematic Data Sources</b>\n\n✅ All data sources are operating normally."
        else:
            lines = ["⚠️ <b>Problematic Data Sources</b>\n"]
            for err in errors:
                lines.append(
                    f"🔴 <b>{err['_id']}</b>\n"
                    f"└ Count: {err.get('error_count', 1)} | Last error: <code>{err.get('last_error', 'Unknown')}</code>\n"
                )
            text = "\n".join(lines)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]]
        )
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "dash_export":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=t("export_csv"), callback_data="admin_export_csv"),
                    InlineKeyboardButton(text=t("export_markdown"), callback_data="admin_export_md"),
                ],
                [InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")],
            ]
        )
        await call.message.edit_text(f"{t('dashboard_export')}", reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "export_csv":
        await call.answer()
        csv_io = await export_stats_csv(db)
        await call.message.answer_document(BufferedInputFile(csv_io.getvalue(), filename="stats.csv"))
        return

    if action == "export_md":
        await call.answer()
        md_io = await export_stats_markdown(db)
        await call.message.answer_document(BufferedInputFile(md_io.getvalue(), filename="stats.md"))
        return

    if action in ("config", "toggle_parser"):
        cfg = get_settings()
        if action == "toggle_parser":
            import dataclasses

            # need to mutate nested dataclass properly.
            new_parser = dataclasses.replace(cfg.parser, auto_update=not cfg.parser.auto_update)
            cfg = dataclasses.replace(cfg, parser=new_parser)
            save_settings(cfg)
            await call.answer()

        parser_status = t("parser_toggle_on") if cfg.parser.auto_update else t("parser_toggle_off")

        text = (
            f"{t('config_title')}\n\n"
            f"Auto update: {'✅' if cfg.parser.auto_update else '❌'}\n"
            f"Interval: {cfg.parser.update_interval_sec}s\n"
            f"Critical: {len(cfg.parser.critical_currencies)}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=parser_status, callback_data="admin_toggle_parser")],
                [InlineKeyboardButton(text=t("parser_change_interval"), callback_data="admin_change_interval")],
                [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
            ]
        )
        try:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
        return

    if action == "change_interval":
        await state.set_state(AdminStates.waiting_for_parser_interval)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_config")]]
        )
        await call.message.edit_text(t("parser_enter_interval"), reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "diagnostics":
        try:
            import psutil

            proc = psutil.Process()
            mem = proc.memory_info()
            ram = mem.rss / (1024 * 1024)
            cpu = proc.cpu_percent(interval=None)
            sys_mem = psutil.virtual_memory()
            res_text = (
                f"<b>RAM</b>\n"
                f"{t('resources_bot_ram')}: <code>{ram:.1f} MB</code>\n"
                f"{t('resources_sys_ram')}: <code>{sys_mem.used / (1024**3):.1f} GB</code> / "
                f"<code>{sys_mem.total / (1024**3):.1f} GB</code>\n\n"
                f"<b>CPU</b>\n{t('resources_cpu')}: <code>{cpu}%</code>\n\n"
                f"OS: {platform.system()} {platform.release()}\n"
                f"Python: {platform.python_version()}\n"
            )
        except ImportError:
            res_text = "psutil not installed\n\n"

        recent_errs = _get_recent_errors(3)
        err_text = t("diagnostics_recent_errors") + (recent_errs if recent_errs else t("error_none"))

        elapsed_ms = int((time.time() - callback_start_time) * 1000)
        time_text = t("diagnostics_response_time").format(ms=elapsed_ms)

        text = f"{t('diagnostics_title')}\n\n{res_text}\n{err_text}\n\n{time_text}"

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "broadcast":
        stats = await get_broadcast_audience_stats(db)
        
        lang_lines = "\n".join(
            f"  • {lang.upper()}: <b>{count}</b>"
            for lang, count in stats["by_language"].items()
        )
        
        stats_text = (
            f"<b>{i18n.get('broadcast.stats_title', lang)}</b>\n\n"
            f"{i18n.get('broadcast.total_users', lang)}: <b>{stats['total']}</b>\n"
            f"{i18n.get('broadcast.premium_users', lang)}: <b>{stats['premium']}</b>\n"
            f"{i18n.get('broadcast.regular_users', lang)}: <b>{stats['non_premium']}</b>\n\n"
            f"<b>{i18n.get('broadcast.by_language', lang)}</b>\n{lang_lines}\n\n"
            f"─────────────────\n"
            f"{i18n.get('broadcast.choose_target', lang)}"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=str(i18n.get("broadcast.target_all", lang)), callback_data="broadcast:target:all"))
        
        lang_buttons = []
        for lang_code, count in stats["by_language"].items():
            btn_text = str(i18n.get("broadcast.target_lang", lang)).format(lang=lang_code.upper(), count=count)
            lang_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"broadcast:target:{lang_code}"))
        
        if lang_buttons:
            builder.row(*lang_buttons, width=2)
        
        builder.row(InlineKeyboardButton(text=str(i18n.get("broadcast.cancel_button", lang)), callback_data="broadcast:cancel"))
        
        await call.message.edit_text(stats_text, parse_mode="HTML", reply_markup=builder.as_markup())
        await call.answer()
        return

    if action == "errors":
        recent_errs = _get_recent_errors(24)
        err_text = t("errors_last_24h") + (recent_errs if recent_errs else t("error_none"))
        text = f"{t('error_title')}\n\n{err_text}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t("errors_download"), callback_data="admin_download_logs")],
                [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
            ]
        )
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return

    if action == "download_logs":
        # Double check admin explicitly
        if call.from_user.id not in get_settings().bot.admin_ids:
            log.warning(f"Unauthorized log download attempt by {call.from_user.id}")
            await call.answer(t("errors_auth_failed"), show_alert=True)
            return

        from app.config import LOGS_DIR

        error_log_path = LOGS_DIR / "errors.log"
        if error_log_path.exists():
            await call.message.answer_document(BufferedInputFile.from_file(error_log_path, filename="errors.log"))
        else:
            await call.answer(t("error_none"))
        return

    await call.answer(t("unknown_action"))


@router.message(AdminStates.waiting_for_parser_interval)
async def process_parser_interval(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return
    def t(k):
        return str(i18n.get(f"admin.{k}", lang))

    try:
        val = int(message.text)
        if val < 10 or val > 86400:  # reasonable limits
            raise ValueError
    except (ValueError, TypeError):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_config")]]
        )
        await message.answer(t("parser_invalid_interval"), reply_markup=kb)
        return

    import dataclasses

    cfg = get_settings()
    new_parser = dataclasses.replace(cfg.parser, update_interval_sec=val)
    cfg = dataclasses.replace(cfg, parser=new_parser)
    save_settings(cfg)

    await state.clear()

    text = (
        f"{t('config_title')}\n\n"
        f"Auto update: {'✅' if cfg.parser.auto_update else '❌'}\n"
        f"Interval: {cfg.parser.update_interval_sec}s\n"
        f"Critical: {len(cfg.parser.critical_currencies)}"
    )

    parser_status = t("parser_toggle_on") if cfg.parser.auto_update else t("parser_toggle_off")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=parser_status, callback_data="admin_toggle_parser")],
            [InlineKeyboardButton(text=t("parser_change_interval"), callback_data="admin_change_interval")],
            [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
        ]
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# ── Broadcast Feature ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("broadcast:target:"))
async def broadcast_target_chosen(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return
    target = call.data.split(":")[-1]
    await state.update_data(target=target)
    await state.set_state(BroadcastStates.waiting_for_text)
    
    target_label = str(i18n.get("broadcast.target_all", lang)) if target == "all" else str(i18n.get("broadcast.target_lang", lang)).format(lang=target.upper(), count="")
    
    await call.message.edit_text(
        f"✏️ <b>{target_label}</b>\n\n"
        f"Send the message you wish to broadcast.\n"
        f"Standard Telegram HTML formatting is supported.\n\n"
        f"Send /cancel to abort.",
        parse_mode="HTML",
    )
    await call.answer()

@router.callback_query(F.data == "broadcast:cancel")
async def broadcast_cancel_callback(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i18n.get("admin.back", lang)), callback_data="admin_back")]])
    await call.message.edit_text(str(i18n.get("broadcast.cancelled", lang)), reply_markup=kb)
    await call.answer()

@router.message(StateFilter(BroadcastStates.waiting_for_text), Command("cancel"))
async def cancel_broadcast_cmd(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i18n.get("admin.back", lang)), callback_data="admin_back")]])
    await message.answer(str(i18n.get("broadcast.cancelled", lang)), parse_mode="HTML", reply_markup=kb)

@router.message(StateFilter(BroadcastStates.waiting_for_text), F.text, ~Command("cancel"))
async def broadcast_text_received(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(message.from_user.id):
        return
    text = message.text or ""
    await state.update_data(broadcast_text=text)
    await state.set_state(BroadcastStates.confirming)
    
    fsm_data = await state.get_data()
    target = fsm_data.get("target", "all")
    target_label = str(i18n.get("broadcast.target_all", lang)) if target == "all" else str(i18n.get("broadcast.target_lang", lang)).format(lang=target.upper(), count="")
    
    builder = InlineKeyboardBuilder()
    builder.button(text=str(i18n.get("broadcast.confirm_button", lang)), callback_data="broadcast:confirm")
    builder.button(text=str(i18n.get("broadcast.cancel_button", lang)), callback_data="broadcast:cancel_confirmed")
    builder.adjust(1)
    
    await message.answer(
        f"<b>{i18n.get('broadcast.preview_title', lang)}</b>\n"
        f"🎯 Target: <b>{target_label}</b>\n\n"
        f"─────────────────\n"
        f"{text}\n"
        f"─────────────────\n\n"
        f"⏰ Will be sent in <b>5 minutes</b> after confirmation.",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

@router.callback_query(F.data == "broadcast:cancel_confirmed")
async def broadcast_cancel_confirmed(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i18n.get("admin.back", lang)), callback_data="admin_back")]])
    await call.message.edit_text(str(i18n.get("broadcast.cancelled", lang)), reply_markup=kb)
    await call.answer()

BROADCAST_DELAY_SECONDS = 300  # 5 minutes

@router.callback_query(F.data == "broadcast:confirm")
async def broadcast_confirmed(call: CallbackQuery, state: FSMContext, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return
    fsm_data = await state.get_data()
    broadcast_text: str = fsm_data.get("broadcast_text", "")
    target: str = fsm_data.get("target", "all")
    admin_id: int = call.from_user.id
    
    await state.clear()
    
    send_at = datetime.utcnow() + timedelta(seconds=BROADCAST_DELAY_SECONDS)
    
    abort_builder = InlineKeyboardBuilder()
    abort_builder.button(
        text=f"{i18n.get('broadcast.abort_button', lang)} (until {send_at.strftime('%H:%M UTC')})",
        callback_data=f"broadcast:abort:{admin_id}",
    )
    
    target_label = str(i18n.get("broadcast.target_all", lang)) if target == "all" else target.upper()
    
    confirmation_msg = await call.message.edit_text(
        f"<b>{i18n.get('broadcast.scheduled', lang)}</b>\n\n"
        f"🕐 Will be sent at: <b>{send_at.strftime('%H:%M UTC')}</b>\n"
        f"🎯 Target: <b>{target_label}</b>\n\n"
        f"You can cancel it until the timer runs out.",
        parse_mode="HTML",
        reply_markup=abort_builder.as_markup(),
    )
    
    bot = call.bot
    db = get_db()
    
    task = asyncio.create_task(
        _delayed_broadcast(
            bot=bot,
            db=db,
            admin_id=admin_id,
            broadcast_text=broadcast_text,
            target=target,
            confirmation_message=confirmation_msg,
            admin_chat_id=call.message.chat.id,
            i18n=i18n,
            lang=lang
        )
    )
    active_broadcast_tasks[admin_id] = task
    await call.answer(str(i18n.get("broadcast.scheduled", lang)))


@router.callback_query(F.data.startswith("broadcast:abort:"))
async def broadcast_abort(call: CallbackQuery, i18n: I18n, lang: str) -> None:
    if not _is_admin(call.from_user.id):
        await call.answer(str(i18n.get("admin.access_denied", lang)), show_alert=True)
        return
    admin_id = int(call.data.split(":")[-1])
    task = active_broadcast_tasks.get(admin_id)
    
    if task and not task.done():
        task.cancel()
        active_broadcast_tasks.pop(admin_id, None)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i18n.get("admin.back", lang)), callback_data="admin_back")]])
        await call.message.edit_text(f"<b>{i18n.get('broadcast.cancelled', lang)}</b>", parse_mode="HTML", reply_markup=kb)
        await call.answer(str(i18n.get("broadcast.cancelled", lang)))
    else:
        await call.answer(str(i18n.get("broadcast.not_found", lang)), show_alert=True)

async def _delayed_broadcast(
    bot,
    db,
    admin_id: int,
    broadcast_text: str,
    target: str,
    confirmation_message: Message,
    admin_chat_id: int,
    i18n: I18n,
    lang: str
) -> None:
    try:
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)
    except asyncio.CancelledError:
        return  # Cancelled by admin
    
    active_broadcast_tasks.pop(admin_id, None)
    
    query_filter = {} if target == "all" else {"Language": target}
    users_collection = db["Users"]
    cursor = users_collection.find(query_filter, {"_id": 1})
    
    success_count = 0
    fail_count = 0
    
    async for user_doc in cursor:
        user_id = user_doc.get("_id")
        if not user_id:
            continue
        try:
            await bot.send_message(chat_id=user_id, text=broadcast_text, parse_mode="HTML")
            success_count += 1
        except Exception:
            fail_count += 1
        
        await asyncio.sleep(0.04)  # Throttling
    
    target_label = str(i18n.get("broadcast.target_all", lang)) if target == "all" else target.upper()
    sent_text = str(i18n.get("broadcast.sent", lang)).format(count=success_count)
    failed_text = str(i18n.get("broadcast.failed", lang)).format(count=fail_count)
    
    report = (
        f"<b>{i18n.get('broadcast.complete', lang)}</b>\n\n"
        f"{sent_text}\n"
        f"{failed_text}\n"
        f"🎯 Target: <b>{target_label}</b>"
    )
    
    try:
        await bot.send_message(admin_chat_id, report, parse_mode="HTML")
        # Edit confirmation message safely (if it wasn't deleted)
        try:
            await bot.edit_message_text(
                chat_id=confirmation_message.chat.id,
                message_id=confirmation_message.message_id,
                text=report + "\n\n<i>Broadcast finished.</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass
    except Exception:
        pass

# ── Admin Management ──────────────────────────────────────────────────────────

@router.message(StateFilter(AdminManagementStates.waiting_for_new_admin_id))
async def process_new_admin_id(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    try:
        new_admin_id = int(message.text)
    except (ValueError, TypeError):
        await message.answer(str(i18n.get("admin.invalid_user_id", lang)))
        return

    from app.state import dynamic_admin_ids
    db = get_db()
    
    dynamic_admin_ids.add(new_admin_id)
    await db["Settings"].update_one(
        {"_id": "dynamic_admins"},
        {"$addToSet": {"admin_ids": new_admin_id}},
        upsert=True
    )
    
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i18n.get("admin.back", lang)), callback_data="admin_manage_admins")]])
    await message.answer(str(i18n.get("admin.admin_added", lang)), reply_markup=kb)

@router.message(StateFilter(AdminManagementStates.waiting_for_remove_admin_id))
async def process_remove_admin_id(message: Message, state: FSMContext, i18n: I18n, lang: str) -> None:
    try:
        remove_admin_id = int(message.text)
    except (ValueError, TypeError):
        await message.answer(str(i18n.get("admin.invalid_user_id", lang)))
        return

    from app.state import dynamic_admin_ids
    db = get_db()
    
    dynamic_admin_ids.discard(remove_admin_id)
    await db["Settings"].update_one(
        {"_id": "dynamic_admins"},
        {"$pull": {"admin_ids": remove_admin_id}}
    )
    
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i18n.get("admin.back", lang)), callback_data="admin_manage_admins")]])
    await message.answer(str(i18n.get("admin.admin_removed", lang)), reply_markup=kb)
