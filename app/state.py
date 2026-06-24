"""
Global state module to hold in-memory dictionaries and avoid circular imports.
"""

from typing import Dict, Set
import asyncio

# Key: admin_id (int), Value: asyncio.Task
active_broadcast_tasks: Dict[int, asyncio.Task] = {}

# Set of dynamic admin IDs loaded from the DB
dynamic_admin_ids: Set[int] = set()
