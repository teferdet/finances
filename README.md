# 📊 Finances Telegram Bot

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/aiogram-3.x-green.svg" alt="Aiogram Version">
  <img src="https://img.shields.io/badge/MongoDB-Powered-brightgreen.svg" alt="Database">
  <img src="https://img.shields.io/badge/Redis-L1%2FL2%20Cache-red.svg" alt="Redis Cache">
  <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License">
</div>

<br>

**Finances** is a comprehensive, open-source personal financial assistant for Telegram. Built on async Python (`aiogram` 3.x), it provides real-time fiat, crypto, and stock tracking, portfolio management with Binance/Bybit API sync, price & volatility alerts, and full administrative control directly via the Telegram interface.

## 🌟 Why Use Finances?
* **CQRS In-Memory Read/Write Architecture**: Ultra-low latency lookups via in-memory read projections (`FiatSnapshot`, `PriceSnapshot`, `UserView`), write-behind activity buffering (`UserActivityBuffer`), and a two-tier L1 (RAM) + L2 (Redis) cache (`TwoTierCache`).
* **Administration Without Redeploy**: Fully control your bot via the interactive `/admin` panel. Change parsing intervals, toggle features, manage groups, trigger backups, or inspect background workers without touching the server.
* **Built-in Observability & Healthchecks**: Real-time server diagnostics (CPU, RAM), supervised background workers (`TaskSupervisor`), database footprint tracking, in-app error log viewing, and a dedicated container healthcheck (`python -m app.health`).
* **i18n-First Architecture**: Custom-built, deeply integrated localization engine supporting 7 languages (`en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`) with nested JSON keys and seamless switching.
* **Secure by Design**: Fernet-encrypted exchange API keys, audited admin privilege management, HTML-sanitized broadcasts, and strict non-root Docker execution.

---

## ✨ Features

### 💱 Core Capabilities
* **Async & High Performance**: Built on `aiogram` 3.x and `motor` for asynchronous MongoDB operations with CQRS interception.
* **Live Currency, Crypto & Stock Rates**: Instant fiat/crypto conversions (including direct `BTC`/`ETH` to fiat conversion), CoinMarketCap & Yahoo Finance tracking, and natural-language amount parsing (`100$`, `2.5 btc to eur`, `5k грн`).
* **Portfolio & Exchange Sync**: Track crypto, stock, and fiat holdings with P&L calculations, sparklines, CSV import/export, and read-only Binance/Bybit API synchronization.
* **Price Alerts & Volatility Monitor**: Set target price alerts (`/alert`) or track portfolio volatility (`1%`–`50%`) with background schedulers and weekly portfolio digests.
* **Group & Inline Mode**: Automatic or `/rate`-triggered currency conversions in Telegram groups with per-group admin settings (`/group_settings`) and inline queries.

### 🔐 Admin Panel Modules (`/admin`)
| Module | Description |
|--------|-------------|
| **Analytics & Statistics Dashboard** | Monitor daily/weekly/monthly active users (DAU/WAU/MAU), total lifetime requests, parser cycles, and export CSV/Markdown reports. |
| **Database & Backups** | Inspect collection sizes, trigger low-memory streaming `.json.gz` backups on demand, or download the latest archive directly in Telegram. |
| **System Configuration & Features** | Manage parser auto-updater state, update intervals, group/inline/mini-app feature flags, and draft loading thresholds on the fly. |
| **Tasks & CQRS Status** | Inspect supervised background workers, uptime, restart counters, CQRS event bus metrics, and write-behind buffer stats. |
| **Server Diagnostics & Error Logs** | View real-time bot RAM allocation, system RAM, CPU load, problematic data sources, and recent error logs. |
| **Mass Message Broadcast** | Push HTML-sanitized announcements to all users or specific language segments with a 5-minute safety delay and abort button. |

---

## 🚀 Tech Stack

