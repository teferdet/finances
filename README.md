# 📊 Finances Telegram Bot

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/aiogram-3.x-green.svg" alt="Aiogram Version">
  <img src="https://img.shields.io/badge/MongoDB-Powered-brightgreen.svg" alt="Database">
  <img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="License">
</div>

<br>

**Finances** is a comprehensive, open-source personal financial assistant for Telegram. Built on async Python, it provides real-time fiat, crypto, and stock tracking, portfolio management, and advanced administrative capabilities directly via the Telegram interface.

## 🌟 Why Use Finances?
* **Administration Without Redeploy**: Fully control your bot via the interactive `/admin` panel. Change parsing intervals, toggle features, or even restart the bot entirely without touching the server.
* **Built-in Observability**: Real-time server diagnostics (CPU, RAM), database footprint tracking, and in-app error log viewing.
* **i18n-First Architecture**: Custom-built, deeply integrated localization engine supporting nested JSON keys and seamless language switching.
* **Secure by Design**: Double-check authorization on sensitive actions (like log downloads) ensures safe operation.

---

## ✨ Features

### 💱 Core Capabilities
* **Async & High Performance**: Built on `aiogram` 3.x and `motor` for asynchronous MongoDB operations.
* **Background Parser**: Custom `curl_cffi` based parser fetching live rates, with intervals configurable on the fly.
* **Price Alerts & Volatility Monitor**: Set specific targets or track portfolio volatility with background schedulers.
* **Localization System**: Fully localized interface using a custom dictionary-based i18n engine.
* **State Caching & Logging**: Centralized error logging and resilient task tracking.

### 🔐 Admin Panel Modules (`/admin`)
| Module | Description |
|--------|-------------|
| **Analytics & Statistics Dashboard** | Monitor daily/weekly active users, total lifetime requests, and parser cycles. |
| **System Configuration** | Manage parser auto-updater state, update intervals, and core fiat currencies on the fly. |
| **Server Diagnostics** | View real-time bot RAM allocation, total system RAM, CPU load, and database storage footprint. |
| **Error Logs** | Read recent incidents directly in Telegram, export full `.log` files securely, or purge logs. |
| **Mass Message Broadcast** | Push formatted HTML announcements to all registered bot users. |
| **Restart Bot** | Interactive 2-step restart sequence directly from Telegram, persisting state across reboots. |

---

## 🚀 Tech Stack

* **Framework**: `aiogram` (v3.x) - Asynchronous Telegram Bot API wrapper.
* **Database**: `motor` (MongoDB async driver).
* **Networking**: `curl_cffi` (advanced anti-bot bypass) & `aiohttp`.
* **Data Sources**: `yfinance`, `beautifulsoup4`, `pandas`.
* **Monitoring**: `psutil` for system diagnostics.

---

## 📂 Project Structure

```text
finances-dev/
├── app/
│   ├── handlers/        # Message, callback, and admin routers
│   ├── keyboards/       # Inline & Reply UI builders
│   ├── services/        # Background parsers, alerts, exports
│   ├── utils/           # Helper functions and text processing
│   ├── bot.py           # Bot instance & dispatcher setup
│   ├── config.py        # Configuration models
│   ├── db.py            # MongoDB connection & indexes
│   ├── i18n.py          # Custom localization engine
│   ├── logger.py        # Centralized logging configuration
│   └── __main__.py      # App entry point
├── locales/             # JSON translation files (en.json, uk.json, etc.)
├── config/              # Configuration files (settings.json)
├── logs/                # Local log storage
└── requirements.txt     # Python dependencies
```

---

## 📚 Documentation

The complete documentation for Finances is located in the `docs/` directory.

*   **[Setup Guide](docs/setup.md)**: Installation, prerequisites, and running the bot.
*   **[Architecture](docs/architecture.md)**: Core components, data flow, and background tasks.
*   **[Configuration](docs/configuration.md)**: Environment setup and runtime `/admin` configuration.
*   **[Admin Panel](docs/admin-panel.md)**: Guide to using the in-app `/admin` modules.
*   **[Localization (i18n)](docs/i18n.md)**: How to manage translations and add languages.
*   **[Deployment](docs/deployment.md)**: CI/CD workflows and production deployment.
*   **[Database Schema](docs/database-schema.md)**: MongoDB collections and data structures.
*   **[Contributing](docs/contributing.md)**: Guidelines for contributing to the project.
*   **[FAQ & Troubleshooting](docs/faq-troubleshooting.md)**: Solutions to common issues.

For a full index, see the [Documentation Index](docs/README.md).

---

## 🌐 Localization (i18n)

Finances uses a custom JSON-based i18n system. All texts are stored in the `locales/` directory. 
To add a new language, simply copy `locales/en.json`, translate the values, and add the new language code to your `settings.json` configuration. See [Setup Guide](setup.md) for more details.

---

## 🤝 Contributing

Contributions are always welcome! Feel free to open issues or submit Pull Requests for:
- Adding new locales/languages.
- Implementing new parsing sources for stocks.
- Optimizing database queries.

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
