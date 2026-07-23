/**
 * Finances Telegram Bot - Documentation Dataset
 * Contains metadata for documentation. Content is dynamically fetched from GitHub.
 */

window.DOCS_DATA = {
  "readme": {
    "title": "Home / Overview",
    "icon": "🏠",
    "category": "Getting Started",
    "file": "README.md",
    "content": "# 📊 Finances Telegram Bot\n\n**Finances** is a comprehensive, open-source personal financial assistant for Telegram. Built on async Python 3.12+, it provides real-time fiat, crypto, and stock tracking, portfolio management, and advanced administrative capabilities directly via the Telegram interface.\n\n---\n\n## 🌟 Key Highlights\n\n* **Administration Without Redeploy**: Fully control your bot via the interactive `/admin` panel. Change parsing intervals, toggle features, or restart the bot directly inside Telegram.\n* **Built-in Observability**: Real-time server diagnostics (CPU, RAM), database footprint tracking, and in-app error log viewing.\n* **i18n-First Architecture**: Custom-built, deeply integrated localization engine supporting nested JSON keys and seamless language switching.\n* **Secure by Design**: Double-check authorization on sensitive actions, encrypted API secrets (Fernet cipher), and flood control.\n\n---\n\n## ✨ Features Breakdown\n\n### 💱 Core Capabilities\n* **Async & High Performance**: Built on `aiogram` 3.x and `motor` for asynchronous MongoDB operations.\n* **Background Parser**: Custom `curl_cffi` based parser fetching live rates with Cloudflare anti-bot bypass.\n* **Price Alerts & Volatility Monitor**: Set specific targets or track portfolio volatility with background schedulers.\n* **Localization System**: Fully localized interface supporting multiple languages (`en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`).\n* **Bot API 10.x Guest Mode**: Evaluates mentions of `@bot` in non-member group chats cleanly.\n\n### 🔐 Admin Panel Modules (`/admin`)\n| Module | Description |\n|--------|-------------|\n| **Analytics & Statistics** | Monitor daily/weekly active users, total lifetime requests, and parser cycles. |\n| **System Configuration** | Manage parser auto-updater state, update intervals, and core currencies on the fly. |\n| **Server Diagnostics** | View real-time RAM allocation, CPU load, and database storage footprint. |\n| **Error Logs** | Read recent incidents directly in Telegram, export full `.log` files, or purge logs. |\n| **Mass Broadcast** | Push formatted HTML announcements to all registered bot users with rate limiting. |\n| **Restart Bot** | Interactive 2-step restart sequence directly from Telegram, persisting state across reboots. |\n\n---\n\n## 🚀 Tech Stack\n\n* **Framework**: `aiogram` (v3.x) - Asynchronous Telegram Bot API wrapper.\n* **Database**: `motor` (MongoDB async driver).\n* **Networking**: `curl_cffi` (advanced anti-bot bypass) & `aiohttp`.\n* **Data Sources**: `yfinance`, `beautifulsoup4`, `pandas`, CoinMarketCap.\n* **Monitoring**: `psutil` for system diagnostics.\n\n---\n\n## 📂 Project Structure\n\n```text\nfinances-dev/\n├── app/\n│   ├── handlers/        # Message, callback, and admin routers\n│   ├── keyboards/       # Inline & Reply UI builders\n│   ├── services/        # Background parsers, alerts, exports\n│   ├── utils/           # Helper functions and text processing\n│   ├── bot.py           # Bot instance & dispatcher setup\n│   ├── config.py        # Configuration models\n│   ├── db.py            # MongoDB connection & indexes\n│   ├── i18n.py          # Custom localization engine\n│   ├── logger.py        # Centralized logging configuration\n│   └── __main__.py      # App entry point\n├── locales/             # JSON translation files (en.json, uk.json, etc.)\n├── config/              # Configuration files (settings.json)\n├── logs/                # Local log storage\n└── requirements.txt     # Python dependencies\n```\n\n---\n\n## 📄 License\nThis project is open-source and available under the **MIT License**."
  },
  "setup": {
    "title": "Setup Guide",
    "icon": "⚙️",
    "category": "Getting Started",
    "file": "setup.md"
  },
  "configuration": {
    "title": "Configuration",
    "icon": "🎛️",
    "category": "Getting Started",
    "file": "configuration.md"
  },
  "faq": {
    "title": "FAQ & Troubleshooting",
    "icon": "❓",
    "category": "Support",
    "file": "faq-troubleshooting.md"
  },
  "architecture": {
    "title": "Architecture Overview",
    "icon": "🏛️",
    "category": "Core Design",
    "file": "ARCHITECTURE.md"
  },
  "modules": {
    "title": "Modules Reference",
    "icon": "📦",
    "category": "Core Design",
    "file": "MODULES.md"
  },
  "handlers": {
    "title": "Handlers & Routers",
    "icon": "🎛️",
    "category": "Architecture",
    "file": "HANDLERS.md"
  },
  "services": {
    "title": "Services & Parser",
    "icon": "⚙️",
    "category": "Core Logic",
    "file": "SERVICES.md"
  },
  "i18n": {
    "title": "Localization (i18n)",
    "icon": "🌍",
    "category": "Core Design",
    "file": "I18N.md"
  },
  "db": {
    "title": "Database Schema",
    "icon": "🗄️",
    "category": "Storage",
    "file": "DATABASE.md"
  },
  "admin": {
    "title": "Admin Panel & Group Mgmt",
    "icon": "🛠️",
    "category": "Administration",
    "file": "ADMIN_PANEL.md"
  },
  "background": {
    "title": "Background Tasks",
    "icon": "🔄",
    "category": "Core Logic",
    "file": "BACKGROUND_TASKS.md"
  },
  "api": {
    "title": "External API Reference",
    "icon": "🌐",
    "category": "Integrations",
    "file": "API_REFERENCE.md"
  },
  "cicd": {
    "title": "CI/CD & Workflows",
    "icon": "🚀",
    "category": "DevOps",
    "file": "CI_CD.md"
  },
  "devops": {
    "title": "DevOps & Server Guide",
    "icon": "🖥️",
    "category": "DevOps",
    "file": "DEVOPS.md"
  }
};
