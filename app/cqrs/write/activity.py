"""
Write-behind buffer for user activity & daily statistics.

Reduces write load from (2 writes per user interaction) to (1 bulk_write every 5 seconds).
In-memory buffer aggregates request counts and latest active timestamps.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from pymongo import UpdateOne

from app.logger import get_logger

log = get_logger("cqrs.write.activity")


class ActivityWriteBehind:
    """Aggregates user activity and daily stats in memory, flushing to MongoDB in periodic batches."""

    def __init__(self, max_buffer_size: int = 10000) -> None:
        self._user_activity: dict[int, dict[str, Any]] = {}
        self._daily_stats: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._max_buffer_size = max_buffer_size
        self._flushed_batches: int = 0
        self._flushed_records: int = 0

    async def record_activity(self, user_id: int) -> None:
        """Record activity in-memory without blocking or DB I/O."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        async with self._lock:
            # Enforce max buffer size to avoid unbounded memory growth under attack
            if len(self._user_activity) >= self._max_buffer_size:
                # Discard oldest or simply stop adding new user tracking until next flush
                pass
            else:
                entry = self._user_activity.setdefault(user_id, {"last_active": now, "count": 0})
                entry["last_active"] = now
                entry["count"] += 1

            self._daily_stats[today_str] = self._daily_stats.get(today_str, 0) + 1

    async def flush(self) -> int:
        """Flush accumulated changes to MongoDB using a single bulk_write."""
        from app.db import get_raw_db

        async with self._lock:
            if not self._user_activity and not self._daily_stats:
                return 0

            pending_users = self._user_activity
            pending_daily = self._daily_stats
            self._user_activity = {}
            self._daily_stats = {}

        raw_db = get_raw_db()
        user_ops = [
            UpdateOne(
                {"_id": uid},
                {"$set": {"last_active": data["last_active"]}, "$inc": {"stats.total_requests": data["count"]}},
                upsert=False,
            )
            for uid, data in pending_users.items()
        ]

        daily_ops = [
            UpdateOne(
                {"_id": date_str},
                {"$inc": {"requests": count}},
                upsert=True,
            )
            for date_str, count in pending_daily.items()
        ]

        written = 0
        try:
            if user_ops:
                res = await raw_db["Users"].bulk_write(user_ops, ordered=False)
                written += (res.modified_count or 0) + (res.upserted_count or 0)
            if daily_ops:
                await raw_db["DailyStats"].bulk_write(daily_ops, ordered=False)

            self._flushed_batches += 1
            self._flushed_records += len(user_ops)
            return written
        except Exception as exc:
            log.warning("Failed to flush activity write-behind buffer: %s; restoring buffer", exc)
            # Restore to buffer with cap
            async with self._lock:
                for uid, data in pending_users.items():
                    if len(self._user_activity) < self._max_buffer_size:
                        cur = self._user_activity.setdefault(uid, {"last_active": data["last_active"], "count": 0})
                        cur["count"] += data["count"]
                for date_str, count in pending_daily.items():
                    self._daily_stats[date_str] = self._daily_stats.get(date_str, 0) + count
            return 0

    async def run_flusher_loop(self, interval_sec: float = 5.0) -> None:
        """Periodic background flusher loop."""
        log.info("Activity write-behind flusher started (interval: %.1fs)", interval_sec)
        while True:
            try:
                await asyncio.sleep(interval_sec)
                await self.flush()
            except asyncio.CancelledError:
                log.info("Activity write-behind flusher stopping, performing final flush...")
                await self.flush()
                break
            except Exception as exc:
                log.error("Error in activity write-behind flusher loop: %s", exc)

    def stats(self) -> dict[str, Any]:
        return {
            "buffered_users": len(self._user_activity),
            "buffered_daily": sum(self._daily_stats.values()),
            "flushed_batches": self._flushed_batches,
            "flushed_records": self._flushed_records,
        }


activity_buffer = ActivityWriteBehind()
