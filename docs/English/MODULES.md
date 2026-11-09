[← Back to docs index](README.md)

# Modules

The `teferdet/finances` codebase is organized logically into modules, keeping CQRS projections, configurations, repositories, business services, utilities, and presentation handlers separated.

## Directory Structure

```text
app/
├── __main__.py          # Entry point and supervised background tasks orchestration
├── bot.py               # Aiogram dispatcher, middleware, and router registration
├── cache.py             # Asynchronous in-memory TTL cache (L1)
├── config.py            # Typed configuration dataclasses loaded from JSON
├── db.py                # MongoDB async connection management via Motor + CQRS wrapper
├── debug_cli.py         # Debug CLI tools for manual testing
├── health.py            # Container healthcheck (Redis heartbeat, MongoDB ping, supervisor check)
├── i18n.py              # Custom JSON internationalization loader & resolver
├── logger.py            # Centralized structured logging setup
├── redis_client.py      # Two-tier L1/L2 Redis async cache with MemoryCache fallback
├── state.py             # FSM states definitions & dynamic admin state
├── cqrs/                # Event bus, DB interceptor, read projections & write-behind buffer
│   ├── bus.py           # In-process async event bus
│   ├── events.py        # Domain events (UserConfigChangedEvent, PortfolioChangedEvent, RatesUpdatedEvent)
│   ├── interceptor.py   # InterceptedDatabase / InterceptedCollection wrappers
│   ├── tasks.py         # TaskSupervisor for resilient background loops
│   ├── read/            # Read models (fiat.py, prices.py, users.py)
│   └── write/           # Write-behind buffer (activity.py)
├── handlers/            # Telegram message, callback, group, inline, and admin handlers
├── keyboards/           # Inline, group admin, and reply markup generators
├── middlewares/         # Middleware interceptors (error, rate-limit, throttle, group cooldown, i18n)
├── repositories/        # Database access layer (groups, communities)
├── services/            # Background tasks, central parser, analytics, security, portfolio, backups
└── utils/               # Helper modules (text processing, resilience, chat admin, ephemeral UI, sparkline, draft)
```

## Core Modules

### `app.cqrs`
Implements Command Query Responsibility Segregation and event-driven synchronization:
- `bus.py` & `events.py`: Lightweight async pub/sub bus dispatching `UserConfigChangedEvent`, `PortfolioChangedEvent`, and `RatesUpdatedEvent`.
- `interceptor.py`: Wraps `AsyncIOMotorDatabase` (`InterceptedDatabase`) so reads against `fiat_rates` are served from `fiat_store` in RAM and writes against `Users` or `fiat_rates` automatically emit invalidation/refresh events.
- `read/fiat.py` (`fiat_store`), `read/prices.py` (`price_store`), `read/users.py` (`get_user_view`): Fast in-memory projections for exchange rates, crypto/stock prices, and user preferences.
- `write/activity.py` (`activity_buffer`): Buffers `last_active` and `total_requests` increments in memory and flushes them in batches every 15 seconds.
- `tasks.py` (`supervisor`): Supervises background `asyncio.Task` workers with crash recovery and exponential backoff.

### `app.health`
Container health verification module (`python -m app.health`):
- Checks the `health:heartbeat` timestamp in Redis (written every 15s by the main bot loop) to detect event-loop deadlocks.
- Pings MongoDB (`db.command("ping")`) and verifies `TaskSupervisor` background tasks.

### `app.config`
Provides a strongly typed representation of the project configurations using Python `dataclasses`.
- `get_settings()`: Reads `config/settings.json` and parses it into `Settings`. Caches the result and hot-reloads if the file modification time changes.
- `get_currencies_data()`: Reads `config/currencies_data.json` to provide currency code-to-emoji/symbol mapping.
- `save_settings()`: Serializes a `Settings` object back to `settings.json` (used by `/admin` config changes).

### `app.db`
Handles asynchronous MongoDB operations using `motor`.
- `init_db(uri, db_name)`: Initializes the database connection, pools, and creates indexes via `ensure_indexes()`.
- `get_db()`: Retrieves the CQRS-wrapped `InterceptedDatabase` instance (`get_raw_db()` returns the raw `AsyncIOMotorDatabase`).
- `get_fiat_collection_name()`: Returns the active fiat collection (`fiat_rates` or `fiat_rates_dev`).

### `app.redis_client`
Two-tier L1/L2 caching (`TwoTierCache`) with transparent fallback:
- Combines an in-process L1 `MemoryCache` (~0ms latency) with an optional L2 Redis backend (`redis.asyncio`).
- `init_redis()`: Connects to Redis if `settings.redis.url` is configured; falls back to L1 `MemoryCache` seamlessly if Redis is unavailable.

### `app.repositories`
Encapsulates database reads and updates for group and community entities:
- `groups.py`: CRUD operations for group chats (`groups` collection), settings overrides, active status toggles, and usage counters.
- `communities.py`: Manages community mappings, associating groups with parent organizational entities.

### `app.i18n`
Provides multi-language support by loading string constants from JSON files located in `locales/`.
- `I18n`: Singleton class containing `get()` to fetch strings dynamically, resolving nested keys and formatting parameters with English (`en`) fallback.
- **Supported languages**: `en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`.

### `app.middlewares`
Lifecycle interceptors executing before handler dispatching:
- `i18n.py`: Loads the user's `UserView`, buffers user activity via `activity_buffer`, and injects `lang` and `I18n`.
- `rate_limit.py` & `throttle.py`: Sliding-window and per-user rate limiters (admin IDs exempt).
- `group_cooldown.py`: Enforces cooldown intervals between group conversion responses.
- `error.py`: Catches unhandled handler exceptions and logs structured diagnostics.

### `app.utils`
Helper modules:
- `text_processing.py`: `TextProcessing` provides a resilient parser supporting multiple numbering systems, currency symbols/slang, and conversion flows. `TextValidator` provides sanitization and command extraction.
- `resilience.py`: `CircuitBreaker` and `@retry_transient` decorator for external HTTP/scraping calls.
- `draft.py`: `sendMessageDraft` animation system for long-running requests.
- `ephemeral.py`: Ephemeral message helpers for group chats.
- `chat_admin.py`: Chat admin verification helpers (`is_chat_admin()`).
- `sparkline.py`: Unicode block character sparkline generator for visualizing price trends.

---

*Last updated: 2026-11-09*
