"""
Read model for Users.

Features:
1. In-memory cache with 5-minute TTL.
2. Single-flight locking to collapse concurrent reads for the same user into 1 query.
3. Automatically invalidated on `UserChanged` event from the bus.
4. Stale-on-error fallback if MongoDB has transient issues.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.cqrs.bus import UserChanged, bus
from app.cqrs.resilience import retry_transient
from app.logger import get_logger

log = get_logger("cqrs.read.users")


@dataclass(slots=True)
class UserView:
    id: int
    language: str = "en"
    base_currency: str = "USD"
    rate_mode: str = "direct"
    portfolio_view: str = "detailed"
    weekly_digest: bool = True
    number_format: str = "commas"
    volatility_threshold: int = 5
    main_menu: list[str] = field(default_factory=list)
    big_buttons: bool = False
    fiat_currencies: list[str] = field(default_factory=list)
    crypto_currencies: list[str] = field(default_factory=list)
    stocks: list[str] = field(default_factory=list)
    portfolio: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_doc(cls, uid: int, doc: dict[str, Any] | None) -> UserView:
        if not doc:
            return cls(id=uid)

        base_curr = doc.get("BaseCurrency") or "USD"
        if isinstance(base_curr, list):
            base_curr = base_curr[0] if base_curr else "USD"

        v_thresh = doc.get("VolatilityThreshold")
        if v_thresh is None:
            v_thresh = doc.get("volatility_threshold_pct", 5)

        return cls(
            id=uid,
            language=doc.get("Language") or "en",
            base_currency=str(base_curr),
            rate_mode=doc.get("RateMode") or "direct",
            portfolio_view=doc.get("PortfolioView") or "detailed",
            weekly_digest=bool(doc.get("WeeklyDigest", True)),
            number_format=doc.get("NumberFormat") or "commas",
            volatility_threshold=int(v_thresh),
            main_menu=list(doc.get("MainMenu") or []),
            big_buttons=bool(doc.get("BigButtons", False)),
            fiat_currencies=list(doc.get("Fiat currency") or []),
            crypto_currencies=list(doc.get("Crypto currency") or []),
            stocks=list(doc.get("Stocks") or []),
            portfolio=dict(doc.get("portfolio") or {}) if isinstance(doc.get("portfolio"), dict) else {},
            raw=doc,
        )


class UserViewStore:
    def __init__(self, ttl_sec: float = 300.0) -> None:
        self._cache: dict[int, tuple[UserView, float]] = {}  # uid -> (view, expires_at)
        self._flights: dict[int, asyncio.Future[UserView]] = {}
        self._lock = asyncio.Lock()
        self._ttl_sec = ttl_sec
        # Subscribe to bus events
        bus.subscribe(UserChanged, self._on_user_changed)

    def _on_user_changed(self, event: UserChanged) -> None:
        if event.user_id is None:
            log.debug("Invalidating all user view caches")
            self._cache.clear()
        else:
            if self._cache.pop(event.user_id, None) is not None:
                log.debug("Invalidated user view cache for uid=%s", event.user_id)

    def invalidate(self, user_id: int | None = None) -> None:
        if user_id is None:
            self._cache.clear()
        else:
            self._cache.pop(user_id, None)

    async def get(self, user_id: int) -> UserView:
        now = time.monotonic()
        entry = self._cache.get(user_id)
        if entry:
            view, expires_at = entry
            if now < expires_at:
                return view

        # Single-flight deduplication for concurrent requests for same user
        flight: asyncio.Future[UserView] | None = None
        async with self._lock:
            flight = self._flights.get(user_id)
            if flight is None:
                flight = asyncio.get_running_loop().create_future()
                self._flights[user_id] = flight
                is_leader = True
            else:
                is_leader = False

        if not is_leader:
            return await flight

        # Leader fetches from DB
        try:
            view = await self._fetch_from_db(user_id)
            self._cache[user_id] = (view, now + self._ttl_sec)
            flight.set_result(view)
            return view
        except Exception as exc:
            # Stale-on-error fallback
            if entry:
                log.warning("DB fetch failed for user %d, serving stale cached view: %s", user_id, exc)
                flight.set_result(entry[0])
                return entry[0]
            flight.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._flights.pop(user_id, None)

    @retry_transient(max_retries=2, initial_delay=0.1)
    async def _fetch_from_db(self, user_id: int) -> UserView:
        from app.db import get_raw_db

        raw_db = get_raw_db()
        doc = await raw_db["Users"].find_one({"_id": user_id})
        return UserView.from_doc(user_id, doc)


user_view_store = UserViewStore()


async def get_user_view(user_id: int) -> UserView:
    """Public helper to get the cached UserView."""
    return await user_view_store.get(user_id)
