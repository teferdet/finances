[← Back to docs index](README.md)

# 🔌 Dashboard API Reference

The Dashboard API is a **.NET 8 ASP.NET Core** REST backend serving the admin dashboard. It connects directly to the shared MongoDB database and provides authentication, statistics, configuration management, and operational actions.

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| **Runtime** | .NET | 8.0 |
| **Web framework** | ASP.NET Core | 8.0 |
| **Database driver** | MongoDB.Driver | 3.11 |
| **Authentication** | JWT Bearer (Microsoft.AspNetCore.Authentication.JwtBearer) | 8.0 |
| **Logging** | Serilog (Console + File sinks) | 10.0 |
| **API docs** | Swashbuckle (Swagger) | 6.6 (dev only) |
| **Env loading** | DotNetEnv | 3.2 |
| **Telegram integration** | Telegram.Bot | 22.10 |

## Project Structure

```
dashboard/API/
├── Program.cs               # Application entry point, DI, middleware pipeline
├── API.csproj               # NuGet dependencies and build config
├── Controllers/
│   ├── AuthController.cs    # OTP request, verify, logout, status check
│   ├── StatsController.cs   # Overview, activity, users, database, bot, parser, alerts, groups, errors
│   ├── ConfigController.cs  # Read/update settings.json, feature flag toggles
│   ├── ActionsController.cs # Bot restart via systemctl
│   └── HealthController.cs  # Health check endpoint (MongoDB ping)
├── Services/
│   ├── AuthService.cs       # OTP generation, Telegram delivery, JWT token issuance
│   ├── StatsService.cs      # MongoDB aggregation for dashboard metrics
│   └── ConfigService.cs     # settings.json file read/write with sensitive field masking
├── Repositories/
│   └── MongoContext.cs       # MongoDB connection singleton, collection accessors, ping
└── Models/
    ├── Entities/             # AuthRequest, User
    ├── Requests/             # OtpRequestDto, OtpVerifyDto, ConfigUpdateDto, FeaturePatchDto
    └── Responses/            # OverviewStatsDto, ActivityChartResponseDto, DatabaseStatsDto, etc.
```

## Dependency Injection

Services are registered in `Program.cs`:

```csharp
builder.Services.AddSingleton<MongoContext>();    // Shared MongoDB connection
builder.Services.AddScoped<AuthService>();         // Per-request auth operations
builder.Services.AddScoped<StatsService>();        // Per-request stats aggregation
builder.Services.AddScoped<ConfigService>();        // Per-request config management
```

## API Endpoints

### Authentication (`/api/auth`)

These endpoints are **public** (no JWT required).

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/request-otp` | Generate OTP, send via Telegram to admin |
| `POST` | `/api/auth/verify-otp` | Verify OTP, set `dash_session` JWT cookie |
| `POST` | `/api/auth/logout` | Clear session cookie |
| `GET` | `/api/auth/check-status` | Check OTP request status (polling endpoint) |

#### `POST /api/auth/request-otp`

**Body:**
```json
{ "telegram_id": 123456789 }
```

**Flow:**
1. Validates `telegram_id` against `BOT_ADMIN_IDS` environment variable
2. Generates cryptographically secure 6-digit OTP via `RandomNumberGenerator`
3. Stores OTP in MongoDB `Otps` collection with IP address and timestamp
4. Sends OTP to the admin via Telegram Bot API `sendMessage`

**Response:** `{ "ok": true, "message": "OTP & Approval buttons sent via Telegram" }`

#### `POST /api/auth/verify-otp`

**Body:**
```json
{ "telegram_id": 123456789, "otp": "482916" }
```

**Flow:**
1. Looks up unused OTP created within the last 5 minutes
2. Marks OTP as used
3. Generates JWT token (7-day expiry, HS256)
4. Sets `dash_session` HttpOnly cookie

**Response:** `{ "ok": true }`

---

### Statistics (`/api/stats`) 🔒

All stats endpoints require JWT authentication.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/stats/overview` | Aggregate KPIs (users, DAU, groups, alerts) |
| `GET` | `/api/stats/activity?days=30` | Daily activity chart data (DAU + requests) |
| `GET` | `/api/stats/users` | User language distribution + top users |
| `GET` | `/api/stats/database` | MongoDB collection stats (sizes, counts, indexes) |
| `GET` | `/api/stats/bot` | Bot process stats (RAM, CPU, threads, system resources) |
| `GET` | `/api/stats/parser` | Parser health (fiat/crypto/stocks last update, errors, cycles) |
| `GET` | `/api/stats/alerts` | Price alert counts (total, active, triggered, top currencies) |
| `GET` | `/api/stats/groups` | Group stats (total, active, inactive, recent registrations) |
| `GET` | `/api/stats/errors` | Recent error log entries |

