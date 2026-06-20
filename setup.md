# Setup & Administration Guide

## 📌 Prerequisites
- **Python 3.11+**
- **MongoDB instance** (local or Atlas)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))

## ⚙️ Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/your-username/finances-dev.git
cd finances-dev
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

## 🛠 Configuration
Configuration is loaded from `config/settings.json` and parsed using data classes in `app/config.py`. 

| Parameter | Required | Description |
|-----------|----------|-------------|
| `bot.token` | Yes | Your Telegram Bot Token. |
| `bot.admin_ids` | Yes | List of Telegram User IDs with admin access (required for `/admin` and log downloads). |
| `database.mongo_uri` | Yes | MongoDB connection string (e.g., `mongodb://localhost:27017`). |
| `database.mongo_database` | No | Database name (default: `finances`). |
| `parser.auto_update` | No | Enables/disables the background parser. Can be toggled in real-time via Admin Panel. |
| `parser.update_interval_sec` | No | Parsing interval in seconds (default: `3600`). Can be modified via the Admin Panel. |

## 🗄 Database Setup
The bot uses `motor` for async MongoDB connections. You don't need to manually run migrations. The database schema and indexes are automatically initialized on startup via `ensure_indexes()` in `app/db.py`.

## 🌐 Locales
Localization is handled by a custom i18n engine (`app/i18n.py`).
Translations are stored in `locales/` as JSON files (e.g., `en.json`, `uk.json`).

**How to add a new language:**
1. Copy `locales/en.json` to `locales/YOUR_LANG_CODE.json` (e.g., `es.json`).
2. Translate the values while keeping the keys and `{variable}` placeholders intact.
3. Add the language code to `i18n.supported_languages` in your configuration (`settings.json`).

## 🚀 Running the Bot
To start the bot in development or production, run the application module:
```bash
python -m app
```

## 🔐 Admin Panel
To access the admin panel, send the `/admin` command in the bot. **Your Telegram User ID must be in the `admin_ids` list in the configuration.**

### Admin Modules & Maintenance
* **Analytics & Statistics Dashboard**: View Total Users, Daily Active Users (DAU), parser cycles, and recent errors.
* **System Configuration**: Manage the parser settings. **Admin action:** Ensure the `update_interval_sec` is not set too low to avoid rate-limiting from data sources.
* **User Analytics**: View audience overview, active users, and power users.
* **Server Diagnostics**: Monitor bot RAM, system CPU, and database size. **Admin action:** Keep an eye on memory usage and DB collection sizes.
* **Error Logs**: View recent exceptions and download/purge logs. **Admin action:** Log downloading requires a double-check authorization (your ID must be in `admin_ids`). Keep the admin list minimal and secure. Periodically download and clear logs if they get too large.
* **Mass Message Broadcast**: Push announcements to all registered users.
* **Restart Bot**: Safely restarts the bot process directly from Telegram.

## ❓ Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| **Bot won't start** | Missing config or invalid MongoDB URI | Ensure `config/settings.json` is properly configured and MongoDB is running. |
| **Admin command blocked** | User ID not in `admin_ids` | Add your numeric Telegram ID to `bot.admin_ids` in `config/settings.json`. |
| **Log download fails** | Double authorization failed | Verify your ID is exactly matched in `admin_ids` (must be an integer, not a string). |
| **Parser not updating data** | Parser disabled or interval too high | Check **System Configuration** in the Admin panel and ensure the parser is turned ON (`🟢 Parser: Enabled`). |
| **UI shows English instead of local lang** | Missing locale keys | Check the bot logs for warnings. Ensure your local `.json` file is up-to-date with `en.json`. |
