"""
Healthcheck and Heartbeat service.

Provides:
1. `run_heartbeat_loop()` — supervised background loop that updates `logs/heartbeat.json`
2. `check_health()` — diagnostics helper
3. CLI entry point (`python -m app.health`) for Docker HEALTHCHECK and monitoring probes
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

from app.config import LOGS_DIR, get_settings
from app.logger import get_logger

log = get_logger("health")

HEARTBEAT_FILE = LOGS_DIR / "heartbeat.json"
MAX_HEARTBEAT_AGE_SEC = 90.0


async def _ping_db() -> tuple[bool, str | None]:
    """Perform a ping on MongoDB."""
    try:
        from app.db import get_raw_db

        raw_db = get_raw_db()
        # 3 second timeout for ping
        await asyncio.wait_for(raw_db.command("ping"), timeout=3.0)
        return True, None
    except Exception as exc:
        return False, str(exc)


async def _ping_redis() -> tuple[bool, str | None]:
    """Check Redis health if configured."""
    settings = get_settings()
    if not settings.redis.url:
        return True, "disabled"

    try:
        from app.redis_client import is_redis_available

        if is_redis_available():
            return True, "connected"
        return False, "disconnected"
    except Exception as exc:
        return False, str(exc)


async def run_heartbeat_loop(interval: float = 20.0) -> None:
    """Supervised background loop writing current health snapshot to logs/heartbeat.json."""
    from app.cqrs.tasks import supervisor

    start_time = time.time()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Heartbeat worker started (interval: %.1fs)", interval)

    while True:
        try:
            db_ok, db_err = await _ping_db()
            redis_ok, redis_status = await _ping_redis()
            tasks_status = supervisor.get_status()

            payload: dict[str, Any] = {
                "timestamp": time.time(),
                "pid": os.getpid(),
                "uptime_sec": round(time.time() - start_time, 1),
                "healthy": db_ok,
                "db": {"ok": db_ok, "error": db_err},
                "redis": {"ok": redis_ok, "status": redis_status},
                "tasks": tasks_status,
            }

            temp_file = HEARTBEAT_FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temp_file.replace(HEARTBEAT_FILE)

        except asyncio.CancelledError:
            log.info("Heartbeat loop cancelled")
            break
        except Exception as exc:
            log.warning("Heartbeat generation failed: %s", exc)

        await asyncio.sleep(interval)


def check_health_sync() -> tuple[bool, str]:
    """Synchronous health check probe for CLI invocation."""
    if HEARTBEAT_FILE.exists():
        try:
            raw = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
            ts = float(raw.get("timestamp", 0))
            age = time.time() - ts
            if age > MAX_HEARTBEAT_AGE_SEC:
                return False, f"Heartbeat is stale: last updated {age:.1f}s ago (> {MAX_HEARTBEAT_AGE_SEC}s threshold)"

            if not raw.get("healthy", False):
                db_info = raw.get("db", {})
                return False, f"Unhealthy status reported: DB error: {db_info.get('error')}"

            # Check if any supervised task is failing repeatedly
            tasks = raw.get("tasks", [])
            failing_tasks = [t["name"] for t in tasks if t.get("last_error") and not t.get("running")]
            if failing_tasks:
                return False, f"Supervised tasks crashed: {', '.join(failing_tasks)}"

            uptime = raw.get("uptime_sec", 0)
            return True, f"Healthy (uptime: {uptime}s, tasks: {len(tasks)} active)"
        except Exception as exc:
            return False, f"Failed to read heartbeat file: {exc}"

    # Heartbeat file not yet created — perform direct DB probe
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db_ok, db_err = loop.run_until_complete(_ping_db())
        loop.close()
        if db_ok:
            return True, "Healthy (direct probe, startup phase)"
        return False, f"Direct DB probe failed: {db_err}"
    except Exception as exc:
        return False, f"Healthcheck error: {exc}"


def main() -> None:
    """CLI entrypoint: exits with 0 if healthy, 1 if unhealthy."""
    ok, message = check_health_sync()
    if ok:
        print(f"[HEALTHCHECK OK] {message}")
        sys.exit(0)
    else:
        print(f"[HEALTHCHECK FAILED] {message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
