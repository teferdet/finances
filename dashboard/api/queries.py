"""
Dashboard Queries — all MongoDB + system-level data queries.

All functions are async. They read from:
- MongoDB (via motor): Users, Groups, groups, Alerts, Portfolios,
  DailyStats, fiat_rates, current_prices, ErrorTracking
- Filesystem: logs/errors.log, logs/bot.log
- psutil: CPU, RAM, process info
- systemd: bot service status via `systemctl`
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
from motor.motor_asyncio import AsyncIOMotorDatabase


# ── Path resolution (relative to project root = dashboard/../) ────────────────
_THIS_DIR = Path(__file__).resolve().parent          # dashboard/api/
_PROJECT_ROOT = _THIS_DIR.parent.parent              # finances/
_LOGS_DIR = _PROJECT_ROOT / "logs"
_CONFIG_DIR = _PROJECT_ROOT / "config"


# ── Overview stats ─────────────────────────────────────────────────────────────

async def get_overview(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Returns top-level KPI metrics."""
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    wau_time = datetime.now() - timedelta(days=7)
    mau_time = datetime.now() - timedelta(days=30)

    total_users, dau, wau, mau, premium, total_groups, total_alerts = await asyncio.gather(
        db["Users"].count_documents({}),
        db["Users"].count_documents({"last_active": {"$gte": today_midnight}}),
        db["Users"].count_documents({"last_active": {"$gte": wau_time}}),
        db["Users"].count_documents({"last_active": {"$gte": mau_time}}),
        db["Users"].count_documents({"Premium": True}),
        db["Groups"].count_documents({}),
        db["Alerts"].count_documents({"triggered": False}),
    )

    # Requests today from DailyStats
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_doc = await db["DailyStats"].find_one({"_id": today_str})
    requests_today = daily_doc.get("requests", 0) if daily_doc else 0

    # Weekly requests
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    cursor = db["DailyStats"].find({"_id": {"$in": dates}})
    weekly_docs = await cursor.to_list(length=7)
    requests_week = sum(d.get("requests", 0) for d in weekly_docs)

    # Errors today from log
    errors_today = _count_log_lines_today(_LOGS_DIR / "errors.log")

    # Parser cycles today
    cycles_today = _count_pattern_in_log(_LOGS_DIR / "bot.log", "Cycle done in")

    return {
        "total_users": total_users,
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "premium": premium,
        "total_groups": total_groups,
        "active_alerts": total_alerts,
        "requests_today": requests_today,
        "requests_week": requests_week,
        "errors_today": errors_today,
        "parser_cycles_today": cycles_today,
        "retention_rate": round(dau / wau * 100, 1) if wau > 0 else 0,
    }


async def get_activity_chart(db: AsyncIOMotorDatabase, days: int = 30) -> dict[str, Any]:
    """Returns daily active user data for the past N days (for charts)."""
    result = []
    for i in range(days - 1, -1, -1):
        day = datetime.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_str = day_start.strftime("%Y-%m-%d")

        dau = await db["Users"].count_documents({
            "last_active": {"$gte": day_start, "$lt": day_end}
        })
        daily_doc = await db["DailyStats"].find_one({"_id": day_str})
        requests = daily_doc.get("requests", 0) if daily_doc else 0
        result.append({"date": day_str, "dau": dau, "requests": requests})

    return {"days": result}


