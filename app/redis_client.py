"""
Two-tier cache (L1 In-Memory + L2 Redis) with automatic fallback.

Architecture:
- L1 (Fast in-memory): Returns objects in microseconds without TCP roundtrips or JSON parsing.
- L2 (Distributed Redis): Shares state across instances/restarts with full TTL.
- Resilient: If Redis is unconfigured or encounters runtime network faults, operations
  gracefully degrade to L1 MemoryCache without raising exceptions to callers.

Usage:
    from app.redis_client import init_redis, close_redis, redis_get, redis_set, redis_delete
"""

from __future__ import annotations

import json
from typing import Any

from app.cache import cache as _mem_cache
from app.logger import get_logger

log = get_logger("redis_client")

_redis: Any = None  # redis.asyncio.Redis | None
L1_MAX_TTL_SEC = 30  # Maximum TTL in local memory cache to keep freshness synced with Redis


async def init_redis() -> None:
    global _redis

    from app.config import get_settings

    settings = get_settings()

    if not settings.redis.url:
        log.info("Redis disabled (settings.redis.url is empty) — using MemoryCache")
        return

    try:
        import redis.asyncio as aioredis
    except ImportError:
        log.warning("redis package not installed. Install with: pip install redis>=5.0.0")
        return

    try:
        client = aioredis.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            socket_timeout=settings.redis.socket_timeout,
            socket_connect_timeout=settings.redis.socket_connect_timeout,
            decode_responses=True,
        )
        await client.ping()
        _redis = client
        log.info("Redis connection established -> %s", settings.redis.url)
    except Exception as exc:
        log.warning("Redis unavailable (%s) — falling back to MemoryCache", exc)
        _redis = None


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as exc:
            log.warning("Error closing Redis: %s", exc)
        finally:
            _redis = None
            log.info("Redis connection closed")


def is_redis_available() -> bool:
    return _redis is not None


async def redis_get(key: str, default: Any = None) -> Any:
    """
    Get value using L1 (in-memory) -> L2 (Redis) lookup.
    """
    # 1. Check L1 Memory Cache first (sub-millisecond)
    val = await _mem_cache.get(key)
    if val is not None:
        return val

    # 2. Check L2 Redis if available
    if _redis is not None:
        try:
            raw = await _redis.get(key)
            if raw is not None:
                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    parsed = raw
                # Populate L1 cache with short TTL
                await _mem_cache.set(key, parsed, ttl=L1_MAX_TTL_SEC)
                return parsed
        except Exception as exc:
            log.debug("Redis GET error for key '%s': %s — using MemoryCache", key, exc)

    return default


async def redis_set(key: str, value: Any, ttl: int = 0) -> None:
    """
    Store value in both L1 (MemoryCache) and L2 (Redis).
    """
    # Store in L1 memory with bounded TTL
    l1_ttl = min(ttl, L1_MAX_TTL_SEC) if ttl > 0 else L1_MAX_TTL_SEC
    await _mem_cache.set(key, value, ttl=l1_ttl)

    # Store in L2 Redis if available
    if _redis is not None:
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            if ttl > 0:
                await _redis.setex(key, ttl, serialized)
            else:
                await _redis.set(key, serialized)
        except Exception as exc:
            log.debug("Redis SET error for key '%s': %s — stored in MemoryCache only", key, exc)


async def redis_delete(key: str) -> bool:
    """
    Delete from both L1 and L2 caches.
    """
    mem_deleted = await _mem_cache.delete(key)
    redis_deleted = False

    if _redis is not None:
        try:
            result = await _redis.delete(key)
            redis_deleted = result > 0
        except Exception as exc:
            log.debug("Redis DEL error for key '%s': %s", key, exc)

    return mem_deleted or redis_deleted


async def redis_exists(key: str) -> bool:
    """Check existence in L1 first, then L2."""
    if await _mem_cache.exists(key):
        return True

    if _redis is not None:
        try:
            return bool(await _redis.exists(key))
        except Exception as exc:
            log.debug("Redis EXISTS error for key '%s': %s", key, exc)

    return False
