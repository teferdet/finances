"""
Service for sending periodic analytical reports to subscribed groups.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from app.db import get_db
from app.logger import get_logger
from app.repositories.groups import get_active_groups, toggle_group_active
from app.services.ephemeral_service import send_ephemeral
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from app.config import get_settings
from app.i18n import get_i18n

log = get_logger("analytics")

class AnalyticsReporter:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def start(self):
        """Starts the background loop to check and send reports."""
        log.info("AnalyticsReporter started")
        while True:
            try:
                now = datetime.utcnow()
                current_time_str = now.strftime("%H:%M")

                groups = await get_active_groups()
                for group in groups:
                    chat_id = group.get("chat_id")
                    analytics = group.get("notifications", {}).get("analytics", {})

                    if not analytics.get("enabled"):
                        continue

                    schedule = analytics.get("schedule", "daily")
                    send_time = analytics.get("send_time", "09:00")
                    use_ephemeral = analytics.get("ephemeral", False)
                    # admin_user_id is the person to whom ephemeral reports are sent
                    admin_user_id = group.get("added_by_admin_id")

                    if current_time_str == send_time:
                        if schedule == "daily":
                            await self._send_daily_report(
                                chat_id, now, use_ephemeral, admin_user_id
                            )
                        elif schedule == "weekly" and now.weekday() == 0:  # Monday
                            await self._send_weekly_report(
                                chat_id, now, use_ephemeral, admin_user_id
                            )

                # Sleep until next minute
                await asyncio.sleep(60 - datetime.utcnow().second)
            except asyncio.CancelledError:
                log.info("AnalyticsReporter stopped")
                break
            except Exception as e:
                log.error("Error in AnalyticsReporter loop: %s", e)
                await asyncio.sleep(60)

    async def _send_daily_report(
        self,
        chat_id: int,
        now: datetime,
        use_ephemeral: bool = False,
        admin_user_id: int | None = None,
    ):
        settings = get_settings()
        lang = settings.i18n.default_language
        i18n = get_i18n()
        stats = await self._collect_daily_stats(now, i18n, lang)
        text = str(i18n.get("admin.groups.analytics_report_daily", lang)).format(
            date=now.strftime('%d %b %Y'),
            active_today=stats['active_today'],
            new_today=stats['new_today'],
            total_users=stats['total_users'],
            requests_today=stats['requests_today'],
            peak_hour=stats['peak_hour'],
            top_currencies=stats['top_currencies'],
            errors_today=stats['errors_today']
        )
        await self._send_message(chat_id, text, use_ephemeral, admin_user_id)

    async def _send_weekly_report(
        self,
        chat_id: int,
        now: datetime,
        use_ephemeral: bool = False,
        admin_user_id: int | None = None,
    ):
        settings = get_settings()
        lang = settings.i18n.default_language
        i18n = get_i18n()
        stats = await self._collect_weekly_stats(now, i18n, lang)
        start_date = (now - timedelta(days=7)).strftime('%d')
        end_date = (now - timedelta(days=1)).strftime('%d %b %Y')
        text = str(i18n.get("admin.groups.analytics_report_weekly", lang)).format(
            date=f"{start_date}–{end_date}",
            active_weekly=stats['active_weekly'],
            new_weekly=stats['new_weekly'],
            retention=stats['retention'],
            requests_weekly=stats['requests_weekly'],
            peak_day=stats['peak_day'],
            top_currencies=stats['top_currencies'],
            errors_weekly=stats['errors_weekly']
        )
        await self._send_message(chat_id, text, use_ephemeral, admin_user_id)

    async def _send_message(
        self,
        chat_id: int,
        text: str,
        use_ephemeral: bool = False,
        admin_user_id: int | None = None,
    ):
        """
        Send analytics to a group.
        If use_ephemeral=True and admin_user_id is set, sends as an ephemeral
        message visible only to that admin (Bot API 10.2).
        Falls back to regular send on failure or missing user_id.
        """
        # ── Ephemeral path ─────────────────────────────────────────────
        if use_ephemeral and admin_user_id:
            eph_id = await send_ephemeral(self.bot, chat_id, admin_user_id, text)
            if eph_id is not None:
                log.info(
                    "Ephemeral analytics sent to user %d in chat %d (eph_id=%d)",
                    admin_user_id, chat_id, eph_id,
                )
                return
            log.warning(
                "Ephemeral analytics failed for chat %d user %d — falling back to public",
                chat_id, admin_user_id,
            )
        # ── Standard public send ───────────────────────────────────────────
        try:
            await self.bot.send_message(chat_id, text, parse_mode="HTML")
        except TelegramForbiddenError:
            await toggle_group_active(chat_id, False)
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower() or "bot was kicked" in str(e).lower():
                await toggle_group_active(chat_id, False)
        except Exception as e:
            log.warning("Failed to send analytics report to %s: %s", chat_id, e)

    async def _collect_daily_stats(self, now: datetime, i18n, lang: str) -> dict:
        total_users = await self.db["Users"].count_documents({})
        
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        active_today = await self.db["Users"].count_documents({"last_active": {"$gte": today_midnight}})
        
        # New today (assuming 'created_at' or 'joined_at', but we use 'last_active' logic since there might not be created_at. Wait, let's use '_id' logic or assume 'created_at' doesn't exist and we just use TODO)
        new_today = 0 # TODO: require field in schema for new users
        
        no_data_str = str(i18n.get("admin.groups.no_data", lang))
        
        # Requests and currencies (Requires request_stats)
        requests_today = 0 # TODO: requires request_stats collection
        peak_hour = "Unknown" # TODO: requires request_stats collection
        top_currencies = no_data_str # TODO: requires request_stats collection
        
        # Errors (parsing logs)
        errors_today = 0
        from app.config import LOGS_DIR
        error_log_path = LOGS_DIR / "errors.log"
        if error_log_path.exists():
            today_str = now.strftime("%Y-%m-%d")
            try:
                with open(error_log_path, "r", encoding="utf-8") as f:
                    errors_today = sum(1 for line in f if line.startswith(today_str))
            except Exception:
                pass

        return {
            "total_users": f"{total_users:,}",
            "active_today": f"{active_today:,}",
            "new_today": f"{new_today:,}",
            "requests_today": f"{requests_today:,}",
            "peak_hour": peak_hour,
            "top_currencies": top_currencies,
            "errors_today": f"{errors_today:,}"
        }

    async def _collect_weekly_stats(self, now: datetime, i18n, lang: str) -> dict:
        weekly_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
        active_weekly = await self.db["Users"].count_documents({"last_active": {"$gte": weekly_midnight}})
        
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        active_today = await self.db["Users"].count_documents({"last_active": {"$gte": today_midnight}})
        
        retention = round((active_today / active_weekly * 100), 1) if active_weekly > 0 else 0
        
        no_data_str = str(i18n.get("admin.groups.no_data", lang))
        
        new_weekly = 0 # TODO: require field in schema for new users
        requests_weekly = 0 # TODO: requires request_stats collection
        peak_day = "Unknown" # TODO: requires request_stats collection
        top_currencies = no_data_str # TODO: requires request_stats collection
        
        # Errors (parsing logs)
        errors_weekly = 0
        from app.config import LOGS_DIR
        error_log_path = LOGS_DIR / "errors.log"
        if error_log_path.exists():
            dates = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
            try:
                with open(error_log_path, "r", encoding="utf-8") as f:
                    errors_weekly = sum(1 for line in f if line[:10] in dates)
            except Exception:
                pass

        return {
            "active_weekly": f"{active_weekly:,}",
            "new_weekly": f"{new_weekly:,}",
            "retention": retention,
            "requests_weekly": f"{requests_weekly:,}",
            "peak_day": peak_day,
            "top_currencies": top_currencies,
            "errors_weekly": f"{errors_weekly:,}"
        }
