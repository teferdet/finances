// ============================================================
// Finances Bot Docs — Typed Data Layer
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
    brandVersion: 'v6.8.0',
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
      'A comprehensive, open-source personal financial assistant for Telegram powered by an in-memory CQRS architecture and two-tier L1/L2 Redis cache. Real-time fiat, crypto, and stock tracking, portfolio analytics with Binance/Bybit sync, price alerts, and containerized Docker deployment.',
    btnTelegram: '📱 Open Telegram Bot',
    btnDocs: '📚 Open Documentation',
    btnGitHub: '🐙 GitHub Repository',
    cards: [
      { icon: '🎛️', title: 'No-Redeploy Admin Panel', desc: 'Control parser intervals, inspect CPU/RAM diagnostics, trigger streaming backups, or broadcast announcements directly inside Telegram via <code>/admin</code>.' },
      { icon: '⚡', title: 'CQRS & L1/L2 Redis Cache', desc: 'Ultra-low latency in-memory read models (<code>FiatSnapshot</code>, <code>PriceSnapshot</code>, <code>UserView</code>), write-behind activity buffer, and two-tier L1/L2 Redis caching.' },
      { icon: '🛡️', title: 'Cloudflare Bypass Scraper', desc: 'Scrapes live exchange rates using <code>curl_cffi</code> Chrome TLS/JA3 browser impersonation with CircuitBreaker resilience.' },
      { icon: '🌍', title: 'i18n Localization System', desc: 'Custom zero-dependency JSON localization engine supporting dot-notation keys and instant language switching (EN, UK, PL, CS, SK, DE, FR).' },
      { icon: '📈', title: 'Portfolio & Volatility Monitor', desc: 'Track asset lots, sync Binance/Bybit balances, aggregate live P&L, and receive background alerts on market swings and weekly Sunday digests.' },
      { icon: '🐳', title: 'Docker & Healthcheck', desc: 'Containerized via Docker Compose (bot + redis) with <code>python -m app.health</code> verification, supervised workers, and GitHub Actions SSH deployment.' },
    ],
  },
  uk: {
    brandVersion: 'v6.8.0',
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
      'Повнофункціональний персональний фінансовий асистент для Telegram із CQRS-архітектурою в пам’яті та дворівневим кешем L1/L2 Redis. Відстеження фіату, крипти й акцій у реальному часі, аналітика портфеля із синхронізацією Binance/Bybit, цінові алерти та Docker-деплой.',
    btnTelegram: '📱 Відкрити бота в Telegram',
    btnDocs: '📚 Відкрити документацію',
    btnGitHub: '🐙 Репозиторій GitHub',
    cards: [
      { icon: '🎛️', title: 'Адмін-панель без перезапуску', desc: 'Керуйте інтервалами парсера, переглядайте діагностику CPU/RAM, запускайте бекапи та робіть розсилки прямо в Telegram через <code>/admin</code>.' },
      { icon: '⚡', title: 'CQRS та L1/L2 кеш Redis', desc: 'Миттєві in-memory проєкції (<code>FiatSnapshot</code>, <code>PriceSnapshot</code>, <code>UserView</code>), write-behind буфер активності та дворівневий L1/L2 кеш.' },
      { icon: '🛡️', title: 'Скрапер з обходом Cloudflare', desc: 'Збирає актуальні курси валют з використанням <code>curl_cffi</code> та CircuitBreaker для безпечного й відмовостійкого обходу антибот-захисту.' },
      { icon: '🌍', title: 'Система локалізації i18n', desc: 'Кастомний швидкий JSON-движок локалізації з вкладеними ключами та миттєвим перемиканням 7 мов (EN, UK, PL, CS, SK, DE, FR).' },
      { icon: '📈', title: 'Портфель та монітор волатильності', desc: 'Трекінг активів, синхронізація з Binance/Bybit, розрахунок P&L у реальному часі, сповіщення про стрибки цін та недільні дайджести.' },
      { icon: '🐳', title: 'Docker та Healthcheck', desc: 'Контейнеризація через Docker Compose (bot + redis) із перевіркою стану <code>python -m app.health</code>, супервізором тасок та автодеплоєм через GitHub Actions.' },
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
    cicd:           { title: 'CI/CD та автоматизація', icon: '🚀', category: 'DevOps',          file: 'Ukrainian/CI_CD.md' },
    devops:         { title: 'DevOps — посібник сервера', icon: '🖥️', category: 'DevOps',       file: 'Ukrainian/DEVOPS.md' },
  },
}
