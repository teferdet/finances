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

from app.config import get_settings, save_settings, CONFIG_DIR
from app.db import get_db
from app.i18n import I18n
from app.logger import get_logger
from app.services.export_service import export_stats_csv, export_stats_markdown

log = get_logger("admin")
router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_parser_interval = State()


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().bot.admin_ids


def _admin_kb(i18n: I18n, lang: str) -> InlineKeyboardMarkup:
    def t(k):
        return str(i18n.get(f"admin.{k}", lang))

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("dashboard_btn"), callback_data="admin_dashboard"),
                InlineKeyboardButton(text=t("config"), callback_data="admin_config"),
            ],
            [
                InlineKeyboardButton(text=t("errors"), callback_data="admin_errors"),
                InlineKeyboardButton(text=t("broadcast"), callback_data="admin_broadcast"),
            ],
            [InlineKeyboardButton(text=t("diagnostics_btn"), callback_data="admin_diagnostics")],
            [InlineKeyboardButton(text=t("restart_bot"), callback_data="admin_restart")],
        ]
    )


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
    await message.answer(
        str(i18n.get("admin.panel", lang)),
        reply_markup=_admin_kb(i18n, lang),
        parse_mode="HTML",
    )


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
        return

    if action == "cancel_restart":
        await call.message.edit_text(t("panel"), reply_markup=_admin_kb(i18n, lang), parse_mode="HTML")
        return

    if action == "back":
        await state.clear()
        await call.message.edit_text(t("panel"), reply_markup=_admin_kb(i18n, lang), parse_mode="HTML")
        return

    if action == "dashboard":
        today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_users = await db["Users"].count_documents({})
        dau = await db["Users"].count_documents({"last_active": {"$gte": today_midnight}})

        errors_today = 0
        from app.config import LOGS_DIR
<<<<<<< HEAD

=======
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
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

<<<<<<< HEAD
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
=======
        text = (f"{t('dashboard_title')}\n\n"
                f"👥 Users Total: <code>{total_users}</code>\n"
                f"🔥 Active Today (DAU): <code>{dau}</code>\n"
                f"🔄 Parser Cycles Today: <code>{cycles_today}</code>\n"
                f"❌ Errors Today: <code>{errors_today}</code>\n")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("dashboard_requests"), callback_data="admin_dash_reqs"),
             InlineKeyboardButton(text=t("dashboard_db"), callback_data="admin_dash_db")],
            [InlineKeyboardButton(text=t("dashboard_problems"), callback_data="admin_dash_probs"),
             InlineKeyboardButton(text=t("dashboard_export"), callback_data="admin_dash_export")],
            [InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        try:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
        return

    if action == "dash_reqs":
        wau_time = datetime.now() - timedelta(days=7)
        mau_time = datetime.now() - timedelta(days=30)
        wau = await db["Users"].count_documents({"last_active": {"$gte": wau_time}})
        mau = await db["Users"].count_documents({"last_active": {"$gte": mau_time}})

        users_list = await db["Users"].find().to_list(length=None)
        total_reqs = sum(u.get("stats", {}).get("total_requests", 0) for u in users_list)

<<<<<<< HEAD
        text = (
            f"📅 <b>Requests & Activity</b>\n\n"
            f"Weekly Active (WAU): <code>{wau}</code>\n"
            f"Monthly Active (MAU): <code>{mau}</code>\n"
            f"Total Lifetime Requests: <code>{total_reqs}</code>\n\n"
            f"<i>TODO: Daily/Weekly requests aggregation</i>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]]
        )
=======
        text = (f"📅 <b>Requests & Activity</b>\n\n"
                f"Weekly Active (WAU): <code>{wau}</code>\n"
                f"Monthly Active (MAU): <code>{mau}</code>\n"
                f"Total Lifetime Requests: <code>{total_reqs}</code>\n\n"
                f"<i>TODO: Daily/Weekly requests aggregation</i>")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if action == "dash_db":
        collections = await db.list_collection_names()
        db_stats = await db.command("dbstats")
        size_mb = db_stats.get("dataSize", 0) / (1024 * 1024)

        col_text = ""
        for c in collections:
            cnt = await db[c].count_documents({})
            col_text += f" - {c}: <code>{cnt}</code>\n"

<<<<<<< HEAD
        text = (
            f"🗄️ <b>Database Statistics</b>\n\nTotal Data Size: <code>{size_mb:.2f} MB</code>\nCollections:\n{col_text}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]]
        )
=======
        text = (f"🗄️ <b>Database Statistics</b>\n\n"
                f"Total Data Size: <code>{size_mb:.2f} MB</code>\n"
                f"Collections:\n{col_text}")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if action == "dash_probs":
<<<<<<< HEAD
        text = (
            "⚠️ <b>Problematic Data Sources</b>\n\n"
            "<i>TODO: Tracking for specific sources (e.g. failed exchange endpoints) to be implemented in DB.</i>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]]
        )
=======
        text = ("⚠️ <b>Problematic Data Sources</b>\n\n"
                "<i>TODO: Tracking for specific sources (e.g. failed exchange endpoints) to be implemented in DB.</i>")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("back"), callback_data="admin_dashboard")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
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
<<<<<<< HEAD

