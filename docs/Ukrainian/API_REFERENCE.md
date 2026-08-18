[← Повернутися до змісту](README.md)

# Довідник зовнішніх API

Бот інтегрується з кількома зовнішніми сервісами та функціями Telegram Bot API для надання ринкових фінансових даних у реальному часі, відповідей на guest-запити та синхронізації портфелів.

## 1. Telegram Bot API 10.x — Guest-запити та спільноти

### Ціль: Telegram Bot API (`answerGuestQuery`)
- **Модуль:** `app/handlers/guest.py`
- **Механізм:** Обробник `aiogram 3.x` (`@router.guest_message(F.guest_query_id)`).
- **Функціонал:** Обробляє згадки `@bot` у чатах, де бот не є учасником. Бот отримує оновлення `guest_message` з `guest_query_id` та відповідає через `message.answer_guest_query(result=InlineQueryResultArticle(...))`.

### Ціль: Telegram Communities (Bot API 10.2)
- **Модуль:** `app/repositories/communities.py`
- **Функціонал:** Маппінг батьківських сутностей спільнот до пов'язаних суперgruп і каналів у MongoDB.

### Ціль: Telegram `sendMessageDraft` (Недокументований)
- **Модуль:** `app/utils/draft.py`
- **Функціонал:** Анімує текст у полі вводу користувача під час обробки запитів ботом. Використовує недокументований метод `sendMessageDraft`. Працює тільки в приватних чатах, тільки для першої відповіді, і тільки коли `settings.draft.enabled` = `True`.

## 2. Курси фіатних валют

### Ціль: `fx-rate.net`
- **Модуль:** `app/services/fiat_parser.py`
- **Механізм:** Веб-скрапінг з BeautifulSoup4.
- **Обхід захисту:** `fx-rate.net` захищений суворими Cloudflare Anti-DDoS перевірками. Для headless-обходу бот використовує `curl_cffi` з аргументом `impersonate="chrome120"`.
- **Потік:** Читає HTML-таблиці, шукаючи класи `.c_parameter` та атрибути `data-rate`, стандартизує прапори країн в емодзі та виводить безпосередньо в MongoDB.
- **Логіка повторів:** Налаштовується через `parser.retry_attempts` (за замовчуванням 3) та `parser.retry_delay_sec` (за замовчуванням 5с).

## 3. Ринкові дані криптовалют

### Ціль: CoinMarketCap API (`pro-api.coinmarketcap.com`)
- **Модуль:** `app/services/crypto_parser.py`
- **Механізм:** Асинхронний запит `aiohttp`.
- **Endpoint:** `/v1/cryptocurrency/listings/latest`
- **Автентифікація:** Потребує заголовок `X-CMC_PRO_API_KEY`, завантажений з `settings.api_keys.crypto`.
- **Query-параметри:** Пагінація через `start=1&limit=100`, конвертація проти визначених користувачем базових валют.

## 4. Ринкові дані акцій

### Ціль: Yahoo Finance
- **Модуль:** `app/services/stocks_parser.py`
- **Механізм:** Python-бібліотека `yfinance`.
- **Примітка реалізації:** Оскільки `yfinance` робить синхронні блокуючі виклики, він обгорнутий в `asyncio.to_thread` / `run_in_executor` для запобігання блокування основного asyncio event loop.

## 5. Синхронізація портфелів з біржами

Користувачі можуть прив'язати свої біржові акаунти до бота для автоматичного заповнення портфеля. Бот безпечно керує секретами (`app/services/security.py` — симетричне шифрування Fernet, ключ з `settings.security.fernet_key`).

### Binance
- **Модуль:** `app/services/exchange_sync.py` → `fetch_binance_balances`
- **Endpoint:** `https://api.binance.com/api/v3/account`
- **Автентифікація:** Потребує підпис HMAC-SHA256, доданий до query string, підписаний розшифрованим API Secret користувача, та заголовок `X-MBX-APIKEY`.

### Bybit
- **Модуль:** `app/services/exchange_sync.py` → `fetch_bybit_balances`
- **Endpoint:** `https://api.bybit.com/v5/account/wallet-balance` (потребує Unified Trading Account).
- **Автентифікація:** Потребує заголовки: `X-BAPI-API-KEY`, `X-BAPI-TIMESTAMP`, `X-BAPI-RECV-WINDOW` та заголовок `X-BAPI-SIGN` — HMAC-SHA256 хеш конкатенованого рядка payload.

## 6. Доставка OTP дашборда

### Ціль: Telegram Bot API (`sendMessage`)
- **Модуль:** `dashboard/API/Services/AuthService.cs`
- **Механізм:** .NET `HttpClient` POST на `https://api.telegram.org/bot{token}/sendMessage`.
- **Функціонал:** Доставляє 6-значні OTP-коди адмін-користувачам як частину потоку автентифікації дашборда. HTML-форматоване повідомлення включає OTP-код та IP-адресу запитувача.

---

*Останнє оновлення: 2026-08-19*
