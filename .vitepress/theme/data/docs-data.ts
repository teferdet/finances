// ============================================================
// Finances Bot Docs — Typed Data Layer
// Migrated from js/docs-data.js
// ============================================================

export type Lang = 'en' | 'uk'

export interface DocEntry {
  title: string
  icon: string
  category: string
  file: string
  content?: string // cached after first fetch
}

export interface UICard {
  icon: string
  title: string
  desc: string
}

export interface UIStrings {
  brandVersion: string
  navHome: string
  navDocs: string
  searchPlaceholder: string
  searchHint: string
  noResults: string
  onThisPage: string
  noSubsections: string
  loadingDoc: string
  errorLoading: string
  copied: string
  copy: string
  btnCopy: string
  heroTitle: string
  heroDesc: string
  btnTelegram: string
  btnDocs: string
  btnGitHub: string
  cards: UICard[]
}

export const UI_STRINGS: Record<Lang, UIStrings> = {
  en: {
    brandVersion: 'v6.6.0',
    navHome: 'Home',
    navDocs: 'Documentation',
    searchPlaceholder: 'Search documentation topics, modules, methods...',
    searchHint: 'Type a query to search documentation...',
    noResults: 'No matching documentation found.',
    onThisPage: 'On this page',
    noSubsections: 'No sub-sections',
    loadingDoc: 'Loading documentation from GitHub...',
    errorLoading: 'Error loading document:',
    copied: 'Copied!',
    copy: '📋 Copy',
    btnCopy: 'Copy',
    heroTitle: '📊 Finances Telegram Bot',
    heroDesc:
      'A comprehensive, open-source personal financial assistant for Telegram with an integrated .NET 8 + React admin dashboard. Real-time fiat, crypto, and stock tracking, portfolio analytics, price alerts, Redis caching, and containerized Docker deployment.',
    btnTelegram: '📱 Open Telegram Bot',
    btnDocs: '📚 Open Documentation',
    btnGitHub: '🐙 GitHub Repository',
    cards: [
      { icon: '🎛️', title: 'No-Redeploy Admin Panel', desc: 'Control parser intervals, inspect CPU/RAM diagnostics, purge logs, or broadcast announcements directly inside Telegram via <code>/admin</code>.' },
      { icon: '📊', title: 'Web Admin Dashboard', desc: 'Modern React 18 + .NET 8 ASP.NET Core web dashboard with Telegram OTP authentication, real-time DAU/WAU/MAU analytics, and live config editor.' },
      { icon: '🛡️', title: 'Cloudflare Bypass Scraper', desc: 'Scrapes live exchange rates using <code>curl_cffi</code> Chrome 120 browser impersonation to bypass anti-bot challenges securely.' },
      { icon: '🌍', title: 'i18n Localization System', desc: 'Custom zero-dependency JSON localization engine supporting dot-notation keys and instant language switching (EN, UK, PL, CS, SK, DE, FR).' },
      { icon: '📈', title: 'Portfolio & Volatility Monitor', desc: 'Track asset lots, aggregate live P&L, and receive background alerts on sudden market swings (≥3%) and weekly Sunday digest reports.' },
      { icon: '🐳', title: 'Docker & Redis Caching', desc: 'Full containerization via Docker Compose (bot, dashboard, frontend, redis) with automated GitHub Actions SSH deployment and healthchecks.' },
    ],
  },
  uk: {
    brandVersion: 'v6.6.0',
    navHome: 'Головна',
    navDocs: 'Документація',
    searchPlaceholder: 'Пошук по темах, модулях, методах...',
    searchHint: 'Введіть запит для пошуку в документації...',
    noResults: 'Нічого не знайдено за вашим запитом.',
    onThisPage: 'На цій сторінці',
    noSubsections: 'Немає підрозділів',
    loadingDoc: 'Завантаження документації з GitHub...',
    errorLoading: 'Помилка завантаження документа:',
    copied: 'Скопійовано!',
    copy: '📋 Скопіювати',
    btnCopy: 'Копіювати',
    heroTitle: '📊 Telegram-бот Finances',
    heroDesc:
      'Повнофункціональний персональний фінансовий асистент для Telegram з інтегрованою веб-панеллю адміністратора на .NET 8 + React. Відстеження фіату, крипти й акцій у реальному часі, аналітика портфеля, цінові алерти, кешування Redis та Docker-деплой.',
    btnTelegram: '📱 Відкрити бота в Telegram',
    btnDocs: '📚 Відкрити документацію',
    btnGitHub: '🐙 Репозиторій GitHub',
    cards: [
      { icon: '🎛️', title: 'Адмін-панель без перезапуску', desc: 'Керуйте інтервалами парсера, переглядайте діагностику CPU/RAM, очищайте логи та робіть розсилки прямо в Telegram через <code>/admin</code>.' },
      { icon: '📊', title: 'Веб-панель адміністратора', desc: 'Сучасний веб-дашборд на React 18 + .NET 8 ASP.NET Core з автентифікацією через Telegram OTP, графіками DAU/WAU/MAU та живим редактором конфігу.' },
      { icon: '🛡️', title: 'Скрапер з обходом Cloudflare', desc: 'Збирає актуальні курси валют з використанням <code>curl_cffi</code> Chrome 120 для безпечного та надійного обходу антибот-захисту.' },
      { icon: '🌍', title: 'Система локалізації i18n', desc: 'Кастомний швидкий JSON-движок локалізації з вкладеними ключами та миттєвим перемиканням 7 мов (EN, UK, PL, CS, SK, DE, FR).' },
      { icon: '📈', title: 'Портфель та монітор волатильності', desc: 'Трекінг лотів активів, розрахунок P&L у реальному часі, фонові сповіщення про різкі стрибки цін (≥3%) та недільні дайджести.' },
      { icon: '🐳', title: 'Docker та кешування Redis', desc: 'Повна контейнеризація через Docker Compose (bot, dashboard, frontend, redis) з автодеплоєм через GitHub Actions та моніторингом.' },
    ],
  },
}

