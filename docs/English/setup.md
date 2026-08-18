# 🛠 Setup Guide

**TL;DR:** This guide provides detailed instructions for deploying Finances locally or on a server. It requires Python 3.11+, MongoDB, and a dedicated Telegram Bot token.

## Requirements

- **Python**: Version 3.11 or higher (as per `pyproject.toml` `target-version = "py312"`).
- **Database**: MongoDB (Local instance or MongoDB Atlas).
- **Telegram**: A Bot Token acquired from [@BotFather](https://t.me/BotFather).
- **System (Optional)**: `build-essential` or equivalent if building `curl_cffi` dependencies from source on certain Linux distributions.

## Dependencies

The project relies on the following core packages (from `requirements.txt`):

| Package | Version | Purpose |
|---------|---------|---------|
| `aiogram` | `>=3.30.0` | Core asynchronous Telegram Bot framework. |
| `motor` | `>=3.7.1` | Asynchronous MongoDB driver. |
| `curl_cffi` | `>=0.7.0` | Advanced HTTP client for bypassing Cloudflare/anti-bot protection during parsing. |
| `aiohttp` | `>=3.9.5` | Standard async HTTP client for API interactions. |
| `beautifulsoup4` | `>=4.12.0` | HTML parsing for the fiat rates scraper. |
| `yfinance` | `>=1.5.1` | Stock market data retrieval. |
| `pandas` | `>=3.0.3` | Data structuring, utilized internally by `yfinance`. |
| `psutil` | `>=7.2.2` | System diagnostics (RAM/CPU) for the Admin panel. |

## Configuration (`settings.json`)

The bot requires a configuration file at `config/settings.json`. Here is an example with explanations:

```json
{
  "bot": {
    "token": "YOUR_TELEGRAM_BOT_TOKEN",
    "admin_ids": [123456789], // Array of integers. Your Telegram User ID for /admin access.
    "version": "finances v6.0"
  },
  "database": {
    "mongo_uri": "mongodb://localhost:27017", // Connection string (Atlas or local)
    "mongo_database": "finances",             // DB name
    "pool_min": 5,
    "pool_max": 50
  },
  "api_keys": {
    "crypto": "YOUR_CRYPTO_API_KEY", // Optional/Placeholder for future APIs
    "stocks": "YOUR_STOCKS_API_KEY"  // Optional/Placeholder
  },
  "urls": {
    "github": "https://github.com/your-username/finances"
  },
  "i18n": {
    "supported_languages": ["en", "uk"],
    "default_language": "en"
  },
  "parser": {
    "auto_update": true,          // Toggle background parser
    "update_interval_sec": 3600   // Parser interval (1 hour)
  },
  "security": {
    "rate_limit_requests": 30,
    "rate_limit_window_sec": 60,
    "fernet_key": "YOUR_FERNET_KEY" // Optional encryption key if needed
  },
  "features": {
    "mini_app_enabled": false,   // Enable/disable Mini App button
    "groups_enabled": true,       // Enable/disable group chat auto-conversions
    "inline_mode_enabled": true   // Enable/disable Inline query mode
  },
  "draft": {
    "loading_threshold_sec": 0.05,  // Delay threshold before showing draft loading animation
    "animation_interval_sec": 0.25, // Frame interval for draft loading animation
    "preview_delay_sec": 0.15      // Morphing preview delay before finalized answer message
  }
}
```

## Running Locally

Clone the repository and run it using a virtual environment:

```bash
git clone https://github.com/your-username/finances-dev.git
cd finances-dev

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application module
python -m app
```
*Tip: Passing `--debug` argument (e.g., `python -m app --debug`) will force the database to use `fiat_rates_debug` collection instead of production.*

## Running as a Systemd Service

For production deployments, use a systemd unit file (example from `deploy/finances-bot.service`):

```ini
[Unit]
Description=Finances Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/finances
Environment="PATH=/home/ubuntu/finances/venv/bin"
ExecStart=/home/ubuntu/finances/venv/bin/python -m app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Place it in `/etc/systemd/system/`, then run `sudo systemctl enable --now finances-bot.service`.
