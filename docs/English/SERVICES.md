[← Back to docs index](README.md)

# Services

The `app/services/` directory contains business logic, database migrations, central parsing orchestrators, UI helper services, and `asyncio` background tasks that run concurrently with the Telegram bot.

These tasks interact with MongoDB and external financial APIs, utilizing a globally injected `Bot` instance for notification delivery when required.

## Background & Orchestration Services

### `parser_service.py` (`CentralParserService`)
The central orchestrator for all price fetching and currency conversions. Contains the `run_parser_loop()` background task and thread-safe parsing logic.
- **Initial Boot Population**: Automatically fetches critical currency lists on application startup if database collections are empty.
- **Hourly Fiat Cycle**: Verifies critical fiat currencies (`USD`, `EUR`, `UAH`, etc.) against a 1-hour TTL, triggering rate scraping via `fiat_parser.fetch_rates()` (using Cloudflare bypass).
- **Three-Hour Market Cycle**: Refreshes cryptocurrency and stock prices via CoinMarketCap and Yahoo Finance APIs, updating both legacy lists and flat `current_prices` cache.
- **Conversion Engine**: `convert_currencies()` provides fast, multi-pair, on-demand conversion calculations consumed by `exchange.py`, `inline_query.py`, `group_admin.py`, and `guest.py`.

### `alert_service.py`
Handles two automated background loops:
1. **Alert Checker**: Runs every 60 seconds (`run_alert_checker`). Compares un-triggered user price alerts (from `Alerts` collection) against `current_prices`. Uses batched messaging (`_send_batched`) to dispatch notifications under Telegram rate limits.
2. **Volatility Monitor**: Runs every 5 minutes (`run_volatility_monitor`). Takes price snapshots hourly and alerts users if tracked portfolio assets experience sudden price swings surpassing their `volatility_threshold_pct` (default 5%).

### `ephemeral_service.py`
Provides auto-deleting message lifecycle management (`send_ephemeral_or_fallback`, `edit_ephemeral_or_fallback`, `delete_ephemeral_or_fallback`).
- Used extensively in group chats (`/group_settings`, `/rate`) to auto-delete temporary menu messages after a configurable timeout, keeping group chat histories clean.

### `analytics_reporter.py`
Generates comprehensive usage metrics and health analytics for group administrators and system admins:
- Aggregates daily conversion request volume, popular currency pairs, active group participation, and community-wide activity metrics.

### `digest_service.py`
- **Weekly Digest**: Evaluates every 30 minutes, triggering on Sundays at 10:00 UTC. Compiles a "Weekly Portfolio Digest" summarizing 7-day portfolio P&L changes and broadcasts it to users.

### `backup.py`
- Runs daily at 03:00 UTC (`run_daily_backup_loop`). Extracts MongoDB data into JSON format, compresses it with `gzip`, and saves to `backups/backup_YYYYMMDD_HHMMSS.gz`, maintaining a rolling window of the 7 latest backups.

## Data & External Integration Services

### `crypto_parser.py`
- Uses `aiohttp` to fetch market listings from the `CoinMarketCap` API, populating `Crypto&Stocks` and updating `current_prices`.

### `stocks_parser.py`
- Wraps `yfinance` in an `asyncio.to_thread` / `run_in_executor` block to prevent blocking the async loop while retrieving stock ticker data.

### `fiat_parser.py`
- Uses `curl_cffi` with Chrome browser impersonation (`chrome120`) to bypass Cloudflare anti-bot challenges on `fx-rate.net`, scraping live fiat rates safely.

### `exchange_sync.py`
- **Exchanges Supported**: Binance, Bybit.
- Syncs API exchange balances utilizing signed `HMAC-SHA256` requests and updates user portfolio lots asynchronously.

### `portfolio_service.py`
- Handles portfolio CRUD operations, lot tracking, and server-side aggregation for total P&L calculations (`get_portfolio_with_pnl`).

### `security.py`
- Provides symmetric Fernet encryption (`cryptography.fernet`) for user API secrets stored in MongoDB. Encryption key is stored in `settings.security.fernet_key`.

### `export_service.py`
- Generates system database statistics and CSV/Markdown reports for system administrators.

### `error_tracking.py`
- Tracks data crawler health in `ProblematicSources` to report failing external APIs (CoinMarketCap, Yahoo Finance, fx-rate.net).

---

*Last updated: 2026-08-19*
