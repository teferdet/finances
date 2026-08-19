"""
Structured logging setup — console + rotating files by date.

Log files:
  logs/bot.log    — INFO+ from app.* only (daily rotation, 30 days)
  logs/debug.log  — DEBUG+ everything from app.* (daily rotation, 7 days)
  logs/errors.log — ERROR/CRITICAL from all sources (size rotation, 7×5MB)

Usage:
    from app.logger import setup_logging, get_logger
    setup_logging()
    log = get_logger("handlers.start")
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from app.config import LOGS_DIR


_CONFIGURED = False

# ── Noisy third-party loggers to silence (WARNING+) ────────────────────────
_SILENT_LIBS: tuple[str, ...] = (
    "httpx",
    "httpcore",
    "aiogram.event",
    "aiogram.dispatcher",
    "motor",
    "pymongo",
    "peewee",       # SQL query DEBUG spam
    "urllib3",
    "asyncio",
)

# ── Parser loggers that are too chatty at INFO level ───────────────────────
_PARSER_INFO_SPAM: tuple[str, ...] = (
    "app.parser.fiat",   # "Fetching rates for XXX..." per currency per cycle
)


class _AppOnlyFilter(logging.Filter):
    """Pass only records from the 'app.*' namespace."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("app.")


def _make_timed_handler(
    filename: str,
    level: int,
    *,
    backup_days: int = 30,
    app_only: bool = False,
) -> TimedRotatingFileHandler:
    """Create a daily-rotating file handler.

    Rotates at midnight; keeps *backup_days* old files.
    Archived files are named  ``<filename>.YYYY-MM-DD``.
    """
    handler = TimedRotatingFileHandler(
        LOGS_DIR / filename,
        when="midnight",
        interval=1,
        backupCount=backup_days,
        encoding="utf-8",
        utc=False,
    )
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(level)
    if app_only:
        handler.addFilter(_AppOnlyFilter())
    return handler


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with console + three file handlers."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # ── Console handler (INFO+, all sources) ────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            console.stream = open(
                sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1
            )
    except Exception:
        pass
    console.setLevel(level)
    console.setFormatter(formatter)

    # ── Root logger ─────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)

    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # ── bot.log — INFO+ from app.* only, daily rotation, 30 days ───────────
        bot_file = _make_timed_handler("bot.log", logging.INFO, backup_days=30, app_only=True)
        bot_file.setFormatter(formatter)
        root.addHandler(bot_file)

        # ── debug.log — DEBUG+ from app.* only, daily rotation, 7 days ─────────
        debug_file = _make_timed_handler("debug.log", logging.DEBUG, backup_days=7, app_only=True)
        debug_file.setFormatter(formatter)
        root.addHandler(debug_file)

        # ── errors.log — ERROR/CRITICAL from all sources, size rotation ─────────
        error_file = RotatingFileHandler(
            LOGS_DIR / "errors.log",
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=7,               # keep 7 backups → up to 40 MB
            encoding="utf-8",
        )
        error_file.setLevel(logging.ERROR)
        error_file.setFormatter(formatter)
        root.addHandler(error_file)

        # ── Session separator in log files ──────────────────────────────────────
        sep = "=" * 72
        startup_record = logging.LogRecord(
            name="app.main",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"{sep}\n  BOT SESSION STARTED\n{sep}",
            args=(),
            exc_info=None,
        )
        bot_file.emit(startup_record)
        debug_file.emit(startup_record)
    except (PermissionError, OSError) as exc:
        sys.stderr.write(f"⚠️  Warning: File logging unavailable in {LOGS_DIR} ({exc}). Using console logging only.\n")

    # ── Silence noisy third-party libraries ─────────────────────────────────
    for name in _SILENT_LIBS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # ── Reduce parser INFO spam to WARNING ──────────────────────────────────
    # Individual "Fetching rates for XXX..." lines go to WARNING+;
    # cycle summaries (INFO) still appear in debug.log.
    for name in _PARSER_INFO_SPAM:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger under the 'app' namespace."""
    return logging.getLogger(f"app.{name}")


def get_d_admin_logger() -> logging.Logger:
    """Get logger specifically for dynamic admin actions in the debug menu."""
    logger = logging.getLogger("d_admin")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        try:
            handler = RotatingFileHandler(
                LOGS_DIR / "d_admin.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fmt = "%(asctime)s | %(message)s"
            handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)
        except (PermissionError, OSError) as exc:
            sys.stderr.write(f"⚠️  Warning: d_admin logger unavailable ({exc})\n")
    return logger


class AsyncTelegramErrorHandler(logging.Handler):
    """
    Custom handler that sends log messages (WARNING/ERROR/CRITICAL)
    to Telegram groups configured to receive them.
    """

    def __init__(self, bot, db):
        super().__init__()
        self.bot = bot
        self.db = db
        self.last_sent: dict[int, float] = {}  # chat_id → timestamp (debounce)
        self._tasks = set()

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.WARNING:
            return

        import asyncio
        import time
        from datetime import datetime

        dt_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        level_name = record.levelname
        emoji = "🔴" if level_name in ("ERROR", "CRITICAL") else "🟠"

        exc_text = ""
        if record.exc_info:
            import traceback

            tb_lines = traceback.format_exception(*record.exc_info)
            tb_short = "".join(tb_lines[-4:]) if len(tb_lines) >= 4 else "".join(tb_lines)
            exc_text = tb_short

        task = asyncio.create_task(
            self._send_to_groups(
                record.levelno,
                level_name,
                emoji,
                dt_str,
                record.pathname,
                record.lineno,
                record.getMessage(),
                exc_text,
                time.time(),
            )
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _send_to_groups(
        self,
        levelno: int,
        level_name: str,
        emoji: str,
        dt_str: str,
        pathname: str,
        lineno: int,
        message: str,
        exc_text: str,
        current_time: float,
    ) -> None:
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
                traceback_part = str(i18n.get("admin.groups.traceback_label", lang)).format(
                    tb=exc_text
                )

            text = str(i18n.get("admin.groups.error_report", lang)).format(
                emoji=emoji,
                level=level_name,
                date=dt_str,
                path=pathname,
                line=lineno,
                message=message,
                traceback=traceback_part,
            )

            groups = await get_active_groups()
            for group in groups:
                chat_id = group.get("chat_id")
                notifs = group.get("notifications", {}).get("errors", {})
                if not notifs.get("enabled"):
                    continue

                min_level_str = notifs.get("min_level", "ERROR")
                min_level = getattr(logging, min_level_str.upper(), logging.ERROR)
                if levelno < min_level:
                    continue

                # Debounce: max 1 message per 10 s per group
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
