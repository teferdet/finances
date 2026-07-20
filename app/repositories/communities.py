"""
Community Repository — Bot API 10.2

Stores community metadata and the mapping of groups to their parent community.
Communities are Telegram's concept of multiple supergroups/channels/bots
grouped under a single organizational entity.

Collection: 'communities'
Document schema:
    {
        "community_id": str,   # Telegram Community ID
        "name": str,
        "discovered_at": datetime,
        "group_chat_ids": [int, ...]
    }
"""

from __future__ import annotations

from datetime import datetime

from app.db import get_db
from app.logger import get_logger

log = get_logger("communities")


async def get_or_create_community(community_id: str, name: str) -> dict:
    """
    Upsert a community record. Creates it if it doesn't exist yet.
    Returns the final community document.
    """
    db = get_db()
    await db["communities"].update_one(
        {"community_id": community_id},
        {
            "$set": {"name": name, "updated_at": datetime.utcnow()},
            "$setOnInsert": {
                "community_id": community_id,
                "discovered_at": datetime.utcnow(),
                "group_chat_ids": [],
            },
        },
        upsert=True,
    )
    doc = await db["communities"].find_one({"community_id": community_id})
    return doc or {}


async def add_group_to_community(chat_id: int, community_id: str) -> None:
    """
    Register that a group (chat_id) belongs to a community.
    Updates both the community's group_chat_ids list and the group's community_id.
    """
    db = get_db()
    # Add to community's group list (avoid duplicates)
    await db["communities"].update_one(
        {"community_id": community_id},
        {"$addToSet": {"group_chat_ids": chat_id}},
    )
    # Tag the group document with its community
    await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {"community_id": community_id, "updated_at": datetime.utcnow()}},
    )
    log.info("Group %d linked to community %s", chat_id, community_id)


async def remove_group_from_community(chat_id: int, community_id: str) -> None:
    """Remove a group from a community (e.g. when bot leaves)."""
    db = get_db()
    await db["communities"].update_one(
        {"community_id": community_id},
        {"$pull": {"group_chat_ids": chat_id}},
    )
    await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$unset": {"community_id": ""}, "$set": {"updated_at": datetime.utcnow()}},
    )


async def get_community(community_id: str) -> dict | None:
    """Get a community document by its ID."""
    db = get_db()
    return await db["communities"].find_one({"community_id": community_id})


async def get_community_groups(community_id: str) -> list[dict]:
    """
    Return all group documents that belong to a given community.
    Useful for community-wide broadcasts or analytics aggregation.
    """
    db = get_db()
    cursor = db["groups"].find({"community_id": community_id})
    return await cursor.to_list(length=None)


async def get_group_community(chat_id: int) -> str | None:
    """Return the community_id for a group, or None if it's not in a community."""
    db = get_db()
    doc = await db["groups"].find_one({"chat_id": chat_id}, {"community_id": 1})
    return doc.get("community_id") if doc else None


async def list_all_communities() -> list[dict]:
    """Return all known communities, sorted by name."""
    db = get_db()
    cursor = db["communities"].find({}).sort("name", 1)
    return await cursor.to_list(length=None)