* **Framework**: `aiogram` (v3.x) — Asynchronous Telegram Bot API wrapper.
* **Database & Cache**: `motor` (MongoDB async driver) + `redis` (`TwoTierCache` L1 in-memory + L2 Redis with automatic fallback).
* **Networking & Parsing**: `curl_cffi` (TLS/JA3 browser impersonation), `aiohttp`, `yfinance`, `beautifulsoup4`, `pandas`.
* **Security & Monitoring**: `cryptography` (Fernet encryption), `psutil` (system diagnostics), `app.health` (container healthcheck).

---

## 📂 Project Structure

```text
finances/
├── app/
│   ├── cqrs/            # Event bus, DB interceptor, read projections & write-behind buffer
│   ├── handlers/        # Message, callback, group, inline, and admin routers
│   ├── keyboards/       # Inline, group admin, and Reply UI builders
│   ├── middlewares/     # Error, rate-limit, throttle, group cooldown, and i18n interceptors
│   ├── repositories/    # Data access layer for groups and communities
│   ├── services/        # Background parsers, alerts, portfolio, digest, backups, security
│   ├── utils/           # Text processing, resilience (circuit breaker), sparklines, ephemeral UI
│   ├── bot.py           # Bot instance & dispatcher setup
│   ├── cache.py         # Asynchronous in-memory TTL cache (L1)
│   ├── config.py        # Typed configuration dataclasses
│   ├── db.py            # MongoDB connection & indexes
│   ├── health.py        # Container healthcheck (Redis heartbeat, MongoDB ping, supervisor check)
│   ├── i18n.py          # Custom localization engine
│   ├── logger.py        # Centralized logging configuration
│   ├── redis_client.py  # Two-tier L1/L2 Redis cache client with transparent fallback
│   └── __main__.py      # App entry point & background task orchestration
├── locales/             # JSON translation files (en, uk, pl, cs, sk, de, fr)
├── config/              # Configuration & currency metadata files
├── docker/              # Container entrypoint scripts
└── requirements.txt     # Python dependencies
```

---

## 📚 Documentation

Complete documentation is available in English and Ukrainian in the [`docs/`](docs/README.md) directory:

* **[Quick Start & Setup Guide](setup.md)** ([EN](docs/English/setup.md))
* **[Architecture](docs/English/ARCHITECTURE.md)** ([UA](docs/Ukrainian/ARCHITECTURE.md)): CQRS layer, data flow, parsing engine, and background schedulers.
* **[Modules Reference](docs/English/MODULES.md)** ([UA](docs/Ukrainian/MODULES.md)): Directory structure and core module breakdown.
* **[Handlers](docs/English/HANDLERS.md)** ([UA](docs/Ukrainian/HANDLERS.md)) & **[Services](docs/English/SERVICES.md)** ([UA](docs/Ukrainian/SERVICES.md))
* **[Admin Panel](docs/English/ADMIN_PANEL.md)** ([UA](docs/Ukrainian/ADMIN_PANEL.md)) & **[Background Tasks](docs/English/BACKGROUND_TASKS.md)** ([UA](docs/Ukrainian/BACKGROUND_TASKS.md))
* **[Database Schema](docs/English/DATABASE.md)** ([UA](docs/Ukrainian/DATABASE.md)) & **[Localization (i18n)](docs/English/I18N.md)** ([UA](docs/Ukrainian/I18N.md))
* **[CI/CD](docs/English/CI_CD.md)** ([UA](docs/Ukrainian/CI_CD.md)) & **[DevOps Guide](docs/English/DEVOPS.md)** ([UA](docs/Ukrainian/DEVOPS.md))

For the full index, see the **[Documentation Index](docs/README.md)**.

---

## 🤝 Contributing

Contributions are always welcome! Feel free to open issues or submit Pull Requests for:
- Adding new locales/languages.
- Implementing new parsing sources for stocks or crypto.
- Optimizing database queries and caching.

## 📄 License
This project is free and open-source software licensed under the **[GNU General Public License v3.0 (GPL-3.0)](LICENSE)**.
