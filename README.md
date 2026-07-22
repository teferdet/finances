# 🌐 Finances Telegram Bot — GitHub Pages Site

This branch contains the standalone static web application for **Finances Telegram Bot** hosted on GitHub Pages.

## 🚀 Live Features
- **Interactive Documentation Browser**: Access all project architecture, API references, database schemas, and DevOps guides.
- **Telegram Bot Simulator**: Interactive playground for testing commands (`/start`, `/admin`, `/group_settings`, `/rates`) and i18n localization.
- **Instant Search Engine**: Client-side full-text search across all documentation (`Ctrl + K`).
- **Dark & Light Mode**: Custom glassmorphism UI with theme toggle.

## 📁 File Structure
```text
.
├── index.html                  # Main Web App HTML5 entry point
├── css/
│   └── styles.css              # Custom Glassmorphism CSS design system
├── js/
│   ├── docs-data.js            # Pre-compiled documentation dataset
│   └── app.js                  # Client-side router & simulator engine
├── .nojekyll                   # GitHub Pages Jekyll bypass flag
└── .github/workflows/
    └── deploy-pages.yml        # GitHub Actions automatic deployment workflow
```
