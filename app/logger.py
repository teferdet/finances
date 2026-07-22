"""
Structured logging setup — console + file + error file with rotation.

Usage:
    from app.logger import setup_logging, get_logger
    setup_logging()
    log = get_logger("handlers.start")
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import LOGS_DIR


_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with console + file handlers."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # ── Console handler ─────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    if sys.stdout.encoding.lower() != "utf-8":
        console.stream = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    console.setLevel(level)
    console.setFormatter(formatter)

    # ── File handler (all messages) ─────────────────────────────────
    all_file = RotatingFileHandler(
        LOGS_DIR / "bot.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    all_file.setLevel(logging.DEBUG)
    all_file.setFormatter(formatter)

    # ── Error file handler ──────────────────────────────────────────
    error_file = RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(formatter)

    # ── Root logger ─────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(all_file)
    root.addHandler(error_file)

    # Silence noisy libraries
    for name in ("httpx", "httpcore", "aiogram.event", "motor", "pymongo"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger under 'app' namespace."""
    return logging.getLogger(f"app.{name}")

def get_d_admin_logger() -> logging.Logger:
    """Get logger specifically for dynamic admin actions in the debug menu."""
    logger = logging.getLogger("d_admin")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            LOGS_DIR / "d_admin.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fmt = "%(asctime)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
    return logger

class AsyncTelegramErrorHandler(logging.Handler):
    """
    Custom handler that sends log messages (ERROR/WARNING/CRITICAL)
    to Telegram groups configured to receive them.
    """
    def __init__(self, bot, db):
        super().__init__()
        self.bot = bot
        self.db = db
        self.last_sent = {}  # dict[chat_id, float] for debouncing

    def emit(self, record: logging.LogRecord):
        # We handle min_level dynamically from the DB, but we only intercept ERROR, WARNING, CRITICAL anyway
        if record.levelno < logging.WARNING:
            return

        import asyncio
        import time
        from datetime import datetime

        # Format message variables
        dt_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        level_name = record.levelname
        emoji = "🔴" if level_name in ("ERROR", "CRITICAL") else "🟠"

        # Exception details
        exc_text = ""
        if record.exc_info:
            import traceback
            tb_lines = traceback.format_exception(*record.exc_info)
            # Take last 3 lines (excluding the very last empty string if present)
            tb_short = "".join(tb_lines[-4:]) if len(tb_lines) >= 4 else "".join(tb_lines)
            exc_text = tb_short

        asyncio.create_task(self._send_to_groups(
            record.levelno, level_name, emoji, dt_str,
            record.pathname, record.lineno, record.getMessage(),
            exc_text, time.time()
        ))

    async def _send_to_groups(self, levelno: int, level_name: str, emoji: str, dt_str: str, pathname: str, lineno: int, message: str, exc_text: str, current_time: float):
        from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
        from app.repositories.groups import get_active_groups, toggle_group_active
        from app.i18n import get_i18n
        from app.config import get_settings

        try:
            settings = get_settings()
            lang = settings.i18n.default_language
            i18n = get_i18n()

            traceback_part = ""
            if exc_text:
                traceback_part = str(i18n.get("admin.groups.traceback_label", lang)).format(tb=exc_text)

            text = str(i18n.get("admin.groups.error_report", lang)).format(
                emoji=emoji,
                level=level_name,
                date=dt_str,
                path=pathname,
                line=lineno,
                message=message,
                traceback=traceback_part
            )

            groups = await get_active_groups()
            for group in groups:
                chat_id = group.get("chat_id")
                notifs = group.get("notifications", {}).get("errors", {})
                if not notifs.get("enabled"):
                    continue

                # Check min level
                min_level_str = notifs.get("min_level", "ERROR")
                min_level = getattr(logging, min_level_str.upper(), logging.ERROR)

                if levelno < min_level:
                    continue

                # Debounce (1 per 10s per group)
                if current_time - self.last_sent.get(chat_id, 0) < 10:
                    continue

                self.last_sent[chat_id] = current_time

                try:
                    await self.bot.send_message(chat_id, text, parse_mode="HTML")
                except TelegramForbiddenError:
                    await toggle_group_active(chat_id, False)
                except TelegramBadRequest as e:
                    if "chat not found" in str(e).lower() or "bot was kicked" in str(e).lower():
                        await toggle_group_active(chat_id, False)
                except Exception:
                    pass
        except Exception:
            pass

