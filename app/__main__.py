"""
Entry point — ``python -m app``

Lifecycle:
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
import logging
import signal
import sys
import os
from app.logger import setup_logging, get_logger
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
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=str(i18n.get("admin.main_menu", lang)), callback_data="admin_back")]
            ])
            text = str(i18n.get("admin.restart_success", lang))
            
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                log.warning("Could not edit restart message: %s", e)
                
            state_path.unlink()
        except Exception as e:
            log.warning("Error handling restart state: %s", e)

    # Ensure DB indexes
    await ensure_indexes()

    # Set bot commands
    try:
        from aiogram.types import BotCommand
        from app.i18n import get_i18n
        i18n = get_i18n()
        for lang in i18n.supported:
            commands_list = [
                BotCommand(command="start", description=i18n.get("commands.start", lang)),
                BotCommand(command="crypto", description=i18n.get("commands.crypto", lang)),
                BotCommand(command="stocks", description=i18n.get("commands.stocks", lang)),
                BotCommand(command="portfolio", description=i18n.get("commands.portfolio", lang)),
                BotCommand(command="export", description=i18n.get("commands.export", lang)),
                BotCommand(command="import", description=i18n.get("commands.import", lang)),
                BotCommand(command="alert", description=i18n.get("commands.alert", lang)),
                BotCommand(command="donate", description=i18n.get("commands.donate", lang)),
                BotCommand(command="settings", description=i18n.get("commands.settings", lang)),
                BotCommand(command="privacy", description=i18n.get("commands.privacy", lang)),
                BotCommand(command="help", description=i18n.get("commands.help", lang)),
                BotCommand(command="my_data", description=i18n.get("commands.my_data", lang)),
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
            BotCommand(command="my_data", description=i18n.get("commands.my_data", "en")),
        ]
        await bot.set_my_commands(commands_list_default)
        log.info("Bot commands set successfully")
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

