# 🔐 Admin Panel Guide

**TL;DR:** The `/admin` panel is an interactive Telegram interface exclusively available to users listed in `bot.admin_ids` (and `dynamic_admin_ids`). It offers live monitoring, configuration, and diagnostics.

## Access Control
Only users whose Telegram ID integer exists in the configuration's `admin_ids` or in the database's dynamic admins list are granted access. The `admin` router in `app/handlers/admin.py` enforces this.

## Available Modules

### Analytics & Statistics Dashboard
- **Description**: Displays daily/weekly active users, total lifetime requests, and parser cycles.
- **Usage Sequence**: Send `/admin` → Click `Analytics 📊`.

### System Configuration
- **Description**: Manage parser auto-updater state and intervals.
- **Usage Sequence**: Send `/admin` → Click `Configuration ⚙️`.

### Server Diagnostics
- **Description**: Displays real-time bot RAM allocation, system RAM, CPU load, and database storage footprint via `psutil`.
- **Usage Sequence**: Send `/admin` → Click `Server 🖥`.

### Error Logs
- **Description**: Read recent exceptions, export `.log` files securely, or clear logs.
- **Usage Sequence**: Send `/admin` → Click `Logs 📝` → `Download`.
- **Security Check**: Employs double-check authorization (your ID must strictly match) before transferring log files.

### Mass Message Broadcast
- **Description**: Push formatted HTML announcements to all registered bot users.
- **Usage Sequence**: Send `/admin` → Click `Broadcast 📢` → Enter message. Uses Finite State Machine (FSM) state `AdminStates:broadcast`.

### Restart Bot
- **Description**: Safely triggers `sys.exit()` leading to a systemd restart, persisting chat states across reboots via `.restart_state.json`.
- **Usage Sequence**: Send `/admin` → Click `Restart 🔄` → Confirm.

## Planned Modules

### 🚧 Group Management
- **Status**: In Progress.
- **Description**: A panel to manage bot settings inside groups, track group activity, and configure group-specific rate limits.
- **Relevant Code**: Partial handlers exist in `app/handlers/group_admin.py` and `app/handlers/admin_groups.py`.

### 🚧 Push Notifications
- **Status**: In Progress.
- **Description**: A scheduled system to push error alerts and analytics reports to administrators directly. The `run_digest_scheduler()` background task in `app/services/digest_service.py` is the foundation for this feature.
