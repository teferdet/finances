"""
Helpers for scanning log files without blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path


def _count_lines_sync(path: Path, prefixes: tuple[str, ...], contains: str | None) -> int:
    if not path.exists():
        return 0
    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:  # streamed — never loads the whole file into memory
            if line.startswith(prefixes) and (contains is None or contains in line):
                count += 1
    return count


async def count_log_lines(path: Path, prefixes: str | tuple[str, ...], contains: str | None = None) -> int:
    """
    Count lines in ``path`` starting with any of ``prefixes`` (and containing ``contains``
    if given). Runs in a worker thread. Returns 0 if the file is missing or unreadable.
    """
    if isinstance(prefixes, str):
        prefixes = (prefixes,)
    try:
        return await asyncio.to_thread(_count_lines_sync, path, prefixes, contains)
    except OSError:
        return 0
