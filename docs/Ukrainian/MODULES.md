[← Повернутися до змісту](README.md)

# Модулі

Кодова база `teferdet/finances` логічно організована в модулі, розділяючи CQRS-проєкції, конфігурації, репозиторії, бізнес-сервіси, утиліти та обробники презентаційного шару.

## Структура директорій

```text
app/
├── __main__.py          # Точка входу та оркестрація контрольованих фонових задач
├── bot.py               # Aiogram диспетчер, middleware та реєстрація роутерів
├── cache.py             # Асинхронний in-memory TTL-кеш (L1)
├── config.py            # Типізовані dataclass-и конфігурації з JSON
├── db.py                # Асинхронне з'єднання з MongoDB через Motor + CQRS-обгортка
├── debug_cli.py         # Debug CLI інструменти для ручного тестування
├── health.py            # Перевірка стану контейнера (heartbeat у Redis, пінг MongoDB, статус тасок)
├── i18n.py              # Кастомний JSON-завантажувач інтернаціоналізації
├── logger.py            # Централізоване структуроване логування
├── redis_client.py      # Дворівневий L1/L2 Redis-кеш із fallback на MemoryCache
├── state.py             # Визначення FSM-станів та динамічних адмінів
├── cqrs/                # Шина подій, перехоплювач БД, read-проєкції та write-behind буфер
│   ├── bus.py           # Внутрішня асинхронна шина подій
│   ├── events.py        # Доменні події (UserConfigChangedEvent, PortfolioChangedEvent, RatesUpdatedEvent)
│   ├── interceptor.py   # Обгортки InterceptedDatabase / InterceptedCollection
│   ├── tasks.py         # TaskSupervisor для відмовостійких фонових воркерів
│   ├── read/            # Read-моделі (fiat.py, prices.py, users.py)
│   └── write/           # Write-behind буфер активності (activity.py)
├── handlers/            # Обробники повідомлень, callback-ів, груп, inline та адмін-панелі
├── keyboards/           # Генератори inline, group admin та reply розміток
├── middlewares/         # Middleware-перехоплювачі (error, rate-limit, throttle, group cooldown, i18n)
├── repositories/        # Шар доступу до БД (groups, communities)
├── services/            # Фонові задачі, центральний парсер, аналітика, безпека, портфель, бекапи
└── utils/               # Допоміжні модулі (обробка тексту, resilience, перевірка адмінів, ephemeral UI, sparkline, draft)
```

## Основні модулі

### `app.cqrs`
Реалізує паттерн CQRS (Command Query Responsibility Segregation) та подієву синхронізацію:
- `bus.py` та `events.py`: Асинхронна шина подій (`UserConfigChangedEvent`, `PortfolioChangedEvent`, `RatesUpdatedEvent`).
- `interceptor.py`: Обгортає `AsyncIOMotorDatabase` (`InterceptedDatabase`), завдяки чому читання `fiat_rates` виконуються з оперативної пам'яті (`fiat_store`), а модифікації `Users` або `fiat_rates` автоматично публікують події інвалідації/оновлення кешу.
- `read/fiat.py` (`fiat_store`), `read/prices.py` (`price_store`), `read/users.py` (`get_user_view`): Швидкі in-memory проєкції для курсів валют, цін крипти/акцій та налаштувань користувача.
- `write/activity.py` (`activity_buffer`): Буферизує оновлення `last_active` і `total_requests` у пам'яті та скидає їх у MongoDB раз на 15 секунд.
- `tasks.py` (`supervisor`): Контролює фонові `asyncio.Task` воркери з автоматичним відновленням після збоїв.

### `app.health`
Модуль перевірки здоров'я контейнера (`python -m app.health`):
- Перевіряє свіжість ключа `health:heartbeat` у Redis (оновлюється кожні 15с основним циклом бота) для виявлення зависань event loop.
- Виконує пінг MongoDB (`db.command("ping")`) і перевіряє стан фонових задач у `TaskSupervisor`.

### `app.config`
Надає строго типізоване представлення конфігурацій проєкту через Python `dataclasses`.
- `get_settings()`: Читає `config/settings.json` та парсить у `Settings`. Кешує результат і автоматично перезавантажує при зміні часу модифікації файлу.
- `get_currencies_data()`: Читає `config/currencies_data.json` для маппінгу коду валюти → емодзі та символ.
- `save_settings()`: Серіалізує об'єкт `Settings` назад у `settings.json` (використовується при змінах у `/admin`).

### `app.db`
Обробляє асинхронні операції MongoDB через `motor`.
- `init_db(uri, db_name)`: Ініціалізує з'єднання з БД, пули та створює індекси через `ensure_indexes()`.
- `get_db()`: Повертає CQRS-обгорнутий екземпляр `InterceptedDatabase` (`get_raw_db()` повертає прямий `AsyncIOMotorDatabase`).
- `get_fiat_collection_name()`: Повертає активну fiat-колекцію (`fiat_rates` або `fiat_rates_dev`).

### `app.redis_client`
Дворівневе кешування L1/L2 (`TwoTierCache`) з прозорим fallback:
- Поєднує локальний L1 `MemoryCache` (~0мс затримки) з опціональним L2 Redis-бекендом (`redis.asyncio`).
- `init_redis()`: Підключається до Redis, якщо задано `settings.redis.url`; автоматично працює через L1 `MemoryCache`, якщо Redis недоступний.

### `app.repositories`
Інкапсулює читання та оновлення БД для сутностей груп і спільнот:
- `groups.py`: CRUD-операції для групових чатів (колекція `groups`), налаштування груп, перемикання активності та лічильники конвертацій.
- `communities.py`: Керує прив'язкою груп до спільнот.

### `app.i18n`
Забезпечує багатомовну підтримку, завантажуючи рядкові константи з JSON-файлів у `locales/`.
- `I18n`: Singleton-клас з методом `get()` для динамічного отримання рядків із fallback на англійську (`en`).
- **Підтримувані мови**: `en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`.

### `app.middlewares`
Перехоплювачі життєвого циклу, що виконуються перед диспетчеризацією обробника:
- `i18n.py`: Завантажує `UserView` користувача, буферизує активність через `activity_buffer` та впроваджує `lang` і `I18n`.
- `rate_limit.py` та `throttle.py`: Обмежувачі частоти запитів (Admin ID звільнені).
- `group_cooldown.py`: Інтервали cooldown між відповідями бота в групах.
- `error.py`: Перехоплює необроблені винятки обробників і логує структуровану діагностику.

### `app.utils`
Допоміжні модулі:
- `text_processing.py`: `TextProcessing` забезпечує парсинг сум, множників (`k`, `m`, `тис`), символів і сленгу валют та запитів конвертації. `TextValidator` відповідає за санітизацію вводу.
- `resilience.py`: `CircuitBreaker` та декоратор `@retry_transient` для зовнішніх HTTP-запитів.
- `draft.py`: Анімація `sendMessageDraft` під час обробки тривалих запитів.
- `ephemeral.py`: Хелпери для тимчасових повідомлень у групах.
- `chat_admin.py`: Перевірка прав адміністратора в чаті (`is_chat_admin()`).
- `sparkline.py`: Генератор текстових спарклайн-графіків з Unicode-блоків.

---

*Останнє оновлення: 2026-11-09*
