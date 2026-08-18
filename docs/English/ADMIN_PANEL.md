[← Back to docs index](README.md)

# Admin Panel & Group Management

The Admin Panel (`app/handlers/admin.py`, `app/handlers/admin_groups.py`, `app/handlers/group_admin.py`) provides system administrators and group chat owners with management tools, diagnostic reports, and mass-communication capabilities.

## Access Control

### System Administrators
System admin authorization is enforced strictly through `_is_admin(user_id)`. A user is a system admin if:
1. Their ID is listed in the `admin_ids` array inside `settings.json`.
2. Or, their ID exists dynamically inside the `admin_ids` array in the `Settings` MongoDB collection (`_id: "admin_settings"`). Super-admins can grant and revoke access dynamically via `/admin`.

### Group Administrators
Group admin permissions in chat groups are validated locally via `is_chat_admin()` (`app/utils/chat_admin.py`), matching real Telegram chat owners and administrators without granting global bot privileges.
- **Anonymous Admin handling**: Handles Telegram's `GroupAnonymousBot` safely by prompting anonymous admins to toggle their personal user profile to adjust group settings.

## System Admin Dashboard (`/admin`)

Invoking `/admin` opens an interactive inline dashboard:

1. **System & Group Statistics**
   - Integrates with `export_service.py` and `analytics_reporter.py`.
   - Displays metrics: Total Users, Daily Active Users (DAU), Active Groups, Communities, Fiat records in DB, API errors today, and MongoDB storage size.

2. **Parser Management (`CentralParserService`)**
   - Queries `ProblematicSources` to inspect failed web scrapers or APIs (CoinMarketCap / Yahoo / fx-rate).
   - Allows forcing a manual parser refresh cycle or clearing error logs (`cb_parser_clear_errors`).

3. **Group & Community Management (`admin_groups.py`)**
   - System admins can view all active/inactive Telegram groups, inspect member counts, link chats to Bot API 10.2 Communities, and toggle group feature flags.

4. **Data Export**
   - Generates and sends full CSV dumps of `Users` and `Groups` collections (`cb_admin_export_users`, `cb_admin_export_groups`).

5. **Maintenance Mode**
   - Toggles global `maintenance_mode` in database. Blocks normal user commands while active.

6. **Manage Admins & Broadcast**
   - Add/remove dynamic admin IDs via FSM (`AdminManageStates`).
   - Trigger mass broadcasts (`/broadcast`).

## Web Dashboard

In addition to the in-Telegram `/admin` panel, the project includes a full **web-based dashboard** at `dashboard/`. It provides the same monitoring and configuration capabilities through a browser interface, with additional data visualization (charts, tables, collection stats). See [Dashboard](DASHBOARD.md) for details.

## Group Administration System (`/group_settings`, `/rate`, `/group_stats`)

Real group administrators use `/group_settings` inside their groups to configure:
- **Listening Currencies**: Select which fiat, crypto, and stock codes trigger auto-conversion in natural language text.
- **Target Currencies**: Set base conversion output currencies.
- **Language Override**: Override bot language specifically for that group chat.
- **Ephemeral UI**: Adjust auto-delete timer for menu messages via `ephemeral_service.py`.

## Broadcast System (`/broadcast`)

State-machine flow (`BroadcastStates`) for mass announcements:
1. **Drafting**: HTML-formatted message input.
2. **Preview**: Renders message draft with confirmation buttons.
3. **Execution**: Pushes messages via `_send_batched` (capped at 25 msg/sec to respect Telegram `FloodWait`), producing a final delivery report.

---

*Last updated: 2026-08-19*
