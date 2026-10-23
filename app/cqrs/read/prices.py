"""
In-memory PriceSnapshot read model.

Replaces full collection scans of `current_prices` (which were occurring every 60s/300s
and on every portfolio view) with an in-RAM snapshot kept fresh via `PricesUpdated` events.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from app.cqrs.bus import PricesUpdated, bus
from app.cqrs.resilience import retry_transient
from app.logger import get_logger

log = get_logger("cqrs.read.prices")


class PriceSnapshotStore:
    def __init__(self, refresh_interval_sec: float = 600.0) -> None:
        self._prices: dict[str, float] = {}
        self._last_loaded: float = 0.0
        self._lock = asyncio.Lock()
        self._refresh_interval_sec = refresh_interval_sec
        # Subscribe to bus events
        bus.subscribe(PricesUpdated, self._on_prices_updated)

    def _on_prices_updated(self, event: PricesUpdated) -> None:
        # Schedule reload in background task so sync bus handler returns immediately
        from app.cqrs.tasks import spawn

        spawn(self.reload(), name="price_snapshot_reload")

    async def get_price(self, ticker: str) -> Optional[float]:
        await self._ensure_loaded()
        return self._prices.get(ticker.upper())

    async def get_all_prices(self) -> dict[str, float]:
        await self._ensure_loaded()
        return dict(self._prices)

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        await self._ensure_loaded()
        return {t.upper(): self._prices[t.upper()] for t in tickers if t.upper() in self._prices}

    async def _ensure_loaded(self) -> None:
        now = time.monotonic()
        if not self._prices or (now - self._last_loaded > self._refresh_interval_sec):
            await self.reload()

    @retry_transient(max_retries=2, initial_delay=0.1)
    async def reload(self) -> dict[str, float]:
        async with self._lock:
            from app.db import get_raw_db

            raw_db = get_raw_db()
            cursor = raw_db["current_prices"].find({}, {"price_usd": 1})
            new_prices: dict[str, float] = {}
            async for doc in cursor:
                price = doc.get("price_usd")
                if price is not None:
                    try:
                        new_prices[str(doc["_id"]).upper()] = float(price)
                    except (ValueError, TypeError):
                        pass

            self._prices = new_prices
            self._last_loaded = time.monotonic()
            log.debug("PriceSnapshotStore reloaded: %d prices in memory", len(self._prices))
            return dict(self._prices)

    def stats(self) -> dict:
        return {
            "cached_tickers": len(self._prices),
            "age_sec": round(time.monotonic() - self._last_loaded, 1) if self._last_loaded else None,
        }


price_store = PriceSnapshotStore()


async def get_price_snapshot() -> dict[str, float]:
    """Return dictionary of {TICKER: price_usd} from memory."""
    return await price_store.get_all_prices()


async def get_ticker_price(ticker: str) -> Optional[float]:
    """Return price in USD for ticker from memory."""
    return await price_store.get_price(ticker)
