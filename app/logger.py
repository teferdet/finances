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
        logger.propagate = False
    return logger
