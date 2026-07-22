[← Back to docs index](README.md)

# Database Structure

The `teferdet/finances` bot uses **MongoDB** with the asynchronous Python driver **Motor** (`motor.motor_asyncio`).

## Connection Setup (`app/db.py`)

- `init_db(uri, db_name)`: Establishes the database connection using connection pooling bounds defined in `settings.json` (`pool_min`, `pool_max`). 
- **Startup Indexes**: The initialization step executes `ensure_indexes()`, forcing `TTL` (Time-To-Live) and standard query indexes asynchronously on collections to guarantee optimal read/write speeds.
- **Debug Collections**: `get_fiat_collection_name()` returns `fiat_rates_debug` instead of `fiat_rates` if the bot is started with the `--debug` flag.

## Collections

### 1. `Users`
Stores core user profiles, preferences, and portfolio lot data.
- `_id`: Telegram User ID (`int`).
- `Name`, `Username`, `Language`, `Premium`, `Sign up`.
- `Fiat currency`, `Crypto currency`, `Stocks`: The user's active watchlists.
- `BaseCurrency`: Default calculation currency.
- `MainMenu`, `BigButtons`: UI customizations.
- `portfolio`: Array of cost-basis asset lot dictionaries.

### 2. `Groups`
Stores configurations and settings for Telegram groups where the bot is installed (`app/repositories/groups.py`).
- `_id` / `chat_id`: Telegram Chat ID (`int`).
- `Title`, `Type` (`supergroup` / `group`), `Members`.
- `Status`: `Active` or `Left`.
- `Input`: Currencies the bot listens to automatically in text messages.
- `Output`: Currencies it converts values to automatically.
- `community_id`: Optional parent Telegram Community ID.
- `settings`: Custom group preferences (e.g. `language`, `ephemeral_timeout`, `cooldown_seconds`).
- `stats`: Operational metrics (total conversion requests, last active date).

### 3. `Communities` (Bot API 10.2+)
Stores organizational entity groupings for Telegram supergroups and channels (`app/repositories/communities.py`).
- `_id` / `community_id`: Telegram Community ID (`str`).
- `name`: Community name.
- `discovered_at`: Timestamp of discovery.
- `group_chat_ids`: Array of chat IDs (`int`) belonging to this community.

### 4. `Alerts`
Stores user-defined price notification triggers.
- `_id`: `ObjectId`.
- `user_id`: Telegram User ID.
- `currency_from`, `currency_to`, `target_price`.
- `condition`: String (`above` or `below`).
- `triggered`: Boolean.

### 5. `fiat_rates`
A high-frequency update collection managed by `fiat_parser.py` / `parser_service.py`.
- `currency`: The base fiat currency (e.g., `USD`).
- `rates`: Dictionary mapping target currencies to exchange rate, reverse rate, symbol, and emoji.
- `updated_at`: Datetime timestamp.

### 6. `current_prices`
Flat caching collection used for instant MongoDB aggregation P&L calculations.
- `_id`: Ticker symbol (e.g., `BTC`, `AAPL`).
- `price_usd`: Live price referenced in USD.
- `source`: String (`crypto` or `stock`).

### 7. `price_history`
Used for short-term volatility alerts and weekly digests.
- `timestamp`: Snapshot creation time.
- `prices`: Dictionary mapping `{ticker: price_usd}`.
- *Retention*: Cleaned up by `alert_service.py` older than 7 days.

### 8. `ApiKeys`
Stores user API keys bound for exchange synchronization (Binance, Bybit).
- `api_secret`: Stored symmetrically encrypted (Fernet cipher).

### 9. `Status` & `ProblematicSources`
- `Status`: Tracks global singleton states (e.g., `last_digest_sent`, `last_crypto_stocks_update`).
- `ProblematicSources`: Logs crawler failures from CoinMarketCap, Yahoo Finance, or `fx-rate.net`.

---

*Last updated: 2026-07-22*

