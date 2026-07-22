# teferdet/finances - Documentation

Welcome to the internal developer documentation for the `teferdet/finances` Telegram Bot.

This directory contains deep-dive documentation on the system architecture, feature modules, database configuration, background services, and infrastructure.

## Documentation Index

1. 🏛️ **[Architecture Overview](ARCHITECTURE.md)**  
   Learn about the core design, data flow, layer separation (Handlers, Repositories, Services), Telegram Bot API 10.x integration, and `aiogram` stack.

2. 📦 **[Modules](MODULES.md)**  
   A breakdown of the `app/` directory, core modules (`config.py`, `utils/`, `middlewares/`), and repositories (`communities.py`, `groups.py`).

3. 🎛️ **[Handlers](HANDLERS.md)**  
   Detailed list of all bot entry points, commands, routers, and callbacks (including `/group_settings`, `/admin`, guest mode queries, `/portfolio`, `/crypto`).

4. ⚙️ **[Services](SERVICES.md)**  
   The background business logic of the bot: `CentralParserService`, portfolio aggregations, ephemeral messaging, analytics reporting, and exchange synchronization.

5. 🌍 **[Internationalization (I18N)](I18N.md)**  
   How the custom JSON-based translation system works across private and group environments, and instructions for adding new languages.

6. 🗄️ **[Database Structure](DATABASE.md)**  
   Overview of the MongoDB `motor` integration, collection schemas (`Users`, `Groups`, `Communities`, `Alerts`, `price_history`, `current_prices`), and indexes.

7. 🛠️ **[Admin Panel & Group Management](ADMIN_PANEL.md)**  
   Guide to the `/admin` dashboard, group administration system (`/group_settings`), diagnostic tools, maintenance toggles, and global broadcast system.

8. 🔄 **[Background Tasks](BACKGROUND_TASKS.md)**  
   Information on concurrent `asyncio` loops managing central price parsing, volatility alerts, weekly digests, ephemeral message cleanup, and local DB backups.

9. 🌐 **[API Reference](API_REFERENCE.md)**  
   Details on external HTTP integrations (CoinMarketCap, fx-rate.net Cloudflare bypass, Yahoo Finance, Binance/Bybit) and Telegram Bot API 10.x guest queries.

10. 🚀 **[CI/CD & Automation](CI_CD.md)**  
    Overview of GitHub Actions workflows for testing, locale validation, security scanning, health checking, stale management, and automated VPS deployment.

11. 🖥️ **[DevOps — Server Operations](DEVOPS.md)**  
    Full operations reference: systemd service control, real-time log monitoring, resource tracking, backups, manual deployment, rollback procedures, and diagnostic one-liners.

---

*Last updated: 2026-07-22*

