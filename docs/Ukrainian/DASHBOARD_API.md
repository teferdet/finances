[← Повернутися до змісту](README.md)

# 🔌 Довідник API дашборда

API дашборда — це **.NET 8 ASP.NET Core** REST-бекенд для адмін-панелі. Підключається безпосередньо до спільної бази MongoDB та надає автентифікацію, статистику, управління конфігурацією та операційні дії.

## Технологічний стек

| Компонент | Технологія | Версія |
|---|---|---|
| **Runtime** | .NET | 8.0 |
| **Веб-фреймворк** | ASP.NET Core | 8.0 |
| **Драйвер БД** | MongoDB.Driver | 3.11 |
| **Автентифікація** | JWT Bearer | 8.0 |
| **Логування** | Serilog (Console + File) | 10.0 |
| **Документація API** | Swashbuckle (Swagger) | 6.6 (лише dev) |
| **Змінні середовища** | DotNetEnv | 3.2 |
| **Інтеграція Telegram** | Telegram.Bot | 22.10 |

## Структура проєкту

```
dashboard/API/
├── Program.cs               # Точка входу, DI, конвеєр middleware
├── API.csproj               # NuGet залежності та конфіг збірки
├── Controllers/
│   ├── AuthController.cs    # Запит OTP, перевірка, вихід, перевірка статусу
│   ├── StatsController.cs   # Огляд, активність, користувачі, БД, бот, парсер, алерти, групи, помилки
│   ├── ConfigController.cs  # Читання/оновлення settings.json, перемикачі feature-прапорців
│   ├── ActionsController.cs # Перезапуск бота через systemctl
│   └── HealthController.cs  # Health check (MongoDB ping)
├── Services/
│   ├── AuthService.cs       # Генерація OTP, доставка через Telegram, видача JWT
│   ├── StatsService.cs      # Агрегація MongoDB для метрик дашборда
│   └── ConfigService.cs     # Читання/запис settings.json з маскуванням чутливих полів
├── Repositories/
│   └── MongoContext.cs       # Singleton з'єднання MongoDB, аксесори колекцій, ping
└── Models/
    ├── Entities/             # AuthRequest, User
    ├── Requests/             # OtpRequestDto, OtpVerifyDto, ConfigUpdateDto, FeaturePatchDto
    └── Responses/            # OverviewStatsDto, ActivityChartResponseDto, DatabaseStatsDto тощо
```

## API ендпоінти

### Автентифікація (`/api/auth`)

Ці ендпоінти **публічні** (JWT не потрібен).

| Метод | Шлях | Опис |
|---|---|---|
| `POST` | `/api/auth/request-otp` | Генерація OTP, надсилання через Telegram |
| `POST` | `/api/auth/verify-otp` | Перевірка OTP, встановлення cookie JWT `dash_session` |
| `POST` | `/api/auth/logout` | Очищення cookie сесії |
| `GET` | `/api/auth/check-status` | Перевірка статусу запиту OTP (polling) |

#### `POST /api/auth/request-otp`

**Тіло:**
```json
{ "telegram_id": 123456789 }
```

**Потік:**
1. Перевірка `telegram_id` проти змінної `BOT_ADMIN_IDS`
2. Генерація криптографічно безпечного 6-значного OTP через `RandomNumberGenerator`
3. Збереження OTP в колекції MongoDB `Otps` з IP-адресою та міткою часу
4. Надсилання OTP адміну через Telegram Bot API `sendMessage`

**Відповідь:** `{ "ok": true, "message": "OTP & Approval buttons sent via Telegram" }`

#### `POST /api/auth/verify-otp`

**Тіло:**
```json
{ "telegram_id": 123456789, "otp": "482916" }
```

**Потік:**
1. Пошук невикористаного OTP, створеного протягом останніх 5 хвилин
2. Позначення OTP як використаного
3. Генерація JWT-токена (термін 7 днів, HS256)
4. Встановлення cookie `dash_session` HttpOnly

**Відповідь:** `{ "ok": true }`

---

### Статистика (`/api/stats`) 🔒

Усі ендпоінти статистики потребують JWT-автентифікації.

| Метод | Шлях | Опис |
|---|---|---|
| `GET` | `/api/stats/overview` | Агреговані KPI (користувачі, DAU, групи, алерти) |
| `GET` | `/api/stats/activity?days=30` | Дані графіка щоденної активності (DAU + запити) |
| `GET` | `/api/stats/users` | Мовний розподіл + топ користувачів |
| `GET` | `/api/stats/database` | Статистика колекцій MongoDB (розміри, кількість, індекси) |
| `GET` | `/api/stats/bot` | Статистика процесу бота (RAM, CPU, потоки, системні ресурси) |
| `GET` | `/api/stats/parser` | Здоров'я парсера (останні оновлення фіат/крипто/акцій, помилки, цикли) |
| `GET` | `/api/stats/alerts` | Підрахунок алертів (загальні, активні, спрацьовані, топ валют) |
| `GET` | `/api/stats/groups` | Статистика груп (загальні, активні, неактивні, останні реєстрації) |
| `GET` | `/api/stats/errors` | Останні записи логу помилок |

---

### Конфігурація (`/api/config`) 🔒

| Метод | Шлях | Опис |
|---|---|---|
| `GET` | `/api/config` | Читання `settings.json` (чутливі поля замасковані) |
| `POST` | `/api/config/update` | Оновлення конкретної секції конфігурації |
| `PATCH` | `/api/config/features` | Перемикання окремого feature-прапорця |

**Обмежені секції** (HTTP 403): `api_keys`, `bot`, `database`, `security`.

---

### Дії (`/api/actions`) 🔒

| Метод | Шлях | Опис |
|---|---|---|
| `POST` | `/api/actions/restart` | Перезапуск бота через `sudo systemctl restart finances-bot.service` |

---

### Здоров'я (`/api/health`)

Публічний ендпоінт — автентифікація не потрібна.

| Метод | Шлях | Опис |
|---|---|---|
| `GET` | `/api/health` | Перевірка з'єднання MongoDB |

**Відповідь (здоровий):** `{ "status": "ok", "database": "connected" }`
**Відповідь (нездоровий, HTTP 503):** `{ "status": "error", "database": "disconnected" }`

Використовується Docker healthcheck-ами та CI/CD `deploy.yml` моніторингом.

## Серіалізація JSON

API використовує `snake_case` для іменування JSON-властивостей:

```csharp
options.JsonSerializerOptions.PropertyNamingPolicy =
    System.Text.Json.JsonNamingPolicy.SnakeCaseLower;
```

## Контекст бази даних (`MongoContext`)

Зареєстрований як **Singleton**, `MongoContext` надає:
- `Database` — екземпляр `IMongoDatabase`
- `Users` — швидкий доступ до колекції `Users`
- `PingAsync()` — health check з'єднання для `/api/health`

## Логування

Serilog налаштований з двома sink-ами:
- **Console** — для логів Docker-контейнера (`docker compose logs`)
- **File** — щоденний ротаційний лог у `/app/logs/api.log`

## Swagger

В режимі розробки (`ASPNETCORE_ENVIRONMENT=Development`) Swagger UI доступний за адресою `/swagger`.

---

*Останнє оновлення: 2026-08-19*
