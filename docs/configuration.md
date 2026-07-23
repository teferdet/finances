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

## Runtime Configuration via `/admin`

Certain operational parameters can be adjusted on the fly by administrators. The bot persists these dynamic states (either in `Settings` collection in MongoDB or by modifying `settings.json` if implemented):

- **Parser State**: Toggling the parser on or off dynamically without stopping the bot process.
- **Update Interval**: Modifying `parser.update_interval_sec` on the fly.
- **Dynamic Admins**: The `app/state.py` holds `dynamic_admin_ids` loaded from the MongoDB `Settings` collection (`_id: "dynamic_admins"`), allowing the addition of admins without editing `settings.json`.
