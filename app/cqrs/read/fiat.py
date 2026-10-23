"""
In-memory FiatRates read model.

Caches rates and timestamps of fiat currency documents to serve currency conversions
and staleness checks in microseconds directly from memory.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.cqrs.bus import FiatUpdated, bus
from app.cqrs.resilience import retry_transient
from app.logger import get_logger

log = get_logger("cqrs.read.fiat")


class FiatRatesStore:
    def __init__(self, ttl_sec: float = 3600.0) -> None:
        self._rates_cache: dict[str, dict[str, Any]] = {}  # CODE -> {"rates": dict, "updated_at": datetime, "loaded_at": float}
        self._lock = asyncio.Lock()
        self._ttl_sec = ttl_sec
        bus.subscribe(FiatUpdated, self._on_fiat_updated)

    def _on_fiat_updated(self, event: FiatUpdated) -> None:
        if event.currency is None:
            log.debug("FiatUpdated: invalidating all fiat rates cache")
            self._rates_cache.clear()
        else:
            self._rates_cache.pop(event.currency.upper(), None)
            log.debug("FiatUpdated: invalidated fiat rates cache for %s", event.currency)

    async def get_currency_doc(self, code: str) -> Optional[dict[str, Any]]:
        code = code.upper()
        now = time.monotonic()
        entry = self._rates_cache.get(code)
        if entry and (now - entry["loaded_at"] < self._ttl_sec):
            return entry

        doc = await self._fetch_doc(code)
        if doc:
            updated_at = doc.get("updated_at")
            if updated_at and updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)

            stored = {
                "currency": code,
                "rates": doc.get("rates", {}),
                "updated_at": updated_at,
                "loaded_at": now,
            }
            self._rates_cache[code] = stored
            return stored
        return None

    @retry_transient(max_retries=2, initial_delay=0.1)
    async def _fetch_doc(self, code: str) -> Optional[dict[str, Any]]:
        from app.db import get_fiat_collection_name, get_raw_db

        raw_db = get_raw_db()
        return await raw_db[get_fiat_collection_name()].find_one({"currency": code})

    async def is_stale(self, code: str, ttl_hours: int = 5) -> bool:
        entry = await self.get_currency_doc(code)
        if not entry or not entry.get("updated_at"):
            return True
        updated: datetime = entry["updated_at"]
        return (datetime.now(timezone.utc) - updated) > timedelta(hours=ttl_hours)

    async def get_rate(self, base: str, target: str) -> Optional[dict[str, Any]]:
        doc = await self.get_currency_doc(base)
        if doc and "rates" in doc:
            return doc["rates"].get(target.upper())
        return None


fiat_store = FiatRatesStore()