#### `GET /api/stats/overview`

Returns aggregate metrics from MongoDB:

```json
{
  "total_users": 1500,
  "dau": 230,
  "wau": 580,
  "mau": 1100,
  "premium": 45,
  "total_groups": 120,
  "active_alerts": 340,
  "requests_today": 5600,
  "requests_week": 38000,
  "errors_today": 3,
  "parser_cycles_today": 24,
  "retention_rate": 73.5
}
```

#### `GET /api/stats/database`

Executes `collStats` for each MongoDB collection:

```json
{
  "total_size_mb": 45.2,
  "storage_size_mb": 38.1,
  "index_size_mb": 7.1,
  "num_collections": 12,
  "connections_current": 5,
  "connections_available": 95,
  "mongo_version": "7.0.12",
  "collections": [
    { "name": "Users", "count": 1500, "size_kb": 2048.0, "avg_obj_size_bytes": 1398.0 },
    { "name": "Groups", "count": 120, "size_kb": 256.0, "avg_obj_size_bytes": 2185.0 }
  ]
}
```

---

### Configuration (`/api/config`) 🔒

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/config` | Read `settings.json` (sensitive fields masked) |
| `POST` | `/api/config/update` | Update a specific config section |
| `PATCH` | `/api/config/features` | Toggle a single feature flag |

#### `POST /api/config/update`

**Body:**
```json
{
  "section": "parser",
  "settings": {
    "auto_update": true,
    "update_interval_sec": 1800
  }
}
```

**Restricted sections** (HTTP 403): `api_keys`, `bot`, `database`, `security`.

#### `PATCH /api/config/features`

**Body:**
```json
{
  "feature": "groups_enabled",
  "value": true
}
```

---

### Actions (`/api/actions`) 🔒

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/actions/restart` | Restart the bot via `sudo systemctl restart finances-bot.service` |

The restart endpoint executes a system process call and returns the result.

---

### Health (`/api/health`)

Public endpoint — no authentication required.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | MongoDB connectivity check |

**Response (healthy):** `{ "status": "ok", "database": "connected" }`
**Response (unhealthy, HTTP 503):** `{ "status": "error", "database": "disconnected" }`

Used by Docker healthchecks and CI/CD `deploy.yml` monitoring.

## JSON Serialization

The API uses `snake_case` JSON property naming policy:

```csharp
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy =
            System.Text.Json.JsonNamingPolicy.SnakeCaseLower;
    });
```

## Database Context (`MongoContext`)

Registered as a **Singleton**, `MongoContext` provides:
- `Database` — the `IMongoDatabase` instance
- `Users` — shortcut to the `Users` collection
- `PingAsync()` — connection health check used by `/api/health`

Configuration is read from environment variables:
- `MONGO_URI` — MongoDB connection string
- `MONGO_DATABASE` — database name (default: `finances`)

## Logging

Serilog is configured with two sinks:
- **Console** — for Docker container logs (`docker compose logs`)
- **File** — daily rolling log at `/app/logs/api.log`

## Swagger

In development mode (`ASPNETCORE_ENVIRONMENT=Development`), Swagger UI is available at `/swagger`.

---

*Last updated: 2026-08-19*
