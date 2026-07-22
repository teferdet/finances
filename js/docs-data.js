/**
 * Finances Telegram Bot - Documentation Dataset
 * Contains pre-compiled markdown contents for instant static rendering on GitHub Pages.
 */

window.DOCS_DATA = {
  "readme": {
    "title": "Home / Overview",
    "icon": "🏠",
    "category": "Getting Started",
    "content": `# 📊 Finances Telegram Bot

**Finances** is a comprehensive, open-source personal financial assistant for Telegram. Built on async Python 3.12+, it provides real-time fiat, crypto, and stock tracking, portfolio management, and advanced administrative capabilities directly via the Telegram interface.

---

## 🌟 Key Highlights

* **Administration Without Redeploy**: Fully control your bot via the interactive \`/admin\` panel. Change parsing intervals, toggle features, or restart the bot directly inside Telegram.
* **Built-in Observability**: Real-time server diagnostics (CPU, RAM), database footprint tracking, and in-app error log viewing.
* **i18n-First Architecture**: Custom-built, deeply integrated localization engine supporting nested JSON keys and seamless language switching.
* **Secure by Design**: Double-check authorization on sensitive actions, encrypted API secrets (Fernet cipher), and flood control.

---

## ✨ Features Breakdown

### 💱 Core Capabilities
* **Async & High Performance**: Built on \`aiogram\` 3.x and \`motor\` for asynchronous MongoDB operations.
* **Background Parser**: Custom \`curl_cffi\` based parser fetching live rates with Cloudflare anti-bot bypass.
* **Price Alerts & Volatility Monitor**: Set specific targets or track portfolio volatility with background schedulers.
* **Localization System**: Fully localized interface supporting multiple languages (\`en\`, \`uk\`, \`pl\`, \`cs\`, \`sk\`, \`de\`, \`fr\`).
* **Bot API 10.x Guest Mode**: Evaluates mentions of \`@bot\` in non-member group chats cleanly.

### 🔐 Admin Panel Modules (\`/admin\`)
| Module | Description |
|--------|-------------|
| **Analytics & Statistics** | Monitor daily/weekly active users, total lifetime requests, and parser cycles. |
| **System Configuration** | Manage parser auto-updater state, update intervals, and core currencies on the fly. |
| **Server Diagnostics** | View real-time RAM allocation, CPU load, and database storage footprint. |
| **Error Logs** | Read recent incidents directly in Telegram, export full \`.log\` files, or purge logs. |
| **Mass Broadcast** | Push formatted HTML announcements to all registered bot users with rate limiting. |
| **Restart Bot** | Interactive 2-step restart sequence directly from Telegram, persisting state across reboots. |

---

## 🚀 Tech Stack

* **Framework**: \`aiogram\` (v3.x) - Asynchronous Telegram Bot API wrapper.
* **Database**: \`motor\` (MongoDB async driver).
* **Networking**: \`curl_cffi\` (advanced anti-bot bypass) & \`aiohttp\`.
* **Data Sources**: \`yfinance\`, \`beautifulsoup4\`, \`pandas\`, CoinMarketCap.
* **Monitoring**: \`psutil\` for system diagnostics.

---

## 📂 Project Structure

\`\`\`text
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
\`\`\`

---

## 📄 License
This project is open-source and available under the **MIT License**.`
  },
  "architecture": {
    "title": "Architecture Overview",
    "icon": "🏛️",
    "category": "Core Design",
    "content": `# Architecture Overview

The \`teferdet/finances\` bot is built using **Python 3.12+** and the **[aiogram 3.x](https://docs.aiogram.dev/)** asynchronous framework. It is designed to be highly concurrent, resilient, and responsive to private messages, group chats, and Bot API 10.x guest queries.

## Core Architecture Components

1. **Entry Point & Orchestration (\`app/__main__.py\`):**
   - Initializes typed configurations (\`config.py\`), establishes async MongoDB pool (\`db.py\`), starts background task loops (\`CentralParserService\`, \`AlertChecker\`, \`VolatilityMonitor\`, \`WeeklyDigest\`), and starts the Telegram bot polling loop.

2. **Routing & Handlers (\`app/handlers/\`):**
   - Domain-driven routers (\`crypto.py\`, \`portfolio.py\`, \`alerts.py\`, \`group_admin.py\`, \`admin_groups.py\`, \`guest.py\`, \`admin.py\`).
   - Private, group, and guest updates (\`F.guest_query_id\`) are filtered at the router level.

3. **Repositories (\`app/repositories/\`):**
   - Encapsulates database access for complex domain entities:
     - \`groups.py\`: Manages group chat configurations, member tracking, settings overrides, and usage stats.
     - \`communities.py\`: Handles Telegram Bot API 10.2 Community structures.

4. **Background Services & Central Parser (\`app/services/\`):**
   - \`parser_service.py\` (\`CentralParserService\`): Central orchestrator for background currency refresh and on-demand conversion.
   - \`ephemeral_service.py\`: Handles self-deleting message lifecycle for clean UI interactions in groups.
   - \`analytics_reporter.py\`: Aggregates usage metrics for system and group administrators.

5. **Data Persistence (MongoDB & Motor):**
   - Asynchronous MongoDB interactions via \`motor\`.
   - Collections: \`Users\`, \`Groups\`, \`Communities\`, \`Alerts\`, \`fiat_rates\`, \`current_prices\`, \`price_history\`, \`ApiKeys\`, \`Status\`, \`ProblematicSources\`.

6. **Caching Layer (\`app/cache.py\`):**
   - Asynchronous in-memory TTL cache reducing database load for \`currencies_info\` and UI state.

---

## Data Flow Diagram

\`\`\`mermaid
graph TD
    User([Telegram User / Group Admin]) --> Bot[Aiogram Dispatcher]
    Bot --> Middlewares[Middlewares: Auth, i18n, Rate Limit, Group Cooldown, Error]
    Middlewares --> Handlers[Domain & Admin Handlers]
    
    Handlers --> Repositories[Repositories: Groups, Communities]
    Handlers --> Services[Services: CentralParser, Ephemeral, Portfolio]
    
    Repositories --> DB[(MongoDB)]
    Services --> DB
    Services --> Cache[In-Memory Cache]
    
    subgraph Background Tasks
        CentralParser[Central Parser Service]
        AlertLoop[Alert Checker]
        VolatilityLoop[Volatility Monitor]
        DigestLoop[Weekly Digest]
        BackupLoop[Local Backup]
    end
    
    CentralParser --> ExtAPIs[External APIs: CMC, Yahoo, fx-rate]
    CentralParser --> DB
    
    AlertLoop --> DB
    AlertLoop -.-> User
    
    VolatilityLoop --> DB
    VolatilityLoop -.-> User
    
    DigestLoop --> DB
    DigestLoop -.-> User
\`\`\`

---

## System Security & Constraints

- **Rate Limiting & Cooldowns:** Protects private and group channels from command spam (\`rate_limit.py\`, \`group_cooldown.py\`).
- **Bot API 10.x Guest Mode:** Safe single-message query evaluation for \`@bot\` mentions in non-member chats (\`guest.py\`).
- **Cloudflare Bypass:** Uses \`curl_cffi\` with browser fingerprinting (\`chrome120\`) to scrape fiat rates securely.
- **API Secret Encryption:** Symmetrically encrypts user exchange secrets (\`Fernet\`) before storing in database (\`security.py\`).`
  },
  "modules": {
    "title": "Modules Reference",
    "icon": "📦",
    "category": "Core Design",
    "content": `# Modules Overview

The \`teferdet/finances\` codebase is organized logically into clean modules, keeping configurations, repositories, business services, utilities, and presentation handlers separated.

\`\`\`text
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
\`\`\`

## Key Module Responsibilities

### \`app.config\`
Provides a strongly typed representation of the project configurations using Python \`dataclasses\`.
- \`get_settings()\`: Reads \`config/settings.json\` and parses it into \`Settings\`.
- \`get_currencies_data()\`: Reads \`config/currencies_data.json\` to provide fiat code-to-emoji mapping.

### \`app.db\`
Handles asynchronous MongoDB operations using \`motor\`.
- \`init_db(uri, db_name)\`: Initializes the database connection and creates indexes via \`ensure_indexes()\`.
- \`get_fiat_collection_name()\`: Returns \`fiat_rates\` or \`fiat_rates_debug\` dynamically.

### \`app.repositories\`
Encapsulates database access for group and community entities:
- \`groups.py\`: CRUD operations for group chats and settings overrides.
- \`communities.py\`: Manages Telegram Bot API 10.2 Community mappings.

### \`app.i18n\`
Provides multi-language support loading translation files from \`locales/\`.
- \`I18n\`: Singleton class resolving dot-notation keys (\`keyboard.settings.bot\`) with fallback to English (\`en\`).

### \`app.middlewares\`
Lifecycle interceptors executing before handler dispatching:
- \`i18n.py\`: Injects locale and \`I18n\` instance into handler context.
- \`rate_limit.py\` & \`group_cooldown.py\`: Spam protection.
- \`error.py\`: Catches unhandled handler exceptions and logs structured diagnostics.`
  },
  "handlers": {
    "title": "Handlers & Routers",
    "icon": "🎛️",
    "category": "Architecture",
    "content": `# Handlers & Routers

Handlers define the core interaction loop with users and groups in Telegram. Built on \`aiogram 3.x\` routers, each file exports a \`router\` instance registered centrally in \`bot.py\`.

## Router Overview (\`app/handlers/\`)

1. **\`admin.py\`**: Handles \`/admin\` dashboard, \`/broadcast\` FSM flow, diagnostics, maintenance mode, and error log downloads.
2. **\`admin_groups.py\`**: Manages active Telegram groups and Bot API 10.2 Communities for system admins.
3. **\`alerts.py\`**: Manages user price alerts (\`/alert\`) and volatility threshold configurations.
4. **\`crypto.py\`**: Displays top cryptocurrencies and market valuations (\`/crypto\`).
5. **\`exchange.py\` & \`exchange_api.py\`**: Handles exchange account API key binding (Binance, Bybit) and balance sync.
6. **\`group_admin.py\`**: Manages group currency preferences (\`/group_settings\`, \`/rate\`, \`/group_stats\`) with anonymous admin support and self-deleting UI messages.
7. **\`groups.py\`**: Listens to \`my_chat_member\` events when bot is added or removed from groups.
8. **\`guest.py\`**: Handles Bot API 10.0+ guest queries (\`@bot\` mentions in non-member chats) via \`answer_guest_query()\`.
9. **\`inline_query.py\`**: Supports \`@fStatisticsBot 100 USD\` inline queries in any Telegram chat.
10. **\`language.py\`**: Provides localized language selector inline keyboard (\`/language\`).
11. **\`my_data.py\`**: Overview of user profile data, active watchlists, and reset options.
12. **\`portability.py\`**: Generates portfolio CSV exports (\`/export\`) and imports (\`/import\`).
13. **\`portfolio.py\`**: Financial portfolio tracking (\`/portfolio\`) and P&L aggregation.
14. **\`settings.py\`**: Multi-page user settings menu.
15. **\`start.py\`**: User onboarding (\`/start\`, \`/help\`, \`/privacy\`).
16. **\`stocks.py\`**: Displays stock market quotes (\`/stocks\`).
17. **\`text.py\`**: Natural language financial text parser for auto-conversions.`
  },
  "services": {
    "title": "Services & Parser",
    "icon": "⚙️",
    "category": "Core Logic",
    "content": `# Core Services & Parser

The \`app/services/\` directory contains business logic, database migrations, central parsing orchestrators, and background tasks.

## 1. Central Parser Orchestrator (\`parser_service.py\`)
- **Initial Boot**: Fetches critical currency pairs on bot startup if database is empty.
- **Hourly Fiat Refresh**: Scrapes fiat rates via \`fiat_parser.py\` using \`curl_cffi\` Chrome impersonation to bypass Cloudflare protection.
- **Three-Hour Market Refresh**: Pulls crypto and stock market data from CoinMarketCap and Yahoo Finance APIs.
- **Conversion Engine**: \`convert_currencies()\` performs instant multi-pair conversions.

## 2. Alert & Volatility Service (\`alert_service.py\`)
- **Alert Checker**: Runs every 60s, checking un-triggered price target triggers against live rates and dispatching notifications.
- **Volatility Monitor**: Runs every 5 min, comparing current prices against 1-hour snapshots and notifying users of $\\ge 3\\%$ price movements.

## 3. Ephemeral UI Service (\`ephemeral_service.py\`)
- Manages auto-deleting menu messages in group chats after configurable timeouts (60–300s).

## 4. Analytics & Digest Services (\`analytics_reporter.py\` / \`digest_service.py\`)
- **Analytics**: Calculates active user metrics, conversion volume, and community statistics.
- **Weekly Digest**: Computes 7-day portfolio performance and broadcasts weekly summary reports on Sundays at 10:00 UTC.

## 5. Automated Backups (\`backup.py\`)
- Runs daily at 03:00 UTC, exporting MongoDB collections into compressed \`.gz\` archives and retaining 7 rolling backups.`
  },
  "i18n": {
    "title": "Localization (i18n)",
    "icon": "🌍",
    "category": "Core Design",
    "content": `# Internationalization (i18n)

Finances features a custom lightweight, JSON-backed localization engine located in \`app/i18n.py\`. It requires zero heavy external dependencies.

## Core Features

- **Dot-Notation Key Resolution**: Resolves nested JSON keys (e.g. \`keyboard.settings.bot\` or \`group_settings.title\`).
- **Automatic Fallback**: If a translation key is missing in a target language (e.g., \`fr\`), it automatically falls back to English (\`en\`).
- **Dynamic Formatting**: Injects variables into translation templates using Python \`.format(**kwargs)\`.
- **Supported Languages**: English (\`en\`), Ukrainian (\`uk\`), Polish (\`pl\`), Czech (\`cs\`), Slovak (\`sk\`), German (\`de\`), French (\`fr\`).

## Adding a New Language

1. Add the new language code (e.g., \`"es"\`) to \`settings.json\`.
2. Create \`locales/es.json\` based on \`locales/en.json\`.
3. Push to \`main\`. GitHub Actions (\`locales.yml\`) automatically validates JSON key completeness.`
  },
  "database": {
    "title": "Database Schema",
    "icon": "🗄️",
    "category": "Storage",
    "content": `# Database Schema (MongoDB & Motor)

The bot utilizes MongoDB accessed via the asynchronous **Motor** driver (\`motor.motor_asyncio\`).

## Collections Overview

1. **\`Users\`**: Telegram user profiles, preferences, active watchlists, base currency, UI layout toggles, and portfolio asset lots.
2. **\`Groups\`**: Registered Telegram supergroups, listening currencies, conversion target currencies, custom language overrides, and ephemeral UI settings.
3. **\`Communities\`**: Bot API 10.2 Community entities mapping supergroups and channels into parent groups.
4. **\`Alerts\`**: Price alert triggers (\`currency_from\`, \`currency_to\`, \`target_price\`, \`condition\`, \`triggered\`).
5. **\`fiat_rates\`**: Live exchange rate matrices updated hourly by \`fiat_parser.py\`.
6. **\`current_prices\`**: Flat caching collection for instant USD valuations across crypto and stock tickers.
7. **\`price_history\`**: Snapshots recorded for 5-minute volatility alerts and 7-day weekly digests.
8. **\`ApiKeys\`**: Encrypted exchange secret storage (Fernet cipher).
9. **\`Status\` & \`ProblematicSources\`**: Global singleton status and API crawler failure tracking.`
  },
  "admin_panel": {
    "title": "Admin Panel & Group Mgmt",
    "icon": "🛠️",
    "category": "Administration",
    "content": `# Admin Panel & Group Management

The interactive Admin Panel (\`/admin\`) provides system administrators and group chat owners with live management tools and server diagnostics.

## 🔐 System Admin Features (\`/admin\`)

- **System & Group Analytics**: Displays total active users, active group count, DB footprint, and API error metrics.
- **Parser Controls**: Force instant parser refresh, inspect failing external sources, or clear error logs.
- **Group & Community Management**: Inspect active supergroups, link chats to Bot API 10.2 Communities, or deactivate inactive groups.
- **CSV Data Exports**: Download full CSV dumps of \`Users\` and \`Groups\` collections securely inside Telegram.
- **Maintenance Mode**: Toggle maintenance state to block public commands during updates.
- **Mass Broadcast (\`/broadcast\`)**: Send formatted HTML announcements to all bot users with rate limiting (25 msg/sec).

## 🎛️ Group Administration (\`/group_settings\`)

- **Listening & Target Currencies**: Configure which currencies trigger auto-conversion in group chat messages.
- **Language Override**: Set specific language for the group chat independently of individual user settings.
- **Ephemeral Timer**: Configure auto-delete duration (60–300s) for bot responses.`
  },
  "background_tasks": {
    "title": "Background Tasks",
    "icon": "🔄",
    "category": "Core Logic",
    "content": `# Background Tasks

All background jobs run concurrently inside Python's \`asyncio\` event loop without external task runners like Celery or Redis.

| Task | File | Interval / Schedule | Description |
|------|------|--------------------|-------------|
| **Central Parser** | \`parser_service.py\` | Hourly / 3-Hour | Scrapes fiat rates and updates crypto/stock prices. |
| **Alert Checker** | \`alert_service.py\` | 60 seconds | Evaluates user target price alerts against current rates. |
| **Volatility Monitor** | \`alert_service.py\` | 5 minutes | Detects sudden price swings $\\ge 3\\%$ and alerts portfolio holders. |
| **Weekly Digest** | \`digest_service.py\` | Sundays @ 10:00 UTC | Generates 7-day P&L portfolio performance reports. |
| **Ephemeral Cleanup** | \`ephemeral_service.py\` | Event-triggered | Deletes temporary group menu messages after timeout. |
| **Database Backup** | \`backup.py\` | Daily @ 03:00 UTC | Creates compressed \`.gz\` MongoDB collection backups. |`
  },
  "api_reference": {
    "title": "External API Reference",
    "icon": "🌐",
    "category": "Integrations",
    "content": `# External API Reference

The bot integrates with several external financial market sources and Telegram Bot API features.

## 1. Telegram Bot API 10.x Features
- **Guest Queries (\`answerGuestQuery\`)**: Handles mentions of \`@bot\` in chats where the bot is not a member via \`InlineQueryResultArticle\`.
- **Communities (Bot API 10.2)**: Maps groups into parent community structures in MongoDB.

## 2. Market Data Providers
- **fx-rate.net**: Web scraped via \`curl_cffi\` using Chrome 120 browser impersonation to bypass Cloudflare protection.
- **CoinMarketCap API**: Async HTTP requests (\`aiohttp\`) fetching top cryptocurrency listings.
- **Yahoo Finance**: Wrapped via \`yfinance\` inside \`asyncio.to_thread\` to prevent blocking the async loop.

## 3. Exchange Synchronization
- **Binance**: HMAC-SHA256 signed API requests fetching user wallet balances.
- **Bybit**: V5 Unified Trading Account API integration using secret HMAC authentication.`
  },
  "ci_cd": {
    "title": "CI/CD & Workflows",
    "icon": "🚀",
    "category": "DevOps",
    "content": `# CI/CD Pipeline & Workflows

The repository uses **GitHub Actions** (\`.github/workflows/\`) for automated testing, linting, translation validation, vulnerability scanning, and production deployment.

## Active Workflows

1. **\`ci.yml\`**: Runs \`ruff\` linter and formatter checks on all pull requests.
2. **\`locales.yml\`**: Validates JSON syntax and schema key parity between \`en.json\` and all translation files.
3. **\`security.yml\`**: Runs \`pip-audit\` to scan Python dependencies for CVEs.
4. **\`health.yml\`**: Connects via SSH every 30 minutes to verify \`finances-bot.service\` is running.
5. **\`deploy.yml\`**: Deploys to Oracle VPS on pushes to \`main\` with automatic rollback if the service fails health check.
6. **\`deploy-pages.yml\`**: Automatically publishes this mini-website to GitHub Pages.`
  },
  "devops": {
    "title": "DevOps & Server Guide",
    "icon": "🖥️",
    "category": "DevOps",
    "content": `# DevOps & Server Operations Guide

Complete operations reference for managing the production \`finances-bot.service\` on Linux servers.

## Quick Management Commands

\`\`\`bash
# Service Control
sudo systemctl start finances-bot
sudo systemctl stop finances-bot
sudo systemctl restart finances-bot
sudo systemctl status finances-bot

# Real-Time Logs
sudo journalctl -u finances-bot.service -f --output=short-iso

# Filter Errors Only
sudo journalctl -u finances-bot.service -f -p err

# Reload systemd unit changes
sudo systemctl daemon-reload
sudo systemctl restart finances-bot
\`\`\`

## System Requirements
- Python 3.12+
- MongoDB 6.0+
- systemd system manager`
  }
};
