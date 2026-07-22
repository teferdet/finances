"""
Entry point — ``python -m app``

Lifecycle:
0. Dependency check (exits early if packages are missing)
1. Setup logging
2. Load config
3. Connect to MongoDB, ensure indexes
4. Start parser background task
5. Start alert checker + volatility monitor + digest scheduler
6. Start aiogram polling
7. On shutdown: cancel all tasks, close DB
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from pathlib import Path

# ── Dependency check (must run before any project imports) ─────────────────────
# Maps distribution package name → importable module name (when they differ)
_IMPORT_NAME: dict[str, str] = {
    "aiogram": "aiogram",
    "motor": "motor",
    "curl_cffi": "curl_cffi",
    "aiohttp": "aiohttp",
    "beautifulsoup4": "bs4",
    "yfinance": "yfinance",
    "pandas": "pandas",
    "psutil": "psutil",
    "pymongo": "pymongo",
    "python-dotenv": "dotenv",
    "colorama": "colorama",
    "requests": "requests",
    "cryptography": "cryptography",
    "bson": "bson",
}


def _check_dependencies() -> None:
    """Check that all required packages are importable. Exit with a helpful
    error message if any are missing."""
    # Read the package names listed in requirements.txt
    req_path = Path(__file__).resolve().parent.parent / "requirements.txt"
    required: list[str] = []
    if req_path.exists():
        for raw_line in req_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Strip version specifiers (>=, ==, <=, ~=, !=)
            pkg_name = line.split(">")[0].split("<")[0].split("=")[0].split("~")[0].split("!")[0].strip()
            if pkg_name:
                required.append(pkg_name)
    else:
        # Fallback: use the hard-coded map keys
        required = list(_IMPORT_NAME.keys())

    missing: list[str] = []
    for pkg in required:
        module = _IMPORT_NAME.get(pkg, pkg.replace("-", "_"))
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(pkg)

    if missing:
        sep = "=" * 60
        pkgs = " ".join(missing)
        print(f"\n{sep}")
        print("  STARTUP ERROR — missing Python packages")
        print(sep)
        print(f"\n  The following package(s) are not installed:\n")
        for m in missing:
            print(f"    ✗  {m}")
        print(f"\n  Install them by running:")
        print(f"\n    pip install {pkgs}")
        print(f"\n  Or install all dependencies at once:")
        print(f"\n    pip install -r requirements.txt")
        print(f"\n{sep}\n")
        sys.exit(1)


_check_dependencies()
# ──────────────────────────────────────────────────────────────────────────────
from app.logger import setup_logging, get_logger, AsyncTelegramErrorHandler
from app.config import get_settings
from app.db import get_db, ensure_indexes, close_db
from app.bot import create_bot, create_dispatcher
from app.services.parser_service import run_parser_loop
from app.services.alert_service import (
    run_alert_checker,
    run_volatility_monitor,
    set_bot as set_alert_bot,
)
from app.services.digest_service import run_digest_scheduler
from app.services.backup import run_daily_backup_loop
from app.services.analytics_reporter import AnalyticsReporter

log = get_logger("main")


async def on_startup(bot) -> None:
    """Called after dispatcher starts polling."""
    settings = get_settings()
    log.info("=" * 60)
    log.info("finances bot v%s starting", settings.bot.version)
    log.info("=" * 60)

    # Check for restart state
    from app.config import CONFIG_DIR
    import json

    state_path = CONFIG_DIR / ".restart_state.json"
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            chat_id = data.get("chat_id")
            message_id = data.get("message_id")

            from app.i18n import get_i18n
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            i18n = get_i18n()
            lang = settings.i18n.default_language

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=str(i18n.get("admin.main_menu", lang)), callback_data="admin_back")]
                ]
            )
            text = str(i18n.get("admin.restart_success", lang))

            try:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
                )
            except Exception as e:
                log.warning("Could not edit restart message: %s", e)

            state_path.unlink()
        except Exception as e:
            log.warning("Error handling restart state: %s", e)

    # Ensure DB indexes
    await ensure_indexes()

    # Load dynamic admins
    try:
        from app.state import dynamic_admin_ids
        db = get_db()
        doc = await db["Settings"].find_one({"_id": "dynamic_admins"})
        if doc and "admin_ids" in doc:
            dynamic_admin_ids.update(doc["admin_ids"])
            log.info("Loaded %d dynamic admins", len(dynamic_admin_ids))
    except Exception as e:
        log.error("Failed to load dynamic admins: %s", e)

    # Set bot commands
    try:
        from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators
        from app.i18n import get_i18n

        i18n = get_i18n()
        for lang in i18n.supported:
            commands_list = [
                BotCommand(command="start", description=i18n.get("commands.start", lang)),
                BotCommand(command="crypto", description=i18n.get("commands.crypto", lang)),
                BotCommand(command="stocks", description=i18n.get("commands.stocks", lang)),
                BotCommand(
                    command="portfolio",
                    description=i18n.get("commands.portfolio", lang),
                ),
                BotCommand(command="export", description=i18n.get("commands.export", lang)),
                BotCommand(command="import", description=i18n.get("commands.import", lang)),
                BotCommand(command="alert", description=i18n.get("commands.alert", lang)),
                BotCommand(command="donate", description=i18n.get("commands.donate", lang)),
                BotCommand(command="settings", description=i18n.get("commands.settings", lang)),
                BotCommand(command="privacy", description=i18n.get("commands.privacy", lang)),
                BotCommand(command="help", description=i18n.get("commands.help", lang)),
            ]
            await bot.set_my_commands(commands_list, language_code=lang)

        # Default fallback
        commands_list_default = [
            BotCommand(command="start", description=i18n.get("commands.start", "en")),
            BotCommand(command="crypto", description=i18n.get("commands.crypto", "en")),
            BotCommand(command="stocks", description=i18n.get("commands.stocks", "en")),
            BotCommand(command="portfolio", description=i18n.get("commands.portfolio", "en")),
            BotCommand(command="export", description=i18n.get("commands.export", "en")),
            BotCommand(command="import", description=i18n.get("commands.import", "en")),
            BotCommand(command="alert", description=i18n.get("commands.alert", "en")),
            BotCommand(command="donate", description=i18n.get("commands.donate", "en")),
            BotCommand(command="settings", description=i18n.get("commands.settings", "en")),
            BotCommand(command="privacy", description=i18n.get("commands.privacy", "en")),
            BotCommand(command="help", description=i18n.get("commands.help", "en")),
        ]
        await bot.set_my_commands(commands_list_default)

        # Group chats commands (for all group members)
        group_member_commands = [
            BotCommand(command="rate", description="Convert currency (e.g. /rate 100 USD)"),
            BotCommand(command="crypto", description="View cryptocurrency rates"),
            BotCommand(command="stocks", description="View stock prices"),
            BotCommand(command="help", description="Show bot help"),
        ]
        await bot.set_my_commands(group_member_commands, scope=BotCommandScopeAllGroupChats())

        # Group admin commands (visible only to chat administrators across all groups)
        group_admin_commands = [
            BotCommand(command="group_settings", description="Group bot settings"),
            BotCommand(command="group_stats", description="Group usage statistics"),
            BotCommand(command="rate", description="Convert currency (e.g. /rate 100 USD)"),
        ]
        await bot.set_my_commands(group_admin_commands, scope=BotCommandScopeAllChatAdministrators())

        log.info("Bot commands and scopes set successfully")
    except Exception as exc:
        log.warning("Failed to set bot commands: %s", exc)


async def main() -> None:
    setup_logging(logging.INFO)

    # Validate config loads
    try:
        settings = get_settings()
        log.info("Config loaded. DB: %s", settings.database.mongo_database)
    except Exception as exc:
        log.critical("Failed to load config: %s", exc)
        sys.exit(1)

    # Initialize DB
    get_db()

    bot = create_bot()
    dp = create_dispatcher()

    # Setup Telegram error handler
    telegram_error_handler = AsyncTelegramErrorHandler(bot=bot, db=get_db())
    logging.getLogger().addHandler(telegram_error_handler)

    # Set bot reference for alert/volatility notifications
    set_alert_bot(bot)

    # Start background tasks
    background_tasks = []

    parser_task = asyncio.create_task(run_parser_loop())
    background_tasks.append(("parser", parser_task))

    alert_task = asyncio.create_task(run_alert_checker(check_interval=60))
    background_tasks.append(("alert_checker", alert_task))

    volatility_task = asyncio.create_task(run_volatility_monitor(check_interval=300))
    background_tasks.append(("volatility_monitor", volatility_task))

    digest_task = asyncio.create_task(run_digest_scheduler())
    background_tasks.append(("digest_scheduler", digest_task))
    
    analytics_reporter = AnalyticsReporter(bot=bot, db=get_db())
    analytics_task = asyncio.create_task(analytics_reporter.start())
    background_tasks.append(("analytics_reporter", analytics_task))

    if settings.bot.backup_enabled:
        backup_task = asyncio.create_task(run_daily_backup_loop(settings.database.mongo_uri))
        background_tasks.append(("backup_scheduler", backup_task))
        
    import sys
    if "--debug" in sys.argv or "debug" in sys.argv:
        from app.debug_cli import run_debug_cli
        debug_cli_task = asyncio.create_task(run_debug_cli())
        background_tasks.append(("debug_cli", debug_cli_task))

    log.info("Started %d background tasks", len(background_tasks))

    # Register startup hook
    dp.startup.register(on_startup)

    try:
        log.info("Starting polling…")
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutdown signal received")
    finally:
        # Cleanup all background tasks
        for name, task in background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            log.info("Background task '%s' stopped", name)

        await close_db()
        await bot.session.close()
        log.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
