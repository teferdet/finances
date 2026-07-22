"""
Repository for managing Telegram groups and their notification settings.
Single source of truth — all writes go to the lowercase 'groups' collection.
"""

from __future__ import annotations

from datetime import datetime
from app.db import get_db


# ── Default currency sets for new groups ─────────────────────────────────────
# These match the historical defaults from the old telebot-based versions.

DEFAULT_INPUT_CURRENCIES = [
    "USD",
    "EUR",
    "GBP",
    "CZK",
    "PLN",
    "CHF",
    "CNY",
    "UAH",
    "BTC",
    "ETH",
]

DEFAULT_OUTPUT_CURRENCIES = [
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "PLN",
    "CHF",
    "UAH",
]


async def upsert_group_from_chat_member(
    chat_id: int,
    title: str,
    group_type: str,
    added_by: int | None = None,
    community_id: str | None = None,
) -> None:
    """
    Called when the bot is added to (or re-added to) a chat.
    Creates the document if it doesn't exist; updates title/type if it does.
    Never overwrites existing notification settings.
    """
    db = get_db()
    now = datetime.utcnow()
    set_fields: dict = {
        "title": title,
        "type": group_type,
        "is_active": True,
        "updated_at": now,
    }
    if community_id is not None:
        set_fields["community_id"] = community_id

    await db["groups"].update_one(
        {"chat_id": chat_id},
        {
            "$set": set_fields,
            "$setOnInsert": {
                "chat_id": chat_id,
                "added_by_admin_id": added_by,
                "added_at": now,
                "community_id": community_id,
                "notifications": {
                    "errors": {
                        "enabled": False,
                        "min_level": "ERROR",
                    },
                    "analytics": {
                        "enabled": False,
                        "schedule": "daily",
                        "send_time": "09:00",
                        "timezone": "UTC",
                        "ephemeral": False,
                    },
                },
                "settings": {
                    "language": "en",
                    "auto_convert": True,
                    "mode": "auto",
                    "input_currencies": list(DEFAULT_INPUT_CURRENCIES),
                    "output_currencies": list(DEFAULT_OUTPUT_CURRENCIES),
                },
                "stats": {
                    "total_requests": 0,
                },
            },
        },
        upsert=True,
    )


async def add_group(chat_id: int, title: str, group_type: str, added_by: int) -> bool:
    """
    Add a new group manually (admin panel).
    Returns False if the group already exists.
    """
    db = get_db()
    existing = await db["groups"].find_one({"chat_id": chat_id})
    if existing:
        return False

    now = datetime.utcnow()
    await db["groups"].insert_one(
        {
            "chat_id": chat_id,
            "title": title,
            "type": group_type,
            "added_by_admin_id": added_by,
            "added_at": now,
            "updated_at": now,
            "is_active": True,
            "community_id": None,
            "notifications": {
                "errors": {
                    "enabled": False,
                    "min_level": "ERROR",
                },
                "analytics": {
                    "enabled": False,
                    "schedule": "daily",
                    "send_time": "09:00",
                    "timezone": "UTC",
                    "ephemeral": False,
                },
            },
            "settings": {
                "language": "en",
                "auto_convert": True,
                "mode": "auto",
                "input_currencies": list(DEFAULT_INPUT_CURRENCIES),
                "output_currencies": list(DEFAULT_OUTPUT_CURRENCIES),
            },
            "stats": {
                "total_requests": 0,
            },
        }
    )
    return True


async def remove_group(chat_id: int) -> bool:
    """Remove a group by chat_id."""
    db = get_db()
    result = await db["groups"].delete_one({"chat_id": chat_id})
    return result.deleted_count > 0


async def get_all_groups() -> list[dict]:
    """Get all groups, sorted by title."""
    db = get_db()
    cursor = db["groups"].find({}).sort("title", 1)
    return await cursor.to_list(length=None)


async def get_active_groups() -> list[dict]:
    """Get all active groups."""
    db = get_db()
    cursor = db["groups"].find({"is_active": True})
    return await cursor.to_list(length=None)


async def get_group(chat_id: int) -> dict | None:
    """Get a specific group by chat_id."""
    db = get_db()
    return await db["groups"].find_one({"chat_id": chat_id})


async def update_group_notifications(chat_id: int, notifications: dict) -> bool:
    """Update notification settings for a group."""
    db = get_db()
    result = await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {"notifications": notifications, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


async def toggle_group_active(chat_id: int, is_active: bool) -> bool:
    """Toggle the active status of a group."""
    db = get_db()
    result = await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


async def update_group_settings(chat_id: int, settings: dict) -> bool:
    """Update the group-level settings sub-document (language, auto_convert, etc.)."""
    db = get_db()
    result = await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {"settings": settings, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


async def get_group_settings(chat_id: int) -> dict:
    """Return the settings sub-document for a group, or defaults."""
    db = get_db()
    doc = await db["groups"].find_one({"chat_id": chat_id}, {"settings": 1})
    if doc and doc.get("settings"):
        return doc["settings"]
    return {
        "language": "en",
        "auto_convert": True,
        "mode": "auto",
        "input_currencies": list(DEFAULT_INPUT_CURRENCIES),
        "output_currencies": list(DEFAULT_OUTPUT_CURRENCIES),
    }


# ── Currency list helpers ────────────────────────────────────────────────────


async def update_group_currencies(chat_id: int, field: str, currencies: list[str]) -> bool:
    """
    Update input or output currency list for a group.

    Args:
        chat_id: Telegram chat ID
        field: Either 'input_currencies' or 'output_currencies'
        currencies: New list of currency codes
    """
    if field not in ("input_currencies", "output_currencies"):
        raise ValueError(f"Invalid field: {field}")
    db = get_db()
    result = await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {f"settings.{field}": currencies, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


# ── Stats helpers ────────────────────────────────────────────────────────────


async def increment_group_stats(chat_id: int) -> None:
    """Increment the total_requests counter for a group (fire-and-forget)."""
    db = get_db()
    await db["groups"].update_one(
        {"chat_id": chat_id},
        {"$inc": {"stats.total_requests": 1}},
    )
