"""
In-memory TTL cache — asyncio-safe replacement for Redis.

Usage:
    from app.cache import cache
    await cache.set("key", value, ttl=300)
    val = await cache.get("key")
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from app.logger import get_logger

log = get_logger("cache")


class MemoryCache:
    """Thread-safe asyncio in-memory cache with per-key TTL."""

    __slots__ = ("_store", "_lock")

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._lock = asyncio.Lock()

    # ── Public API ──────────────────────────────────────────────────

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            value, expires_at = entry
            if expires_at and time.monotonic() > expires_at:
                del self._store[key]
                return default
            return value

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """
        Store a value. ttl=0 means no expiration.
        ttl is in seconds.
        """
        expires_at = (time.monotonic() + ttl) if ttl > 0 else 0.0
        async with self._lock:
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        return (await self.get(key)) is not None

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed items."""
        now = time.monotonic()
        removed = 0
        async with self._lock:
            expired_keys = [k for k, (_, exp) in self._store.items() if exp and now > exp]
            for k in expired_keys:
                del self._store[k]
                removed += 1
        if removed:
            log.debug("Cache cleanup: removed %d expired entries", removed)
        return removed

    @property
    def size(self) -> int:
        return len(self._store)

    # ── JSON helpers (drop-in for old cache_json_get/set) ───────────

    async def json_get(self, key: str) -> Optional[dict]:
        return await self.get(key)

    async def json_set(self, key: str, value: dict, ttl: int = 3600) -> None:
        await self.set(key, value, ttl=ttl)


# ── Module-level singleton ──────────────────────────────────────────
cache = MemoryCache()


async def run_cache_cleanup_loop(interval: int = 900) -> None:
    """Background task to periodically purge expired cache entries (default: every 15 min)."""
    log.info("Started memory cache background cleanup loop (interval: %ds)", interval)
    while True:
        try:
            await asyncio.sleep(interval)
            await cache.cleanup_expired()
        except asyncio.CancelledError:
            log.info("Cache cleanup loop stopped")
            break
        except Exception as exc:
            log.warning("Error in cache cleanup loop: %s", exc)

