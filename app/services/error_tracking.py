"""
Error tracking for data sources.
"""
from datetime import datetime, timezone
from app.db import get_db

async def report_source_error(source_name: str, error_msg: str) -> None:
    db = get_db()
    # Truncate error message to prevent huge logs in DB
    if len(error_msg) > 500:
        error_msg = error_msg[:497] + "..."

    await db["ProblematicSources"].update_one(
        {"_id": source_name},
        {
            "$set": {
                "last_error": error_msg,
                "updated_at": datetime.now(timezone.utc),
                "resolved": False
            },
            "$inc": {"error_count": 1},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
        },
        upsert=True
    )

async def clear_source_error(source_name: str) -> None:
    db = get_db()
    await db["ProblematicSources"].update_one(
        {"_id": source_name},
        {"$set": {"resolved": True, "updated_at": datetime.now(timezone.utc)}}
    )

async def get_active_errors() -> list[dict]:
    db = get_db()
    cursor = db["ProblematicSources"].find({"resolved": False}).sort("updated_at", -1)
    return await cursor.to_list(length=100)
