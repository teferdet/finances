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
├── state.py             # FSM states definitions
├── handlers/            # Telegram message, callback, and guest query handlers
├── keyboards/           # Inline, group admin, and reply markup generators
├── middlewares/         # Middleware interceptors (auth, i18n, rate-limit, group cooldown, error)
├── repositories/        # Database access layer (groups, communities)
├── services/            # Background tasks, central parser, analytics, security, portfolio
└── utils/               # Helper modules (text processing, chat admin helpers, ephemeral UI)
```

## Core Modules

### `app.config`
Provides a strongly typed representation of the project configurations using Python `dataclasses`.
- `get_settings()`: Reads `config/settings.json` and parses it into `Settings`. Caches the result but reloads if the file modification time changes.
- `get_currencies_data()`: Reads `config/currencies_data.json` to provide fiat code-to-emoji mapping.

### `app.db`
Handles asynchronous MongoDB operations using `motor`.
- `init_db(uri, db_name)`: Initializes the database connection, pools, and creates indexes via `ensure_indexes()`.
- `get_db()`: Retrieves the initialized `AsyncIOMotorDatabase` instance.
- `get_fiat_collection_name()`: Returns the correct fiat collection dynamically, appending `_debug` if running in debug mode.

### `app.repositories`
Encapsulates database reads and updates for group and community entities:
- `groups.py`: CRUD operations for group chats, settings overrides, active status toggles, and usage counters.
- `communities.py`: Manages Telegram Bot API 10.2 Community mappings, associating groups with parent organizational entities.

### `app.i18n`
Provides multi-language support by loading string constants from JSON files located in `locales/`.
- `I18n`: Singleton class containing `get()` to fetch strings dynamically, resolving nested keys and formatting parameters. Falls back to English (`en`) if a key is not found in the target language.

### `app.middlewares`
Lifecycle interceptors executing before handler dispatching:
- `i18n.py`: Injects locale and `I18n` instances based on user or group preferences.
- `rate_limit.py` & `throttle.py`: Protects against user command spam.
- `group_cooldown.py`: Enforces cooldown intervals between group conversion responses.
- `error.py`: Catches unhandled handler exceptions and logs structured diagnostics.

### `app.utils.text_processing`
Handles user input containing financial data.
- `TextProcessing`: Provides a highly resilient parser (`_parse_conversion_request`, `_parse_symbol_amount`, `_parse_code_amount`, etc.) supporting multiple numbering systems, standalone currency aliases, and conversion flows (e.g., "100 USD to UAH").
- `TextValidator`: Provides sanitization and command extraction logic.

### `app.keyboards`
Contains builder functions for UI elements:
- `inline.py`: Contains pagination logic (`paginated_currency_keyboard`) and settings menus.
- `group_admin.py`: Generates group settings menus (`/group_settings`), language selection, and deactivation dialogs.
- `main.py`: Generates dynamic reply keyboards, toggling button sizes based on `BigButtons` preference and conditionally showing premium options or mini-apps.

---

*Last updated: 2026-07-22*