export const DOCS_DATA: Record<Lang, Record<string, DocEntry>> = {
  en: {
    readme:         { title: 'Home / Overview',        icon: '🏠', category: 'Getting Started', file: 'English/README.md' },
    setup:          { title: 'Setup Guide',            icon: '⚙️', category: 'Getting Started', file: 'English/setup.md' },
    configuration:  { title: 'Configuration',          icon: '🎛️', category: 'Getting Started', file: 'English/configuration.md' },
    architecture:   { title: 'Architecture Overview',  icon: '🏛️', category: 'Core Design',     file: 'English/ARCHITECTURE.md' },
    modules:        { title: 'Modules Reference',      icon: '📦', category: 'Core Design',     file: 'English/MODULES.md' },
    i18n:           { title: 'Localization (i18n)',     icon: '🌍', category: 'Core Design',     file: 'English/I18N.md' },
    handlers:       { title: 'Handlers & Routers',     icon: '🎛️', category: 'Bot Core',        file: 'English/HANDLERS.md' },
    services:       { title: 'Services & Parsers',     icon: '⚙️', category: 'Bot Core',        file: 'English/SERVICES.md' },
    background:     { title: 'Background Tasks',       icon: '🔄', category: 'Bot Core',        file: 'English/BACKGROUND_TASKS.md' },
    db:             { title: 'Database Schema',        icon: '🗄️', category: 'Storage',         file: 'English/DATABASE.md' },
    admin:          { title: 'Admin Panel & Groups',   icon: '🛠️', category: 'Administration',  file: 'English/ADMIN_PANEL.md' },
    api:            { title: 'External API Reference', icon: '🌐', category: 'Integrations',    file: 'English/API_REFERENCE.md' },
    dashboard:      { title: 'Dashboard Overview',     icon: '📊', category: 'Web Dashboard',   file: 'English/DASHBOARD.md' },
    dashboard_api:  { title: 'Dashboard REST API',     icon: '🔌', category: 'Web Dashboard',   file: 'English/DASHBOARD_API.md' },
    dashboard_fe:   { title: 'Dashboard Frontend',     icon: '🖥️', category: 'Web Dashboard',   file: 'English/DASHBOARD_FRONTEND.md' },
    cicd:           { title: 'CI/CD & Workflows',      icon: '🚀', category: 'DevOps',          file: 'English/CI_CD.md' },
    devops:         { title: 'DevOps & Server Guide',  icon: '🖥️', category: 'DevOps',          file: 'English/DEVOPS.md' },
    faq:            { title: 'FAQ & Troubleshooting',  icon: '❓', category: 'Support',         file: 'English/faq-troubleshooting.md' },
  },
  uk: {
    readme:         { title: 'Головна / Огляд',        icon: '🏠', category: 'Початок роботи',  file: 'Ukrainian/README.md' },
    architecture:   { title: 'Огляд архітектури',      icon: '🏛️', category: 'Архітектура',     file: 'Ukrainian/ARCHITECTURE.md' },
    modules:        { title: 'Довідник модулів',        icon: '📦', category: 'Архітектура',     file: 'Ukrainian/MODULES.md' },
    i18n:           { title: 'Локалізація (i18n)',      icon: '🌍', category: 'Архітектура',     file: 'Ukrainian/I18N.md' },
    handlers:       { title: 'Обробники та роутери',   icon: '🎛️', category: 'Ядро бота',       file: 'Ukrainian/HANDLERS.md' },
    services:       { title: 'Сервіси та парсери',     icon: '⚙️', category: 'Ядро бота',       file: 'Ukrainian/SERVICES.md' },
    background:     { title: 'Фонові задачі',          icon: '🔄', category: 'Ядро бота',       file: 'Ukrainian/BACKGROUND_TASKS.md' },
    db:             { title: 'Структура бази даних',   icon: '🗄️', category: 'База даних',      file: 'Ukrainian/DATABASE.md' },
    admin:          { title: 'Адмін-панель та групи',  icon: '🛠️', category: 'Адміністрування', file: 'Ukrainian/ADMIN_PANEL.md' },
    api:            { title: 'Довідник зовнішніх API', icon: '🌐', category: 'Інтеграції',      file: 'Ukrainian/API_REFERENCE.md' },
    dashboard:      { title: 'Огляд дашборда',         icon: '📊', category: 'Веб-дашборд',     file: 'Ukrainian/DASHBOARD.md' },
    dashboard_api:  { title: 'API дашборда (.NET 8)',  icon: '🔌', category: 'Веб-дашборд',     file: 'Ukrainian/DASHBOARD_API.md' },
    dashboard_fe:   { title: 'Фронтенд дашборда',      icon: '🖥️', category: 'Веб-дашборд',     file: 'Ukrainian/DASHBOARD_FRONTEND.md' },
    cicd:           { title: 'CI/CD та автоматизація', icon: '🚀', category: 'DevOps',          file: 'Ukrainian/CI_CD.md' },
    devops:         { title: 'DevOps — посібник сервера', icon: '🖥️', category: 'DevOps',       file: 'Ukrainian/DEVOPS.md' },
  },
}
