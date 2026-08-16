"""
Optional Redis client — async wrapper with MemoryCache fallback.

Redis is enabled only when settings.redis.url is non-empty.
If Redis is unavailable (not configured, or connection fails at startup),
all operations transparently fall back to the in-process MemoryCache.

Usage:
    from app.redis_client import init_redis, close_redis, redis_get, redis_set, redis_delete

    # At startup (after get_settings())
    await init_redis()

    # In handlers / services
    value = await redis_get('key')
    await redis_set('key', 'value', ttl=300)
    await redis_delete('key')
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.cache import cache as _mem_cache
from app.logger import get_logger

log = get_logger('redis_client')

_redis: Any = None  # redis.asyncio.Redis | None


async def init_redis() -> None:
    global _redis

    from app.config import get_settings
    settings = get_settings()

    if not settings.redis.url:
        log.info('Redis disabled (settings.redis.url is empty) — using MemoryCache')
        return

    try:
        import redis.asyncio as aioredis
    except ImportError:
        log.warning('redis package not installed. Install with: pip install redis>=5.0.0')
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
        log.info('Redis connection established -> %s', settings.redis.url)
    except Exception as exc:
        log.warning('Redis unavailable (%s) — falling back to MemoryCache', exc)
        _redis = None


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as exc:
            log.warning('Error closing Redis: %s', exc)
        finally:
            _redis = None
            log.info('Redis connection closed')


def is_redis_available() -> bool:
    return _redis is not None


async def redis_get(key: str, default: Any = None) -> Any:
    if _redis is None:
        return await _mem_cache.get(key, default)
    try:
        raw = await _redis.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    except Exception as exc:
        log.debug("Redis GET error for key '%s': %s — using MemoryCache", key, exc)
        return await _mem_cache.get(key, default)


async def redis_set(key: str, value: Any, ttl: int = 0) -> None:
    if _redis is None:
        await _mem_cache.set(key, value, ttl=ttl)
        return
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        if ttl > 0:
            await _redis.setex(key, ttl, serialized)
        else:
            await _redis.set(key, serialized)
    except Exception as exc:
        log.debug("Redis SET error for key '%s': %s — using MemoryCache", key, exc)
        await _mem_cache.set(key, value, ttl=ttl)


async def redis_delete(key: str) -> bool:
    if _redis is None:
        return await _mem_cache.delete(key)
    try:
        result = await _redis.delete(key)
        return result > 0
    except Exception as exc:
        log.debug("Redis DEL error for key '%s': %s — using MemoryCache", key, exc)
        return await _mem_cache.delete(key)


async def redis_exists(key: str) -> bool:
    if _redis is None:
        return await _mem_cache.exists(key)
    try:
        return bool(await _redis.exists(key))
    except Exception as exc:
        log.debug("Redis EXISTS error for key '%s': %s — using MemoryCache", key, exc)
        return await _mem_cache.exists(key)
