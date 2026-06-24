"""
MongoDB backup service.
Creates a compressed mongodump archive and saves it locally to the backups/ folder.
Keeps only the last 7 backups to save disk space.
"""
import asyncio
import gzip
import logging
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from app.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

BACKUPS_DIR = PROJECT_ROOT / "backups"


async def daily_backup(mongo_uri: str) -> None:
    """
    Runs mongodump, compresses it to .gz, and saves it to the backups folder.
    """
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dump_dir = BACKUPS_DIR / f"dump_{timestamp}"
    archive_path = BACKUPS_DIR / f"backup_{timestamp}.gz"

    cmd = [
        "mongodump",
        f"--uri={mongo_uri}",
        f"--out={dump_dir}",
        "--quiet",
    ]

    try:
        logger.info("Starting local MongoDB backup...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"mongodump failed: {stderr.decode()}")

        # Archive the dump directory
        with gzip.open(archive_path, "wb") as gz_out:
            for root, _, files in os.walk(dump_dir):
                for file in files:
                    file_path = Path(root) / file
                    with open(file_path, "rb") as f:
                        gz_out.write(f.read())

        logger.info(f"Backup created successfully: {archive_path.name} ({archive_path.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        if archive_path.exists():
            archive_path.unlink()
    finally:
        # Cleanup the raw dump directory, keep only the .gz archive
        shutil.rmtree(dump_dir, ignore_errors=True)

        # Rotate old backups (keep last 7)
        try:
            backups = sorted(BACKUPS_DIR.glob("backup_*.gz"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
                    logger.info(f"Deleted old backup to free space: {old_backup.name}")
        except Exception as e:
            logger.warning(f"Failed to rotate old backups: {e}")


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
        logger.info(f"Next local MongoDB backup scheduled in {sleep_seconds:.0f} seconds (at {next_run} UTC).")
        
        await asyncio.sleep(sleep_seconds)
        await daily_backup(mongo_uri)
