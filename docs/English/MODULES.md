[← Back to docs index](README.md)

# Modules

The `teferdet/finances` codebase is organized logically into modules, keeping configurations, repositories, business services, utilities, and presentation handlers separated.

## Directory Structure

```
app/
├── __main__.py          # Entry point and background tasks orchestration
├── bot.py               # Aiogram dispatcher, middleware, and router registration
├── cache.py             # Asynchronous in-memory TTL cache
├── config.py            # Typed configuration dataclasses loaded from JSON
├── db.py                # MongoDB async connection management via Motor
├── debug_cli.py         # Debug CLI tools for manual testing
├── i18n.py              # Custom JSON internationalization loader & resolver
├── logger.py            # Centralized structured logging setup
├── redis_client.py      # Optional Redis async client with MemoryCache fallback
├── state.py             # FSM states definitions
├── handlers/            # Telegram message, callback, and guest query handlers
├── keyboards/           # Inline, group admin, and reply markup generators
├── middlewares/         # Middleware interceptors (auth, i18n, rate-limit, throttle, group cooldown, error)
├── repositories/        # Database access layer (groups, communities)
├── services/            # Background tasks, central parser, analytics, security, portfolio
└── utils/               # Helper modules (text processing, chat admin helpers, ephemeral UI, sparkline, draft)

dashboard/
├── API/                 # .NET 8 REST API backend
│   ├── Controllers/     # AuthController, StatsController, ConfigController, ActionsController, HealthController
│   ├── Services/        # AuthService, StatsService, ConfigService
│   ├── Repositories/    # MongoContext (database singleton)
│   └── Models/          # Entities, Requests, Responses DTOs
├── frontend/            # React 18 + MUI 9 SPA (Vite build)
│   ├── src/
│   │   ├── api/         # Typed API client
│   │   ├── components/  # auth/, layout/, pages/, ui/
│   │   └── lib/         # Utility functions
│   └── nginx.conf       # NGINX config for production serving
└── nginx/               # Production NGINX reverse proxy config
```

## Core Modules

### `app.config`
Provides a strongly typed representation of the project configurations using Python `dataclasses`.
- `get_settings()`: Reads `config/settings.json` and parses it into `Settings`. Caches the result but reloads if the file modification time changes. Supports 11 typed sections: `BotSettings`, `DatabaseSettings`, `ApiKeysSettings`, `UrlsSettings`, `I18nSettings`, `ParserSettings`, `SecuritySettings`, `FeaturesSettings`, `DraftSettings`, `RedisSettings`, `SentrySettings`.
- `get_currencies_data()`: Reads `config/currencies_data.json` to provide fiat code-to-emoji mapping.
- `save_settings()`: Serializes a `Settings` object back to `settings.json` (used by admin config changes).

### `app.db`
Handles asynchronous MongoDB operations using `motor`.
- `init_db(uri, db_name)`: Initializes the database connection, pools, and creates indexes via `ensure_indexes()`.
- `get_db()`: Retrieves the initialized `AsyncIOMotorDatabase` instance.
- `get_fiat_collection_name()`: Returns the correct fiat collection dynamically, appending `_debug` if running in debug mode.

### `app.redis_client`
Optional Redis integration with transparent fallback.
- `init_redis()`: Connects to Redis using `redis.asyncio` if `settings.redis.url` is configured. Falls back to `MemoryCache` silently if Redis is unavailable or package is not installed.
- `redis_get(key)`, `redis_set(key, value, ttl)`, `redis_delete(key)`: Async operations that work with either Redis or in-memory cache.

### `app.repositories`
Encapsulates database reads and updates for group and community entities:
- `groups.py`: CRUD operations for group chats, settings overrides, active status toggles, and usage counters.
- `communities.py`: Manages Telegram Bot API 10.2 Community mappings, associating groups with parent organizational entities.

### `app.i18n`
Provides multi-language support by loading string constants from JSON files located in `locales/`.
- `I18n`: Singleton class containing `get()` to fetch strings dynamically, resolving nested keys and formatting parameters. Falls back to English (`en`) if a key is not found in the target language.
- **Supported languages**: `en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`.

### `app.middlewares`
Lifecycle interceptors executing before handler dispatching:
- `i18n.py`: Injects locale and `I18n` instances based on user or group preferences.
- `rate_limit.py`: Sliding window rate limiter — tracks per-user request counts within a configurable window. Admin IDs are exempt.
- `throttle.py`: Simple per-user rate limiter using in-memory hit tracking.
- `group_cooldown.py`: Enforces cooldown intervals between group conversion responses.
- `error.py`: Catches unhandled handler exceptions and logs structured diagnostics.

### `app.utils`
Helper modules:
- `text_processing.py`: `TextProcessing` provides a highly resilient parser supporting multiple numbering systems, standalone currency aliases, and conversion flows. `TextValidator` provides sanitization and command extraction logic.
- `draft.py`: `sendMessageDraft` animation system — animates text in the user input box while the bot processes requests. Uses undocumented Telegram Bot API method.
- `ephemeral.py`: Ephemeral message helpers for auto-deleting temporary messages.
- `chat_admin.py`: Chat admin verification helpers (`is_chat_admin()`).
- `sparkline.py`: Unicode block character sparkline generator for visualizing price trends in Telegram messages.

### `app.keyboards`
Contains builder functions for UI elements:
- `inline.py`: Contains pagination logic (`paginated_currency_keyboard`) and settings menus.
- `admin_groups.py`: Admin group management keyboards.
- `group_admin.py`: Generates group settings menus (`/group_settings`), language selection, and deactivation dialogs.
- `main.py`: Generates dynamic reply keyboards, toggling button sizes based on `BigButtons` preference and conditionally showing premium options or mini-apps.

---

*Last updated: 2026-08-19*
