[← Повернутися до змісту](README.md)

# Модулі

Кодова база `teferdet/finances` логічно організована в модулі, розділяючи конфігурації, репозиторії, бізнес-сервіси, утиліти та обробники презентаційного шару.

## Структура директорій

```
app/
├── __main__.py          # Точка входу та оркестрація фонових задач
├── bot.py               # Aiogram диспетчер, middleware та реєстрація роутерів
├── cache.py             # Асинхронний in-memory TTL-кеш
├── config.py            # Типізовані dataclass-и конфігурації з JSON
├── db.py                # Асинхронне з'єднання з MongoDB через Motor
├── debug_cli.py         # Debug CLI інструменти для ручного тестування
├── i18n.py              # Кастомний JSON-завантажувач інтернаціоналізації
├── logger.py            # Централізоване структуроване логування
├── redis_client.py      # Опціональний Redis-клієнт з fallback на MemoryCache
├── state.py             # Визначення FSM-станів
├── handlers/            # Обробники повідомлень, callback-ів та guest-запитів Telegram
├── keyboards/           # Генератори inline, group admin та reply розміток
├── middlewares/         # Middleware-перехоплювачі (auth, i18n, rate-limit, throttle, group cooldown, error)
├── repositories/        # Шар доступу до БД (groups, communities)
├── services/            # Фонові задачі, центральний парсер, аналітика, безпека, портфель
└── utils/               # Допоміжні модулі (обробка тексту, перевірка адмінів, ephemeral UI, sparkline, draft)

dashboard/
├── API/                 # .NET 8 REST API бекенд
│   ├── Controllers/     # AuthController, StatsController, ConfigController, ActionsController, HealthController
│   ├── Services/        # AuthService, StatsService, ConfigService
│   ├── Repositories/    # MongoContext (singleton бази даних)
│   └── Models/          # Entities, Requests, Responses DTO
├── frontend/            # React 18 + MUI 9 SPA (Vite збірка)
│   ├── src/
│   │   ├── api/         # Типізований API-клієнт
│   │   ├── components/  # auth/, layout/, pages/, ui/
│   │   └── lib/         # Утилітні функції
│   └── nginx.conf       # NGINX конфіг для production
└── nginx/               # Production NGINX reverse proxy конфіг
```

## Основні модулі

### `app.config`
Надає строго типізоване представлення конфігурацій проєкту через Python `dataclasses`.
- `get_settings()`: Читає `config/settings.json` та парсить у `Settings`. Кешує результат, але перезавантажує при зміні часу модифікації файлу. Підтримує 11 типізованих секцій: `BotSettings`, `DatabaseSettings`, `ApiKeysSettings`, `UrlsSettings`, `I18nSettings`, `ParserSettings`, `SecuritySettings`, `FeaturesSettings`, `DraftSettings`, `RedisSettings`, `SentrySettings`.
- `get_currencies_data()`: Читає `config/currencies_data.json` для маппінгу коду валюти → емодзі.
- `save_settings()`: Серіалізує об'єкт `Settings` назад у `settings.json` (використовується при адмін-змінах конфігурації).

### `app.db`
Обробляє асинхронні операції MongoDB через `motor`.
- `init_db(uri, db_name)`: Ініціалізує з'єднання з БД, пули та створює індекси через `ensure_indexes()`.
- `get_db()`: Повертає ініціалізований екземпляр `AsyncIOMotorDatabase`.
- `get_fiat_collection_name()`: Повертає правильну fiat-колекцію, додаючи `_debug` у debug-режимі.

### `app.redis_client`
Опціональна інтеграція Redis з прозорим fallback.
- `init_redis()`: Підключається до Redis через `redis.asyncio`, якщо `settings.redis.url` сконфігуровано. Тихо переходить на `MemoryCache`, якщо Redis недоступний або пакет не встановлено.
- `redis_get(key)`, `redis_set(key, value, ttl)`, `redis_delete(key)`: Асинхронні операції, що працюють як з Redis, так і з in-memory кешем.

### `app.repositories`
Інкапсулює читання та оновлення БД для сутностей груп і спільнот:
- `groups.py`: CRUD-операції для групових чатів, перевизначення налаштувань, перемикання статусу активності та лічильники використання.
- `communities.py`: Керує маппінгами Telegram Bot API 10.2 Community, пов'язуючи групи з батьківськими організаційними сутностями.

### `app.i18n`
Забезпечує багатомовну підтримку, завантажуючи рядкові константи з JSON-файлів у `locales/`.
- `I18n`: Singleton-клас з методом `get()` для динамічного отримання рядків, розв'язання вкладених ключів та форматування параметрів. Fallback на англійську (`en`), якщо ключ не знайдено в цільовій мові.
- **Підтримувані мови**: `en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`.

### `app.middlewares`
Перехоплювачі життєвого циклу, що виконуються перед диспетчеризацією обробника:
- `i18n.py`: Впроваджує локаль та екземпляри `I18n` на основі вподобань користувача або групи.
- `rate_limit.py`: Rate limiter з ковзним вікном — відстежує кількість запитів по користувачах у налаштовуваному вікні. Admin ID звільнені.
- `throttle.py`: Простий per-user rate limiter з відстеженням хітів в пам'яті.
- `group_cooldown.py`: Примусові інтервали cooldown між відповідями конвертації в групах.
- `error.py`: Перехоплює необроблені винятки обробників і логує структуровану діагностику.

### `app.utils`
Допоміжні модулі:
- `text_processing.py`: `TextProcessing` забезпечує надійний парсер з підтримкою різних систем числення, аліасів валют та потоків конвертації. `TextValidator` надає логіку санітизації та вилучення команд.
- `draft.py`: Система анімації `sendMessageDraft` — анімує текст у полі вводу користувача під час обробки запитів. Використовує недокументований метод Telegram Bot API.
- `ephemeral.py`: Хелпери для автовидалення тимчасових повідомлень.
- `chat_admin.py`: Хелпери для перевірки адмінів чату (`is_chat_admin()`).
- `sparkline.py`: Генератор спарклайнів з Unicode block-символів для візуалізації цінових трендів у повідомленнях Telegram.

### `app.keyboards`
Функції-конструктори для UI-елементів:
- `inline.py`: Логіка пагінації (`paginated_currency_keyboard`) та меню налаштувань.
- `admin_groups.py`: Клавіатури управління адмін-групами.
- `group_admin.py`: Генерує меню налаштувань груп (`/group_settings`), вибір мови та діалоги деактивації.
- `main.py`: Генерує динамічні reply-клавіатури, перемикаючи розмір кнопок залежно від `BigButtons` та умовно показуючи преміум-опції або mini-apps.

---

*Останнє оновлення: 2026-08-19*
