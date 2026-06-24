"""
Async MongoDB connection via Motor.

Usage:
    from app.db import get_db, close_db
    db = get_db()          # returns MotorDatabase
    await close_db()       # call on shutdown
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings
from app.logger import get_logger

log = get_logger("db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    """Return the shared MotorDatabase instance (lazy init)."""
    global _client, _db
    if _db is not None:
        return _db

    settings = get_settings()
    _client = AsyncIOMotorClient(
        settings.database.mongo_uri,
        maxPoolSize=settings.database.pool_max,
        minPoolSize=settings.database.pool_min,
        maxIdleTimeMS=30_000,
    )
    _db = _client[settings.database.mongo_database]
    log.info("MongoDB connection established -> %s", settings.database.mongo_database)
    return _db


async def ensure_indexes() -> None:
    """Create essential indexes (idempotent)."""
    db = get_db()
    try:
        await db["fiat_rates"].create_index("currency", unique=True)
        await db["fiat_rates"].create_index("updated_at")
        await db["Users"].create_index("Username")
        await db["Users"].create_index("last_active")
        await db["Groups"].create_index("Status")
        await db["Alerts"].create_index("user_id")
        await db["Alerts"].create_index([("user_id", 1), ("triggered", 1)])
        await db["Alerts"].create_index([("triggered", 1), ("currency_from", 1)])
        await db["Portfolios"].create_index("user_id")
        await db["current_prices"].create_index("source")
        await db["current_prices"].create_index("updated_at")
        # Price history for volatility tracking
        await db["price_history"].create_index([("timestamp", -1)], expireAfterSeconds=7 * 24 * 3600)
        # Portfolio ticker indexes for volatility user lookups
        await db["Users"].create_index("portfolio.crypto.ticker")
        await db["Users"].create_index("portfolio.stock.ticker")
        log.info("Database indexes ensured")
    except Exception as exc:
        log.error("Failed to create indexes: %s", exc)


async def close_db() -> None:
    """Close the Motor client (call on shutdown)."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        log.info("MongoDB connection closed")


async def get_broadcast_audience_stats(db: AsyncIOMotorDatabase) -> dict:
    """
    Returns audience breakdown by language and premium status.
    
    Returns:
    {
        "total": 1234,
        "by_language": {"en": 800, "uk": 400},
        "premium": 156,
        "non_premium": 1078,
    }
    """
    users_collection = db["Users"]
    
    total = await users_collection.count_documents({})
    premium = await users_collection.count_documents({"Premium": True})
    
    pipeline = [
        {"$group": {"_id": "$Language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    by_language = {}
    async for doc in users_collection.aggregate(pipeline):
        lang_code = doc["_id"] or "unknown"
        by_language[lang_code] = doc["count"]
    
    return {
        "total": total,
        "by_language": by_language,
        "premium": premium,
        "non_premium": total - premium,
    }