=======
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
            # need to mutate nested dataclass properly.
            new_parser = dataclasses.replace(cfg.parser, auto_update=not cfg.parser.auto_update)
            cfg = dataclasses.replace(cfg, parser=new_parser)
            save_settings(cfg)
            await call.answer()

        parser_status = t("parser_toggle_on") if cfg.parser.auto_update else t("parser_toggle_off")

<<<<<<< HEAD
        text = (
            f"{t('config_title')}\n\n"
            f"Auto update: {'✅' if cfg.parser.auto_update else '❌'}\n"
            f"Interval: {cfg.parser.update_interval_sec}s\n"
            f"Critical: {len(cfg.parser.critical_currencies)}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=parser_status, callback_data="admin_toggle_parser")],
                [
                    InlineKeyboardButton(
                        text=t("parser_change_interval"),
                        callback_data="admin_change_interval",
                    )
                ],
                [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
            ]
        )
=======
        text = (f"{t('config_title')}\n\n"
                f"Auto update: {'✅' if cfg.parser.auto_update else '❌'}\n"
                f"Interval: {cfg.parser.update_interval_sec}s\n"
                f"Critical: {len(cfg.parser.critical_currencies)}")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=parser_status, callback_data="admin_toggle_parser")],
            [InlineKeyboardButton(text=t("parser_change_interval"), callback_data="admin_change_interval")],
            [InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
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
<<<<<<< HEAD
        err_text = t("diagnostics_recent_errors") + (recent_errs if recent_errs else t("error_none"))

        elapsed_ms = int((time.time() - callback_start_time) * 1000)
        time_text = t("diagnostics_response_time").format(ms=elapsed_ms)

        text = f"{t('diagnostics_title')}\n\n{res_text}\n{err_text}\n\n{time_text}"

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
=======
        err_text = t('diagnostics_recent_errors') + (recent_errs if recent_errs else t('error_none'))

        elapsed_ms = int((time.time() - callback_start_time) * 1000)
        time_text = t('diagnostics_response_time').format(ms=elapsed_ms)

        text = f"{t('diagnostics_title')}\n\n{res_text}\n{err_text}\n\n{time_text}"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if action == "broadcast":
        await call.answer()
        await call.message.answer(t("broadcast_prompt"), parse_mode="HTML")
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

<<<<<<< HEAD
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
            [
                InlineKeyboardButton(
                    text=t("parser_change_interval"),
                    callback_data="admin_change_interval",
                )
            ],
            [InlineKeyboardButton(text=t("back"), callback_data="admin_back")],
        ]
    )
=======
    text = (f"{t('config_title')}\n\n"
            f"Auto update: {'✅' if cfg.parser.auto_update else '❌'}\n"
            f"Interval: {cfg.parser.update_interval_sec}s\n"
            f"Critical: {len(cfg.parser.critical_currencies)}")

    parser_status = t("parser_toggle_on") if cfg.parser.auto_update else t("parser_toggle_off")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=parser_status, callback_data="admin_toggle_parser")],
        [InlineKeyboardButton(text=t("parser_change_interval"), callback_data="admin_change_interval")],
        [InlineKeyboardButton(text=t("back"), callback_data="admin_back")]])
>>>>>>> 6233cd8c1c0c25e0cc1ce26e6f7b0051542ecf79

    await message.answer(text, reply_markup=kb, parse_mode="HTML")
