# 🗄 Database Schema

**TL;DR:** The bot uses MongoDB with the `motor` async driver. The schema is implicitly defined by the code and relies on specific indexes established in `app/db.py`.

## Core Collections

### 1. `fiat_rates` (or `fiat_rates_debug`)
Stores the latest scraped currency conversion rates.
- **Indexes**: `currency` (unique), `updated_at`.
- **Document Example**:
  ```json
  {
    "currency": "USD",
    "rate_to_base": 1.0,
    "updated_at": ISODate("2026-07-23T12:00:00Z")
  }
  ```

### 2. `Users`
Stores individual bot users and their personalized settings.
- **Indexes**: `Username`, `last_active`, `portfolio.crypto.ticker`, `portfolio.stock.ticker`.
- **Document Example**:
  ```json
  {
    "_id": 123456789,
    "Username": "johndoe",
    "Language": "en",
    "Premium": false,
    "last_active": ISODate("2026-07-23T12:00:00Z"),
    "portfolio": {
       "crypto": [{"ticker": "BTC", "amount": 0.5}]
    }
  }
  ```

### 3. `Groups` / `groups`
Tracks groups where the bot is added.
- **Indexes**: `Status`, `chat_id` (unique), `is_active`.
- **Note**: `Groups` and `groups` appear in `db.py`, indicating older migrations or separate logic for chat tracking.

### 4. `Alerts`
User-defined price alerts.
- **Indexes**: `user_id`, `[user_id, triggered]`, `[triggered, currency_from]`.
- **Document Example**:
  ```json
  {
    "user_id": 123456789,
    "currency_from": "BTC",
    "target_price": 100000.0,
    "triggered": false
  }
  ```

### 5. `price_history`
Stores time-series data for volatility monitoring.
- **Indexes**: `timestamp` (descending) with a TTL (expireAfterSeconds) of 7 days.
