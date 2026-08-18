# 📚 Finances Documentation

Welcome to the comprehensive technical documentation for the Finances project — an asynchronous Telegram bot with an integrated web admin dashboard.

## Bot Core

- **[Architecture](ARCHITECTURE.md)**: System overview, data flow, parsing engine, and background schedulers.
- **[Modules](MODULES.md)**: Directory structure and core modules reference.
- **[Handlers](HANDLERS.md)**: Detailed breakdown of all Telegram command and callback handlers.
- **[Services](SERVICES.md)**: Background tasks, data parsers, and business logic services.
- **[Database](DATABASE.md)**: MongoDB collections, indexes, and document structures.
- **[I18N](I18N.md)**: Custom JSON-based localization engine.
- **[Admin Panel](ADMIN_PANEL.md)**: In-app `/admin` modules, access control, and broadcast system.
- **[Background Tasks](BACKGROUND_TASKS.md)**: Parser, alerts, volatility, digest, and backup loops.
- **[API Reference](API_REFERENCE.md)**: External APIs — Telegram, CoinMarketCap, Yahoo Finance, fx-rate.net, Binance, Bybit.

## Dashboard

- **[Dashboard Overview](DASHBOARD.md)**: Architecture, components, authentication flow, and deployment of the web admin panel.
- **[Dashboard API](DASHBOARD_API.md)**: REST API reference — .NET 8 backend endpoints, models, and authentication.
- **[Dashboard Frontend](DASHBOARD_FRONTEND.md)**: React + MUI frontend — pages, components, API client, and build system.

## Operations

- **[CI/CD](CI_CD.md)**: GitHub Actions workflows — linting, security, health monitoring, and deployment.
- **[DevOps](DEVOPS.md)**: Server operations guide — Docker and legacy systemd deployments, logs, backups, and monitoring.

---

*Last updated: 2026-08-19*
