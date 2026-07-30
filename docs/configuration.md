# ⚙️ Configuration Reference

**TL;DR:** Configuration is handled by reading `config/settings.json` into typed dataclasses in `app/config.py`. Certain parameters can also be modified at runtime without restarting the bot.

## `settings.json` Properties

| Parameter | Type | Default / Example | Usage in Code | Description |
|-----------|------|-------------------|---------------|-------------|
| `bot.token` | `str` | `""` | `app.bot.py` | Core Telegram Bot token required to launch. |
| `bot.admin_ids` | `List[int]` | `[]` | `app.handlers.admin.py` | Users allowed to access the `/admin` panel. |
| `database.mongo_uri` | `str` | `""` | `app.db.py` | MongoDB connection string. |
| `database.mongo_database`| `str` | `"finances"` | `app.db.py` | Target MongoDB database name. |
| `i18n.supported_languages`| `List[str]` | `["en", "uk"]` | `app.i18n.py` | Languages active in the localization engine. |
| `parser.update_interval_sec`| `int` | `3600` | `app.services.parser_service.py` | How often the `curl_cffi` parser runs. |
| `security.rate_limit_requests`| `int` | `30` | `app.middlewares.rate_limit.py`| Throttling threshold. |
| `features.groups_enabled`| `bool` | `true` | `app.handlers.groups.py`, `app.bot.py` | Enable/disable public group chat auto-conversions and middlewares. |
| `features.inline_mode_enabled`| `bool` | `true` | `app.handlers.inline_query.py`, `app.bot.py` | Enable/disable Telegram Inline query mode handler. |
| `features.mini_app_enabled`| `bool` | `false` | `app.handlers.start.py` | Enable/disable Mini App button access. |
| `draft.loading_threshold_sec`| `float` | `0.05` | `app.handlers.exchange.py` | Delay threshold in seconds before showing animated loading draft. |
| `draft.animation_interval_sec`| `float` | `0.25` | `app.handlers.exchange.py` | Frame animation interval in seconds for loading draft spinner. |
| `draft.preview_delay_sec`| `float` | `0.15` | `app.handlers.exchange.py` | Morphing preview pause in seconds before finalized answer message. |

## Runtime Configuration via `/admin`

Certain operational parameters can be adjusted on the fly by administrators. The bot persists these dynamic states by writing to `config/settings.json` or MongoDB:

- **Features Control (`⚙️ Features`)**: Interactively toggle `groups_enabled`, `inline_mode_enabled`, and `mini_app_enabled` on/off in real-time.
- **Draft Loading Threshold**: Interactively cycle `draft.loading_threshold_sec` (`0.01s` ➔ `0.05s` ➔ `0.1s` ➔ `0.25s` ➔ `0.4s`) to adjust when draft animation triggers.
- **Parser State**: Toggling the parser on or off dynamically without stopping the bot process.
- **Update Interval**: Modifying `parser.update_interval_sec` on the fly.
- **Dynamic Admins**: The `app/state.py` holds `dynamic_admin_ids` loaded from the MongoDB `Settings` collection (`_id: "dynamic_admins"`), allowing the addition of admins without editing `settings.json`.
