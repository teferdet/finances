"""
Write-side interceptor — every Mongo write becomes a domain event.

``app.db.get_db()`` returns an ``InterceptedDatabase`` that transparently wraps
the Motor database. Writes to *watched* collections publish events on the bus
**after** the write completes (also on failure — invalidating is always safe):

    Users                       → UserChanged(user_id | None)
    current_prices              → PricesUpdated()
    fiat_rates / fiat_rates_debug → FiatUpdated(currency | None)

This guarantees read-model consistency regardless of *where* in the codebase
a write happens, so handlers don't have to remember to invalidate caches.

Use ``get_raw_db()`` for high-volume writes that must NOT emit events
(e.g. the activity write-behind flusher touching ``last_active``).
"""

from __future__ import annotations

from typing import Any, Callable

from app.cqrs.bus import FiatUpdated, PricesUpdated, UserChanged, bus

WRITE_METHODS = frozenset(
    {
        "insert_one",
        "insert_many",
        "update_one",
        "update_many",
        "replace_one",
        "delete_one",
        "delete_many",
        "find_one_and_update",
        "find_one_and_replace",
        "find_one_and_delete",
        "bulk_write",
    }
)

# Methods whose first argument is a filter that targets a single document.
_SINGLE_DOC_FILTER_METHODS = frozenset(
    {"update_one", "replace_one", "delete_one", "find_one_and_update", "find_one_and_replace", "find_one_and_delete"}
)


def _extract_filter(method: str, args: tuple, kwargs: dict) -> dict | None:
    if method == "insert_one":
        doc = args[0] if args else kwargs.get("document")
        return doc if isinstance(doc, dict) else None
    if method in _SINGLE_DOC_FILTER_METHODS:
        flt = args[0] if args else kwargs.get("filter")
        return flt if isinstance(flt, dict) else None
    return None  # many-doc ops → "unknown"


def _scalar(value: Any) -> Any:
    """Return value only if it's a plain scalar key (not an operator dict like {'$in': [...]})."""
    return value if isinstance(value, (int, str)) and not isinstance(value, bool) else None


def _on_users_write(method: str, args: tuple, kwargs: dict) -> None:
    flt = _extract_filter(method, args, kwargs)
    uid = _scalar(flt.get("_id")) if flt else None
    bus.publish(UserChanged(user_id=uid if isinstance(uid, int) else None))


def _on_prices_write(method: str, args: tuple, kwargs: dict) -> None:
    bus.publish(PricesUpdated())


def _on_fiat_write(method: str, args: tuple, kwargs: dict) -> None:
    flt = _extract_filter(method, args, kwargs)
    code = _scalar(flt.get("currency")) if flt else None
    bus.publish(FiatUpdated(currency=code.upper() if isinstance(code, str) else None))


WATCHED: dict[str, Callable[[str, tuple, dict], None]] = {
    "Users": _on_users_write,
    "current_prices": _on_prices_write,
    "fiat_rates": _on_fiat_write,
    "fiat_rates_debug": _on_fiat_write,
}


class WatchedCollection:
    """Thin proxy over a Motor collection; write methods emit events after completion."""

    __slots__ = ("_coll", "_on_write")

    def __init__(self, coll: Any, on_write: Callable[[str, tuple, dict], None]) -> None:
        self._coll = coll
        self._on_write = on_write

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._coll, name)
        if name not in WRITE_METHODS:
            return attr

        on_write = self._on_write

        async def _write(*args: Any, **kwargs: Any) -> Any:
            try:
                return await attr(*args, **kwargs)
            finally:
                on_write(name, args, kwargs)

        return _write

    def __getitem__(self, name: str) -> Any:
        return self._coll[name]

    def __repr__(self) -> str:
        return f"WatchedCollection({self._coll!r})"


class InterceptedDatabase:
    """Proxy over AsyncIOMotorDatabase that wraps watched collections."""

    __slots__ = ("_db",)

    def __init__(self, db: Any) -> None:
        self._db = db

    @property
    def raw(self) -> Any:
        return self._db

    @staticmethod
    def _wrap(name: str, coll: Any) -> Any:
        handler = WATCHED.get(name)
        return WatchedCollection(coll, handler) if handler else coll

    def __getitem__(self, name: str) -> Any:
        return self._wrap(name, self._db[name])

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._db, name)
        return self._wrap(name, attr) if name in WATCHED else attr

    def get_collection(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._wrap(name, self._db.get_collection(name, *args, **kwargs))

    def __repr__(self) -> str:
        return f"InterceptedDatabase({self._db!r})"
