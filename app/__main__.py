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
import os
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
        print("\n  The following package(s) are not installed:\n")
        for m in missing:
            print(f"    ✗  {m}")
        print("\n  Install them by running:")
        print(f"\n    pip install {pkgs}")
        print("\n  Or install all dependencies at once:")
        print("\n    pip install -r requirements.txt")
        print(f"\n{sep}\n")
        sys.exit(1)


_check_dependencies()
# ──────────────────────────────────────────────────────────────────────────────
from app.logger import setup_logging, get_logger, AsyncTelegramErrorHandler
from app.config import get_settings
from app.db import get_db, ensure_indexes, close_db
from app.redis_client import init_redis, close_redis
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

    # Ensure DB indexes
    await ensure_indexes()

    # Pre-warm CQRS PriceSnapshot read model
    try:
        from app.cqrs.read.prices import price_store

        await price_store.reload()
        log.info("CQRS PriceSnapshot read model pre-warmed")
    except Exception as e:
        log.warning("Failed to pre-warm PriceSnapshot: %s", e)

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
                BotCommand(command="portfolio", description=i18n.get("commands.portfolio", lang)),
                BotCommand(command="calc", description=i18n.get("commands.calc", lang)),
                BotCommand(command="crypto", description=i18n.get("commands.crypto", lang)),
                BotCommand(command="stocks", description=i18n.get("commands.stocks", lang)),
                BotCommand(command="alert", description=i18n.get("commands.alert", lang)),
                BotCommand(command="my_data", description=i18n.get("commands.my_data", lang)),
                BotCommand(command="settings", description=i18n.get("commands.settings", lang)),
                BotCommand(command="export", description=i18n.get("commands.export", lang)),
                BotCommand(command="import", description=i18n.get("commands.import", lang)),
                BotCommand(command="donate", description=i18n.get("commands.donate", lang)),
                BotCommand(command="privacy", description=i18n.get("commands.privacy", lang)),
                BotCommand(command="help", description=i18n.get("commands.help", lang)),
            ]
            await bot.set_my_commands(commands_list, language_code=lang)

        # Default fallback
        commands_list_default = [
            BotCommand(command="start", description=i18n.get("commands.start", "en")),
            BotCommand(command="portfolio", description=i18n.get("commands.portfolio", "en")),
            BotCommand(command="calc", description=i18n.get("commands.calc", "en")),
            BotCommand(command="crypto", description=i18n.get("commands.crypto", "en")),
            BotCommand(command="stocks", description=i18n.get("commands.stocks", "en")),
            BotCommand(command="alert", description=i18n.get("commands.alert", "en")),
            BotCommand(command="my_data", description=i18n.get("commands.my_data", "en")),
            BotCommand(command="settings", description=i18n.get("commands.settings", "en")),
            BotCommand(command="export", description=i18n.get("commands.export", "en")),
            BotCommand(command="import", description=i18n.get("commands.import", "en")),
            BotCommand(command="donate", description=i18n.get("commands.donate", "en")),
            BotCommand(command="privacy", description=i18n.get("commands.privacy", "en")),
            BotCommand(command="help", description=i18n.get("commands.help", "en")),
        ]
        await bot.set_my_commands(commands_list_default)

        # Group chats commands (only if groups feature is enabled)
        if settings.features.groups_enabled:
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

    # ── Sentry initialization ──────────────────────────────────────────────────
    if settings.sentry.dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry.dsn,
                environment=settings.sentry.environment,
                traces_sample_rate=settings.sentry.traces_sample_rate,
                profiles_sample_rate=settings.sentry.profiles_sample_rate,
                send_default_pii=settings.sentry.send_default_pii,
            )
            log.info("Sentry initialized (env=%s)", settings.sentry.environment)
        except Exception as exc:
            log.warning("Failed to initialize Sentry: %s", exc)
    else:
        log.info("Sentry disabled (settings.sentry.dsn is empty)")

    # Initialize DB
    get_db()

    # ── Redis initialization (optional, fallback to MemoryCache) ───────────────
    await init_redis()

    bot = create_bot()
    dp = create_dispatcher()

    # Setup Telegram error handler
    telegram_error_handler = AsyncTelegramErrorHandler(bot=bot, db=get_db())
    logging.getLogger().addHandler(telegram_error_handler)

    # Set bot reference for alert/volatility notifications
    set_alert_bot(bot)

    # ── Task Supervisor & Write-Behind Activity Flusher ───────────────────────
    from app.cqrs.tasks import supervisor
    from app.cqrs.write.activity import activity_buffer

    supervisor.register("parser", run_parser_loop)
    supervisor.register("alert_checker", lambda: run_alert_checker(check_interval=60))
    supervisor.register("volatility_monitor", lambda: run_volatility_monitor(check_interval=300))
    supervisor.register("digest_scheduler", run_digest_scheduler)

    analytics_reporter = AnalyticsReporter(bot=bot, db=get_db())
    supervisor.register("analytics_reporter", analytics_reporter.start)

    if settings.bot.backup_enabled:
        supervisor.register("backup_scheduler", lambda: run_daily_backup_loop(settings.database.mongo_uri))

    from app.cache import run_cache_cleanup_loop
    supervisor.register("cache_cleanup", run_cache_cleanup_loop)

    # Activity write-behind buffer flusher (flushes memory updates every 5s)
    supervisor.register("activity_flusher", activity_buffer.run_flusher_loop)

    # M-3 fix: require both --debug flag AND APP_DEBUG_CLI=true env var.
    if "--debug" in sys.argv and os.environ.get("APP_DEBUG_CLI", "").lower() == "true":
        from app.debug_cli import run_debug_cli
        supervisor.register("debug_cli", run_debug_cli)

    supervisor.start_all()
    log.info("Supervisor started all background workers")

    # Register startup hook
    dp.startup.register(on_startup)

    try:
        log.info("Starting polling…")
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutdown signal received")
    finally:
        log.info("Initiating graceful shutdown...")
        await supervisor.stop_all()

        # Final flush of write-behind activity buffer
        try:
            flushed = await activity_buffer.flush()
            log.info("Final activity flush completed (%d records written)", flushed)
        except Exception as exc:
            log.warning("Final activity flush warning: %s", exc)

        await close_db()
        await close_redis()
        await bot.session.close()
        log.info("Shutdown complete")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
