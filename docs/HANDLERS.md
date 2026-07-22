[← Back to docs index](README.md)

# Handlers

Handlers define the core interaction loop with users and groups in the Telegram Bot. The `teferdet/finances` bot uses `aiogram 3.x` routers to separate concerns. Each file exports a `router` instance, which is registered centrally in `bot.py`.

## Directory: `app/handlers/`

### 1. `admin.py`
**Trigger**: `/admin`, `/broadcast`, or specific admin callbacks (`cb_admin_*`).
- **Access**: Restricted by `_is_admin()`, which checks the `admin_ids` list from `settings.json` and a dynamically updatable `Settings` collection in MongoDB.
- **Commands**:
  - `/admin`: Displays the admin dashboard.
  - `/broadcast`: Initiates an FSM flow (`BroadcastStates`) to send a message to all users. Includes preview and confirm callbacks.
- **Features**: Diagnostic reports (via `export_service.py`), toggling maintenance mode, dynamically adding/removing admins, checking parser health, and extracting CSV reports.

### 2. `admin_groups.py`
**Trigger**: Admin callbacks prefixed with `admin_groups:`.
- **Flow**: Provides global system administrators with deep monitoring and control over registered Telegram groups and Bot API 10.2 Communities.
- **Features**: Group status listings, manual group deactivation, community linking, and group-wide analytics overview.

### 3. `alerts.py`
**Trigger**: `/alert` and `alert_*` callbacks.
- **Flow**: Provides an interface for users to set target price notifications for crypto, stock, or fiat pairs. 
- **DB Interaction**: Saves un-triggered alerts to the `Alerts` collection.
- **Volatility**: Allows users to configure their `volatility_threshold_pct` (e.g., 5% drop).

### 4. `crypto.py`
**Trigger**: `/crypto` command.
- **Flow**: Fetches live crypto rates cached in MongoDB (parsed by `crypto_parser.py`).
- **Response**: Formats top assets based on user configuration and displays them.

### 5. `exchange.py` & `exchange_api.py`
**Trigger**: Callbacks for exchange synchronization (e.g., Binance, Bybit).
- **Flow**:
  - `exchange.py` initiates the API key binding process, handling FSM inputs for `api_key` and `api_secret`.
  - `exchange_api.py` interacts with `exchange_sync.py` to encrypt secrets using `security.py` and syncs current exchange balances directly into the user's portfolio.

### 6. `group_admin.py`
**Trigger**: `/group_settings`, `/rate`, `/group_stats`, and `grp_settings:` callbacks.
- **Flow**: Allows actual group administrators (chat owner / admins) to manage group currency settings, language preferences, and listening parameters.
- **Security & UX**: 
  - Validates group permissions via `is_chat_admin()`.
  - Handles Telegram's `GroupAnonymousBot` safely by prompting anonymous admins to toggle their personal profile.
  - Employs `ephemeral_service` for clean, self-deleting settings notifications in group chats.

### 7. `groups.py`
**Trigger**: `my_chat_member` events (bot added/kicked) or `/config` inside a group.
- **Flow**: Detects when the bot is added to or removed from a group chat. Automatically registers or updates group status in `app/repositories/groups.py` and offers deep-links for setup.

### 8. `guest.py` (Bot API 10.0+)
**Trigger**: `guest_message` updates (`F.guest_query_id`).
- **Flow**: Processes `@bot` mentions in chats where the bot is NOT a member. Parses natural language financial text and replies via `message.answer_guest_query()` using `InlineQueryResultArticle` objects.

### 9. `inline_query.py`
**Trigger**: Typing `@fStatisticsBot <query>` in any chat.
- **Flow**: Uses `TextProcessing` to parse the query (e.g., `100 USD`). Calculates the live conversion value against target currencies and returns an `InlineQueryResultArticle`.

### 10. `language.py`
**Trigger**: `/language`, `/lang` or settings callbacks.
- **Flow**: Presents a localized inline keyboard of supported languages mapped from `app/i18n.py`. Updates user database preferences.

### 11. `my_data.py`
**Trigger**: "My Data" callbacks from the settings menu.
- **Flow**: Generates an overview of the user's profile, including tracked assets, active alerts, and settings, with a reset option.

### 12. `portability.py`
**Trigger**: `/export`, `/import`, or receiving a `.csv` document.
- **Flow**:
  - `export`: Generates a `portfolio_export.csv` containing asset entries.
  - `import`: Uses pandas (run in `asyncio.to_thread`) to read a CSV, validate tickers, and append valid assets.

### 13. `portfolio.py`
**Trigger**: `/portfolio` and `portfolio_*` callbacks.
- **Flow**: Manages financial portfolio entries (`/portfolio add crypto BTC 1.5 60000`). Aggregates P&L using cached `current_prices`.

### 14. `settings.py`
**Trigger**: `/settings` and menu callbacks.
- **Flow**: Multi-page settings menu utilizing `cache.py` to store navigation state. Modifies fiat, crypto, stock watchlists, base currency, and UI toggles.

### 15. `start.py`
**Trigger**: `/start`, `/help`, `/donate`, `/privacy`, `/expense_manager`.
- **Flow**: Registers new users upon `/start` and sends localized greeting messages with reply keyboard layouts.

### 16. `stocks.py`
**Trigger**: `/stocks` command.
- **Flow**: Returns current stock valuations based on user preferences, using values parsed by `stocks_parser.py`.

### 17. `text.py`
**Trigger**: Catch-all for plain text messages in private and group chats.
- **Flow**: Identifies monetary values in natural language, delegates conversion to `parser_service.convert_currencies()`, and formats the response while respecting group cooldowns.

---

*Last updated: 2026-07-22*

