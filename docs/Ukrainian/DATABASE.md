[← Повернутися до змісту](README.md)

# Структура бази даних

Бот `teferdet/finances` використовує **MongoDB** з асинхронним Python-драйвером **Motor** (`motor.motor_asyncio`). API дашборда підключається до тієї ж бази через .NET **MongoDB.Driver**.

## Налаштування з'єднання (`app/db.py`)

- `init_db(uri, db_name)`: Встановлює з'єднання з БД з використанням пулу з'єднань, визначеного в `settings.json` (`pool_min`, `pool_max`).
- **Стартові індекси**: Етап ініціалізації виконує `ensure_indexes()`, примусово створюючи `TTL` (Time-To-Live) та стандартні індекси запитів для гарантії оптимальних швидкостей читання/запису.
- **Debug-колекції**: `get_fiat_collection_name()` повертає `fiat_rates_debug` замість `fiat_rates`, якщо бот запущено з прапорцем `--debug`.

## Колекції

### 1. `Users`
Зберігає основні профілі користувачів, вподобання та дані лотів портфеля.
- `_id`: Telegram User ID (`int`).
- `Name`, `Username`, `Language`, `Premium`, `Sign up`.
- `Fiat currency`, `Crypto currency`, `Stocks`: Активні watchlist-и користувача.
- `BaseCurrency`: Валюта розрахунків за замовчуванням.
- `MainMenu`, `BigButtons`: Кастомізація UI.
- `portfolio`: Масив словників лотів активів за собівартістю.
- `last_active`: Мітка часу останньої взаємодії (для розрахунків DAU/WAU/MAU).
- `language`: ISO-код мови (`en`, `uk`, `pl`, `cs`, `sk`, `de`, `fr`).
- `volatility_threshold_pct`: Поріг алерту волатильності (за замовчуванням 5%).

### 2. `Groups`
Зберігає конфігурації та налаштування для Telegram-груп, де встановлено бот (`app/repositories/groups.py`).
- `_id` / `chat_id`: Telegram Chat ID (`int`).
- `Title`, `Type` (`supergroup` / `group`), `Members`.
- `Status`: `Active` або `Left`.
- `Input`: Валюти, які бот автоматично слухає в текстових повідомленнях.
- `Output`: Валюти, в які бот автоматично конвертує.
- `community_id`: Опціональний ID батьківської Telegram Community.
- `settings`: Кастомні налаштування групи (напр. `language`, `ephemeral_timeout`, `cooldown_seconds`).
- `stats`: Операційні метрики (загальна кількість запитів конвертації, дата останньої активності).

### 3. `Communities` (Bot API 10.2+)
Зберігає організаційні групування сутностей для Telegram суперgruп та каналів (`app/repositories/communities.py`).
- `_id` / `community_id`: Telegram Community ID (`str`).
- `name`: Назва спільноти.
- `discovered_at`: Мітка часу виявлення.
- `group_chat_ids`: Масив chat ID (`int`), що належать до цієї спільноти.

### 4. `Alerts`
Зберігає визначені користувачем тригери цінових повідомлень.
- `_id`: `ObjectId`.
- `user_id`: Telegram User ID.
- `currency_from`, `currency_to`, `target_price`.
- `condition`: Рядок (`above` або `below`).
- `triggered`: Булевий.

### 5. `fiat_rates`
Колекція з високочастотним оновленням, керована `fiat_parser.py` / `parser_service.py`.
- `currency`: Базова фіатна валюта (напр., `USD`).
- `rates`: Словник маппінгу цільових валют до обмінного курсу, зворотного курсу, символу та емодзі.
- `updated_at`: Мітка часу.

### 6. `current_prices`
Плоска кеш-колекція для миттєвих агрегаційних розрахунків P&L в MongoDB.
- `_id`: Символ тікера (напр., `BTC`, `AAPL`).
- `price_usd`: Актуальна ціна в USD.
- `source`: Рядок (`crypto` або `stock`).

### 7. `price_history`
Використовується для короткострокових алертів волатильності та щотижневих дайджестів.
- `timestamp`: Час створення знімка.
- `prices`: Словник маппінгу `{ticker: price_usd}`.
- *Ретенція*: Очищується `alert_service.py` старші за 7 днів.

### 8. `ApiKeys`
Зберігає API-ключі користувачів для синхронізації бірж (Binance, Bybit).
- `user_id`: Telegram User ID.
- `exchange`: Назва біржі (`binance` або `bybit`).
- `api_key`: API-ключ у відкритому вигляді.
- `api_secret`: Зберігається з симетричним шифруванням (Fernet, ключ з `settings.security.fernet_key`).

### 9. `Status` та `ProblematicSources`
- `Status`: Відстежує глобальні singleton-стани (напр., `last_digest_sent`, `last_crypto_stocks_update`).
- `ProblematicSources`: Логує збої краулерів з CoinMarketCap, Yahoo Finance або `fx-rate.net`.

### 10. `Otps` (Дашборд)
Зберігає OTP-коди для входу в дашборд.
- `telegramId`: Telegram User ID адміна.
- `otp`: 6-значний рядок коду.
- `ipAddress`: IP-адреса запитувача.
- `createdAt`: Мітка часу створення (ефективний TTL 5 хвилин).
- `used`: Булевий — позначає OTP як використаний.

### 11. `Settings` (Динамічний адмін)
Перевизначення конфігурації runtime, керовані через `/admin`.
- `_id`: `"admin_settings"` (singleton).
- `admin_ids`: Динамічно надані Telegram ID адмінів.
- `maintenance_mode`: Булевий — блокує звичайні команди користувачів при активації.

---

*Останнє оновлення: 2026-08-19*