async def get_users_by_language(db: AsyncIOMotorDatabase) -> list[dict]:
    """Breakdown of users by language."""
    pipeline = [
        {"$group": {"_id": "$Language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    result = []
    async for doc in db["Users"].aggregate(pipeline):
        result.append({"language": doc["_id"] or "unknown", "count": doc["count"]})
    return result


async def get_top_users(db: AsyncIOMotorDatabase, limit: int = 20) -> list[dict]:
    """Top users by total requests."""
    cursor = db["Users"].find(
        {},
        {"_id": 1, "Username": 1, "Language": 1, "Premium": 1,
         "stats.total_requests": 1, "last_active": 1}
    ).sort("stats.total_requests", -1).limit(limit)
    users = []
    async for u in cursor:
        users.append({
            "id": u["_id"],
            "username": u.get("Username", ""),
            "language": u.get("Language", "en"),
            "premium": u.get("Premium", False),
            "requests": u.get("stats", {}).get("total_requests", 0),
            "last_active": u.get("last_active", "").isoformat() if u.get("last_active") else None,
        })
    return users


# ── Database stats ─────────────────────────────────────────────────────────────

async def get_database_stats(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Collection counts, sizes, and DB-level stats."""
    collections = await db.list_collection_names()
    db_stats = await db.command("dbStats")
    server_info = await db.command("serverStatus")

    col_stats = []
    for col_name in sorted(collections):
        try:
            col_stat = await db.command("collStats", col_name)
            count = col_stat.get("count", 0)
            size_kb = round(col_stat.get("size", 0) / 1024, 1)
            avg_obj_size = round(col_stat.get("avgObjSize", 0), 0)
        except Exception:
            count = await db[col_name].count_documents({})
            size_kb = 0
            avg_obj_size = 0
        col_stats.append({
            "name": col_name,
            "count": count,
            "size_kb": size_kb,
            "avg_obj_size_bytes": avg_obj_size,
        })

    # Connection pool info
    connections = server_info.get("connections", {})

    return {
        "total_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
        "storage_size_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
        "index_size_mb": round(db_stats.get("indexSize", 0) / (1024 * 1024), 2),
        "collections": col_stats,
        "num_collections": len(collections),
        "connections_current": connections.get("current", 0),
        "connections_available": connections.get("available", 0),
        "mongo_version": server_info.get("version", "unknown"),
    }


# ── Bot / System health ────────────────────────────────────────────────────────

async def get_bot_status() -> dict[str, Any]:
    """Bot service health, CPU, RAM, uptime."""
    result: dict[str, Any] = {}

    # systemd status
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", "finances-bot.service"],
            capture_output=True, text=True, timeout=5
        )
        result["service_status"] = proc.stdout.strip()
    except Exception:
        result["service_status"] = "unknown"

    # systemd uptime
    try:
        proc = subprocess.run(
            ["systemctl", "show", "finances-bot.service",
             "--property=ActiveEnterTimestamp", "--no-page"],
            capture_output=True, text=True, timeout=5
        )
        ts_line = proc.stdout.strip()
        # e.g. "ActiveEnterTimestamp=Wed 2026-08-13 10:00:00 UTC"
        if "=" in ts_line:
            ts_str = ts_line.split("=", 1)[1].strip()
            result["started_at"] = ts_str
        else:
            result["started_at"] = None
    except Exception:
        result["started_at"] = None

    # Process metrics
    try:
        bot_proc = _find_bot_process()
        if bot_proc:
            mem = bot_proc.memory_info()
            result["bot_ram_mb"] = round(mem.rss / (1024 * 1024), 1)
            result["bot_cpu_pct"] = bot_proc.cpu_percent(interval=None)
            result["bot_pid"] = bot_proc.pid
            result["bot_threads"] = bot_proc.num_threads()
        else:
            result.update({"bot_ram_mb": None, "bot_cpu_pct": None,
                            "bot_pid": None, "bot_threads": None})
    except Exception:
        result.update({"bot_ram_mb": None, "bot_cpu_pct": None,
                        "bot_pid": None, "bot_threads": None})

    # System-wide metrics
    sys_mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_cores = psutil.cpu_count(logical=False) or 1
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

    result.update({
        "sys_ram_used_gb": round(sys_mem.used / (1024 ** 3), 2),
        "sys_ram_total_gb": round(sys_mem.total / (1024 ** 3), 2),
        "sys_ram_pct": sys_mem.percent,
        "sys_cpu_pct": psutil.cpu_percent(interval=None),
        "sys_cpu_cores": cpu_cores,
        "load_avg_1m": round(load_avg[0], 2),
        "load_avg_5m": round(load_avg[1], 2),
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "disk_pct": disk.percent,
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "hostname": platform.node(),
    })

    # Bot version from config
    try:
        cfg_path = _CONFIG_DIR / "settings.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        result["bot_version"] = cfg.get("bot", {}).get("version", "unknown")
    except Exception:
        result["bot_version"] = "unknown"

    return result


def _find_bot_process() -> psutil.Process | None:
    """Find the running bot Python process."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any("app" in arg for arg in cmdline) and "python" in (proc.info.get("name") or ""):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


# ── Parser status ──────────────────────────────────────────────────────────────

async def get_parser_status(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Status of fiat, crypto and stocks parsers."""
    # Fiat — last updated rate
    fiat_latest = await db["fiat_rates"].find_one(
        {}, sort=[("updated_at", -1)]
    )
    fiat_count = await db["fiat_rates"].count_documents({})

    # Crypto / stocks prices
    crypto_doc = await db["current_prices"].find_one({"source": "crypto"})
    stocks_doc = await db["current_prices"].find_one({"source": "stocks"})

    # Error tracking for parsers
    parser_errors = []
    async for err in db["ErrorTracking"].find({}).sort("error_count", -1).limit(10):
        parser_errors.append({
            "source": err.get("_id", "unknown"),
            "count": err.get("error_count", 0),
            "last_error": err.get("last_error", ""),
            "last_seen": err.get("last_seen", "").isoformat() if err.get("last_seen") else None,
        })

    return {
        "fiat": {
            "count": fiat_count,
            "last_updated": fiat_latest.get("updated_at").isoformat() if fiat_latest and fiat_latest.get("updated_at") else None,
        },
        "crypto": {
            "last_updated": crypto_doc.get("updated_at").isoformat() if crypto_doc and crypto_doc.get("updated_at") else None,
        },
        "stocks": {
            "last_updated": stocks_doc.get("updated_at").isoformat() if stocks_doc and stocks_doc.get("updated_at") else None,
        },
        "parser_errors": parser_errors,
        "cycles_today": _count_pattern_in_log(_LOGS_DIR / "bot.log", "Cycle done in"),
    }


# ── Alerts ─────────────────────────────────────────────────────────────────────

async def get_alerts_stats(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Price alert statistics."""
    total = await db["Alerts"].count_documents({})
    active = await db["Alerts"].count_documents({"triggered": False})
    triggered = await db["Alerts"].count_documents({"triggered": True})

    # Top currencies in alerts
    pipeline = [
        {"$match": {"triggered": False}},
        {"$group": {"_id": "$currency_from", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_currencies = []
    async for doc in db["Alerts"].aggregate(pipeline):
        top_currencies.append({"currency": doc["_id"], "count": doc["count"]})

    return {
        "total": total,
        "active": active,
        "triggered": triggered,
        "top_currencies": top_currencies,
    }


# ── Groups ─────────────────────────────────────────────────────────────────────

async def get_groups_stats(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Groups overview."""
    total = await db["groups"].count_documents({})
    active = await db["groups"].count_documents({"is_active": True})

    # Recent groups
    cursor = db["groups"].find(
        {},
        {"chat_id": 1, "title": 1, "is_active": 1, "added_at": 1, "member_count": 1}
    ).sort("added_at", -1).limit(20)
    recent = []
    async for g in cursor:
        recent.append({
            "chat_id": g.get("chat_id"),
            "title": g.get("title", "Unknown"),
            "is_active": g.get("is_active", False),
            "member_count": g.get("member_count", 0),
            "added_at": g.get("added_at").isoformat() if g.get("added_at") else None,
        })

    return {"total": total, "active": active, "inactive": total - active, "recent": recent}


# ── Error log ─────────────────────────────────────────────────────────────────

def get_error_log(lines: int = 100) -> list[dict]:
    """Return the last N lines from errors.log with parsed metadata."""
    error_log_path = _LOGS_DIR / "errors.log"
    if not error_log_path.exists():
        return []

    time_re = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.+)$")
    result = []
    try:
        with open(error_log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        for line in all_lines[-lines:]:
            line = line.rstrip()
            m = time_re.match(line)
            if m:
                result.append({
                    "timestamp": m.group(1),
                    "level": m.group(2),
                    "message": m.group(3)[:300],
                })
            elif line:
                result.append({"timestamp": None, "level": "INFO", "message": line[:300]})
    except Exception:
        pass
    return list(reversed(result))  # newest first


# ── Config reader ──────────────────────────────────────────────────────────────

def get_config_safe() -> dict[str, Any]:
    """Return config without sensitive secrets."""
    try:
        cfg_path = _CONFIG_DIR / "settings.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return {}

    # Strip secrets
    cfg.get("bot", {}).pop("token", None)
    cfg.get("database", {}).pop("mongo_uri", None)
    cfg.get("api_keys", {}).clear()
    cfg.get("security", {}).pop("fernet_key", None)
    return cfg


FORBIDDEN_FIELDS = {
    ("bot", "token"),
    ("database", "mongo_uri"),
    ("security", "fernet_key"),
    ("api_keys", "crypto"),
    ("api_keys", "stocks"),
}


def update_config_section(section: str, data: dict[str, Any]) -> bool:
    """
    Safely update a section in settings.json.
    Strips sensitive keys so tokens/passwords can never be overwritten.
    """
    try:
        cfg_path = _CONFIG_DIR / "settings.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        if section not in cfg:
            cfg[section] = {}

        # Strip forbidden secrets
        for k in list(data.keys()):
            if (section, k) in FORBIDDEN_FIELDS or section == "api_keys":
                data.pop(k, None)

        cfg[section].update(data)

        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error updating config section {section}: {e}")
        return False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _count_log_lines_today(log_path: Path) -> int:
    today_str = datetime.now().strftime("%Y-%m-%d")
    count = 0
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith(today_str):
                    count += 1
    except Exception:
        pass
    return count


def _count_pattern_in_log(log_path: Path, pattern: str) -> int:
    today_str = datetime.now().strftime("%Y-%m-%d")
    count = 0
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith(today_str) and pattern in line:
                    count += 1
    except Exception:
        pass
    return count


# ── Broadcast & Admins ─────────────────────────────────────────────────────────

_active_broadcast = {
    "running": False,
    "total": 0,
    "sent": 0,
    "failed": 0,
    "target": "all",
    "text": "",
    "started_at": None,
}


async def get_broadcast_audience(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    """Calculate target audience stats for broadcasting."""
    total = await db["Users"].count_documents({})
    premium = await db["Users"].count_documents({"Premium": True})

    pipeline = [
        {"$group": {"_id": "$Language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    by_lang = {}
    async for doc in db["Users"].aggregate(pipeline):
        lang_code = doc["_id"] or "unknown"
        by_lang[lang_code] = doc["count"]

    return {
        "total": total,
        "premium": premium,
        "non_premium": total - premium,
        "by_language": by_lang,
    }


def get_broadcast_status() -> dict[str, Any]:
    """Return live status of active broadcast."""
    return dict(_active_broadcast)


def cancel_broadcast() -> bool:
    """Stop running broadcast task."""
    global _active_broadcast
    if _active_broadcast["running"]:
        _active_broadcast["running"] = False
        return True
    return False


async def start_broadcast_task(db: AsyncIOMotorDatabase, target: str, text: str) -> bool:
    """Start background task for broadcast."""
    global _active_broadcast
    if _active_broadcast["running"]:
        return False

    asyncio.create_task(_execute_broadcast(db, target, text))
    return True


async def _execute_broadcast(db: AsyncIOMotorDatabase, target: str, text: str) -> None:
    global _active_broadcast
    from .auth import BOT_TOKEN
    import httpx

    query = {}
    if target == "premium":
        query = {"Premium": True}
    elif target == "non_premium":
        query = {"Premium": False}
    elif target.startswith("lang_"):
        lang_code = target.split("_", 1)[1]
        query = {"Language": lang_code}

    cursor = db["Users"].find(query, {"_id": 1})
    user_ids = [doc["_id"] async for doc in cursor]

    _active_broadcast.update({
        "running": True,
        "total": len(user_ids),
        "sent": 0,
        "failed": 0,
        "target": target,
        "text": text,
        "started_at": datetime.now().isoformat(),
    })

    if not BOT_TOKEN:
        _active_broadcast["running"] = False
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    async with httpx.AsyncClient(timeout=10.0) as client:
        for uid in user_ids:
            if not _active_broadcast["running"]:
                break
            try:
                resp = await client.post(url, json={
                    "chat_id": uid,
                    "text": text,
                    "parse_mode": "HTML",
                })
                if resp.status_code == 200:
                    _active_broadcast["sent"] += 1
                else:
                    _active_broadcast["failed"] += 1
            except Exception:
                _active_broadcast["failed"] += 1
            
            await asyncio.sleep(0.04)  # 25 msgs/sec safety limit

    _active_broadcast["running"] = False


async def get_admins_list(db: AsyncIOMotorDatabase, primary_ids: list[int]) -> dict[str, Any]:
    """Get static and dynamic admins."""
    dynamic_doc = await db["admins"].find_one({"_id": "dynamic_admins"})
    dynamic_ids = dynamic_doc.get("ids", []) if dynamic_doc else []
    return {
        "primary_admins": primary_ids,
        "dynamic_admins": dynamic_ids,
        "total": len(set(primary_ids + dynamic_ids)),
    }


async def add_dynamic_admin(db: AsyncIOMotorDatabase, admin_id: int) -> bool:
    """Add dynamic admin ID to DB."""
    await db["admins"].update_one(
        {"_id": "dynamic_admins"},
        {"$addToSet": {"ids": admin_id}},
        upsert=True
    )
    try:
        from app.state import dynamic_admin_ids
        dynamic_admin_ids.add(admin_id)
    except Exception:
        pass
    return True


async def remove_dynamic_admin(db: AsyncIOMotorDatabase, admin_id: int) -> bool:
    """Remove dynamic admin ID from DB."""
    await db["admins"].update_one(
        {"_id": "dynamic_admins"},
        {"$pull": {"ids": admin_id}}
    )
    try:
        from app.state import dynamic_admin_ids
        dynamic_admin_ids.discard(admin_id)
    except Exception:
        pass
    return True


def save_parser_interval(seconds: int) -> bool:
    """Save parser update interval to settings.json."""
    try:
        cfg_path = _CONFIG_DIR / "settings.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.setdefault("parser", {})["update_interval_sec"] = seconds
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


async def search_users(db: AsyncIOMotorDatabase, query: str, limit: int = 20) -> list[dict]:
    """Search users by ID or username."""
    filter_q = {}
    query_str = query.strip()
    if query_str.isdigit():
        filter_q = {"$or": [{"_id": int(query_str)}, {"Username": {"$regex": query_str, "$options": "i"}}]}
    elif query_str:
        filter_q = {"Username": {"$regex": query_str.replace("@", ""), "$options": "i"}}

    cursor = db["Users"].find(
        filter_q,
        {"_id": 1, "Username": 1, "Language": 1, "Premium": 1,
         "stats.total_requests": 1, "last_active": 1}
    ).limit(limit)

    users = []
    async for u in cursor:
        users.append({
            "id": u["_id"],
            "username": u.get("Username", ""),
            "language": u.get("Language", "en"),
            "premium": u.get("Premium", False),
            "requests": u.get("stats", {}).get("total_requests", 0),
            "last_active": u.get("last_active", "").isoformat() if u.get("last_active") else None,
        })
    return users

