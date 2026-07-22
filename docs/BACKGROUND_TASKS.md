[← Back to docs index](README.md)

# Background Tasks

The bot relies heavily on asyncio to run concurrent background tasks within the main process. This eliminates the need for external infrastructure like Celery or Redis.

Tasks are bootstrapped in `app/__main__.py` right before the `aiogram` Dispatcher begins polling. They are gathered into an `asyncio.TaskGroup` or individual `asyncio.create_task()` references and gracefully cancelled when the bot receives a shutdown signal (SIGINT/SIGTERM).

## 1. Central Parser Orchestrator (`CentralParserService`)
**File:** `app/services/parser_service.py` -> `run_parser_loop()`

- **Initial Boot:** Checks MongoDB for critical currency presence. If missing or incomplete, performs immediate initial rate population across fiat, crypto, and stock pairs.
- **Hourly Fiat Cycle:** Verifies critical fiat currencies (`USD`, `EUR`, `UAH`, etc.) against a 1-hour TTL, triggering rate scraping via `fiat_parser.fetch_rates()` (using Cloudflare bypass).
- **Three-Hour Market Cycle:** Refreshes cryptocurrency and stock prices via CoinMarketCap and Yahoo Finance APIs, updating both legacy lists and flat `current_prices` cache.

## 2. Alert Checker
**File:** `app/services/alert_service.py` -> `run_alert_checker()`

- **Interval:** Runs every 60 seconds.
- **Action:** Pulls un-triggered alerts from MongoDB (`triggered=False`). Evaluates live prices from `current_prices`. If conditions (`above`/`below`) match, constructs localized notification via `I18n` and dispatches messages with rate-controlled batching.

## 3. Volatility Monitor
**File:** `app/services/alert_service.py` -> `run_volatility_monitor()`

- **Snapshotting:** At the end of every Parser cycle, `save_price_snapshot()` logs price dictionary into `price_history`.
- **Interval:** Runs every 5 minutes.
- **Action:** Compares `current_prices` against snapshot from 1 hour ago. If asset price delta exceeds threshold ($\ge 3\%$), searches active user portfolios holding that asset and alerts users surpassing their `volatility_threshold_pct`.

## 4. Weekly Portfolio Digest
**File:** `app/services/digest_service.py` -> `run_digest_scheduler()`

- **Interval:** Evaluates conditions every 30 minutes.
- **Action:** Triggers at 10:00 UTC every Sunday (`DIGEST_DAY = 6`). Pulls 7-day-old price snapshot, compiles weekly P&L summaries for portfolio holders, and dispatches localized digest reports.

## 5. Ephemeral Message Cleanup
**File:** `app/utils/ephemeral.py` / `app/services/ephemeral_service.py`

- **Trigger:** Scheduled after UI actions in group chats (`/group_settings`).
- **Action:** Tracks temporary menu message IDs and automatically deletes them after a configured timeout (e.g. 60–300s), maintaining clean group chat histories.

## 6. Local MongoDB Backups
**File:** `app/services/backup.py` -> `run_daily_backup_loop()`

- **Interval:** Runs daily at 03:00 UTC.
- **Action:** Exports database collections into JSON format, compresses into `.gz` archives under `backups/backup_YYYYMMDD_HHMMSS.gz`, and cleans up backups older than 7 days to maintain storage efficiency.

---

*Last updated: 2026-07-22*

