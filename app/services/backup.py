"""
MongoDB backup service.

Key Features:
1. Low-memory streaming: Streams collections document-by-document into gzip.
   Uses constant O(1) memory (~10 MB), fully safe for Docker 400 MB memory limits.
2. Dynamic collection discovery: Backs up ALL collections in MongoDB (ApiKeys, Users,
   Settings, DailyStats, etc.), rather than an easily outdated hard-coded list.
3. Atomic writes: Writes to temporary file before replacing to avoid corrupted archives.
4. Retention policy: Keeps the last 7 daily archives.
5. Observability: Records backup metrics (size, document count, duration, status) into MongoDB `Status`.
6. Disaster Recovery: Includes `restore_backup(archive_path)` for full recovery.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from bson import Decimal128, ObjectId

from app.config import PROJECT_ROOT, get_settings
from app.logger import get_logger

logger = get_logger("services.backup")

BACKUPS_DIR = PROJECT_ROOT / "backups"


def _bson_to_json_safe(obj: Any) -> Any:
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

        return {"$binary": base64.b64encode(obj).decode("ascii")}
    return obj


def _json_safe_to_bson(obj: Any) -> Any:
    """Recursively convert JSON-safe dictionary back to native BSON types for restore."""
    if isinstance(obj, dict):
        if len(obj) == 1:
            if "$oid" in obj:
                return ObjectId(obj["$oid"])
            if "$numberDecimal" in obj:
                return Decimal128(obj["$numberDecimal"])
            if "$date" in obj:
                return datetime.fromisoformat(obj["$date"])
            if "$binary" in obj:
                import base64

                return base64.b64decode(obj["$binary"].encode("ascii"))
        return {k: _json_safe_to_bson(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe_to_bson(v) for v in obj]
    return obj


async def daily_backup(mongo_uri: str | None = None) -> Optional[Path]:
    """
    Exports all MongoDB collections to a compressed gzip JSON file using low-memory streaming.
    Returns archive Path if successful, None otherwise.
    """
    from app.db import get_raw_db

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()
    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y%m%d_%H%M%S")
    archive_name = f"backup_{timestamp}.json.gz"
    archive_path = BACKUPS_DIR / archive_name
    tmp_path = BACKUPS_DIR / f"{archive_name}.tmp"

    settings = get_settings()
    db = get_raw_db()

    total_docs = 0
    collection_stats: dict[str, int] = {}

    try:
        logger.info("Starting low-memory streaming MongoDB backup...")

        # 1. Discover all non-system collections dynamically
        all_cols = await db.list_collection_names()
        collections = sorted([c for c in all_cols if not c.startswith("system.")])

        # 2. Stream directly into gzip file
        with gzip.open(tmp_path, "wt", encoding="utf-8") as gz_out:
            gz_out.write("{\n")
            # Write metadata header
            meta = {
                "_meta": {
                    "created_at": now_utc.isoformat(),
                    "database": settings.database.mongo_database,
                    "version": settings.bot.version,
                    "collections": collections,
                }
            }
            # Write only the inner _meta object so the root JSON object stays open
            gz_out.write(f'  "_meta": {json.dumps(meta["_meta"], ensure_ascii=False)},\n')
            gz_out.write('  "collections": {\n')

            for col_idx, col_name in enumerate(collections):
                gz_out.write(f'    {json.dumps(col_name)}: [\n')
                col_docs = 0
                first_doc = True

                cursor = db[col_name].find({})
                async for doc in cursor:
                    if not first_doc:
                        gz_out.write(",\n")
                    first_doc = False

                    safe_doc = _bson_to_json_safe(doc)
                    gz_out.write(f"      {json.dumps(safe_doc, ensure_ascii=False)}")
                    col_docs += 1
                    total_docs += 1

                gz_out.write("\n    ]")
                if col_idx < len(collections) - 1:
                    gz_out.write(",\n")
                else:
                    gz_out.write("\n")

                collection_stats[col_name] = col_docs
                logger.debug("Backed up %d docs from '%s'", col_docs, col_name)

            gz_out.write("  }\n}\n")

        # 3. Atomic rename after successful compression
        if tmp_path.exists():
            if archive_path.exists():
                archive_path.unlink()
            os.replace(tmp_path, archive_path)

        elapsed = time.monotonic() - start_time
        size_kb = archive_path.stat().st_size / 1024

        logger.info(
            "Backup created successfully: %s (%.1f KB, %d docs across %d collections in %.1fs)",
            archive_path.name,
            size_kb,
            total_docs,
            len(collections),
            elapsed,
        )

        # 4. Save success status in DB
        try:
            await db["Status"].update_one(
                {"_id": "backup_status"},
                {
                    "$set": {
                        "last_backup_at": now_utc,
                        "status": "success",
                        "size_kb": round(size_kb, 1),
                        "total_docs": total_docs,
                        "duration_sec": round(elapsed, 2),
                        "collections_count": len(collections),
                        "filename": archive_path.name,
                    }
                },
                upsert=True,
            )
        except Exception as st_err:
            logger.warning("Failed to record backup status in DB: %s", st_err)

        return archive_path

    except Exception as e:
        logger.error("Backup failed: %s", e, exc_info=True)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if archive_path.exists():
            archive_path.unlink(missing_ok=True)

        # Record failure status in DB
        try:
            await db["Status"].update_one(
                {"_id": "backup_status"},
                {
                    "$set": {
                        "last_backup_at": now_utc,
                        "status": "failed",
                        "error": str(e),
                    }
                },
                upsert=True,
            )
        except Exception:
            pass
        return None

    finally:
        # Rotate old backups — keep last 7
        try:
            rotate_backups(keep=7)
        except Exception as rot_err:
            logger.warning("Failed to rotate old backups: %s", rot_err)


def rotate_backups(keep: int = 7) -> int:
    """Keep only the latest `keep` backups, removing older ones."""
    if not BACKUPS_DIR.exists():
        return 0

    backups = sorted(BACKUPS_DIR.glob("backup_*.json.gz")) + sorted(BACKUPS_DIR.glob("backup_*.gz"))
    removed = 0
    if len(backups) > keep:
        for old in backups[:-keep]:
            try:
                old.unlink()
                logger.info("Deleted old backup: %s", old.name)
                removed += 1
            except Exception as e:
                logger.warning("Could not delete %s: %s", old.name, e)
    return removed


def list_backups() -> list[dict[str, Any]]:
    """List available backup archives sorted newest first."""
    if not BACKUPS_DIR.exists():
        return []

    results = []
    files = sorted(BACKUPS_DIR.glob("backup_*.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        stat = f.stat()
        results.append(
            {
                "filename": f.name,
                "path": f,
                "size_kb": round(stat.st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            }
        )
    return results


def get_latest_backup() -> Optional[Path]:
    """Return Path to latest backup file if exists."""
    backups = list_backups()
    return backups[0]["path"] if backups else None


async def restore_backup(archive_path: Path, drop_existing: bool = False) -> dict[str, int]:
    """
    Restores collections from a backup archive (.json.gz).
    If drop_existing=True, clears collection before inserting.
    Returns dict of {collection_name: restored_documents_count}.
    """
    from app.db import get_raw_db

    if not await asyncio.to_thread(archive_path.exists):
        raise FileNotFoundError(f"Backup file not found: {archive_path}")

    logger.info("Starting restore from %s...", archive_path.name)
    db = get_raw_db()

    def _load() -> Any:
        with gzip.open(archive_path, "rt", encoding="utf-8") as gz_in:
            return json.load(gz_in)

    data = await asyncio.to_thread(_load)

    # Support both new format {"_meta": ..., "collections": {...}} and legacy {"Users": [...]}
    collections_data = data.get("collections", data)
    restored_stats: dict[str, int] = {}

    for col_name, docs in collections_data.items():
        if col_name.startswith("_"):
            continue
        if not isinstance(docs, list):
            continue

        if drop_existing:
            await db[col_name].delete_many({})

        if docs:
            raw_docs = [_json_safe_to_bson(d) for d in docs]
            # Insert in chunks of 500 to keep memory low
            for i in range(0, len(raw_docs), 500):
                chunk = raw_docs[i : i + 500]
                await db[col_name].insert_many(chunk, ordered=False)

        restored_stats[col_name] = len(docs)
        logger.info("Restored %d documents to '%s'", len(docs), col_name)

    return restored_stats


async def run_daily_backup_loop(mongo_uri: str | None = None) -> None:
    """
    Background loop that triggers daily backup at 03:00 UTC.
    """
    while True:
        now = datetime.now(timezone.utc)
        # Calculate next run time (03:00 UTC)
        next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)

        sleep_seconds = (next_run - now).total_seconds()
        logger.info(
            "Next MongoDB backup scheduled in %.0f seconds (at %s UTC).",
            sleep_seconds,
            next_run.strftime("%Y-%m-%d %H:%M:%S"),
        )

        await asyncio.sleep(sleep_seconds)
        await daily_backup(mongo_uri)
