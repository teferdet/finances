"""
MongoDB backup service.
Creates a compressed JSON/BSON archive of all collections using the Motor driver.
Does NOT require mongodump to be installed.
Keeps only the last 7 backups to save disk space.
"""
import asyncio
import gzip
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from bson import ObjectId, Decimal128

from app.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

BACKUPS_DIR = PROJECT_ROOT / "backups"

# Collections to back up (in order)
BACKUP_COLLECTIONS = [
    "Users",
    "Groups",
    "groups",
    "Alerts",
    "Portfolios",
    "Settings",
    "fiat_rates",
    "current_prices",
    "price_history",
]


def _bson_to_json_safe(obj):
    """Recursively convert BSON types to JSON-serialisable Python types."""
    if isinstance(obj, dict):
        return {k: _bson_to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_bson_to_json_safe(v) for v in obj]
    if isinstance(obj, ObjectId):
        return {"$oid": str(obj)}
    if isinstance(obj, Decimal128):
        return {"$numberDecimal": str(obj)}
    if isinstance(obj, datetime):
        return {"$date": obj.isoformat()}
    if isinstance(obj, bytes):
        import base64
        return {"$binary": base64.b64encode(obj).decode()}
    return obj


async def daily_backup(mongo_uri: str) -> None:
    """
    Exports all MongoDB collections to JSON and saves a gzip archive in the backups folder.
    Uses Motor (async) — no external tools required.
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import get_settings

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_path = BACKUPS_DIR / f"backup_{timestamp}.gz"

    settings = get_settings()

    try:
        logger.info("Starting native MongoDB backup...")

        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=30_000)
        db = client[settings.database.mongo_database]

        backup_data: dict = {
            "_meta": {
                "created_at": datetime.utcnow().isoformat(),
                "database": settings.database.mongo_database,
                "version": settings.bot.version,
            }
        }

        total_docs = 0
        for collection_name in BACKUP_COLLECTIONS:
            try:
                docs = await db[collection_name].find({}).to_list(length=None)
                backup_data[collection_name] = [_bson_to_json_safe(doc) for doc in docs]
                total_docs += len(docs)
                logger.debug("  Backed up %d docs from '%s'", len(docs), collection_name)
            except Exception as col_err:
                logger.warning("  Skipped collection '%s': %s", collection_name, col_err)
                backup_data[collection_name] = []

        client.close()

        # Write compressed JSON archive
        json_bytes = json.dumps(backup_data, ensure_ascii=False, indent=None).encode("utf-8")
        with gzip.open(archive_path, "wb") as gz_out:
            gz_out.write(json_bytes)

        size_kb = archive_path.stat().st_size / 1024
        logger.info(
            "Backup created: %s (%.1f KB, %d documents across %d collections)",
            archive_path.name, size_kb, total_docs, len(BACKUP_COLLECTIONS),
        )

    except Exception as e:
        logger.error("Backup failed: %s", e, exc_info=True)
        if archive_path.exists():
            archive_path.unlink()

    finally:
        # Rotate old backups — keep last 7
        try:
            backups = sorted(BACKUPS_DIR.glob("backup_*.gz"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
                    logger.info("Deleted old backup: %s", old_backup.name)
        except Exception as e:
            logger.warning("Failed to rotate old backups: %s", e)


async def run_daily_backup_loop(mongo_uri: str) -> None:
    """
    Custom asyncio loop to run the local backup every day at 03:00 UTC.
    """
    while True:
        now = datetime.utcnow()
        # Calculate next run time (03:00 UTC)
        next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)

        sleep_seconds = (next_run - now).total_seconds()
        logger.info(
            "Next MongoDB backup scheduled in %.0f seconds (at %s UTC).",
            sleep_seconds, next_run,
        )

        await asyncio.sleep(sleep_seconds)
        await daily_backup(mongo_uri)
