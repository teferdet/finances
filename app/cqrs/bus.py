"""
Live — lightweight in-process event bus.

Handlers are **synchronous** and must be cheap (cache invalidation, flag flips).
Anything slow should be scheduled from the handler via ``app.cqrs.tasks.spawn``.
A failing handler never breaks the publisher or other handlers.

Usage:
    from app.cqrs.bus import bus, UserChanged
    bus.subscribe(UserChanged, lambda ev: ...)
    bus.publish(UserChanged(user_id=123))
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

from app.logger import get_logger

log = get_logger("cqrs.bus")


# ── Events ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Event:
    pass


@dataclass(frozen=True, slots=True)
class UserChanged(Event):
    """A Users document changed. ``user_id=None`` means 'unknown / many users'."""

    user_id: Optional[int] = None


@dataclass(frozen=True, slots=True)
class PricesUpdated(Event):
    """current_prices collection changed."""


@dataclass(frozen=True, slots=True)
class FiatUpdated(Event):
    """fiat_rates changed. ``currency=None`` means 'unknown / many currencies'."""

    currency: Optional[str] = None


# ── Bus ─────────────────────────────────────────────────────────────

Handler = Callable[[Event], None]


class EventBus:
    __slots__ = ("_handlers", "published")

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)
        self.published: dict[str, int] = defaultdict(int)  # stats for /admin

    def subscribe(self, event_type: type, handler: Handler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass

    def publish(self, event: Event) -> None:
        self.published[type(event).__name__] += 1
        for handler in tuple(self._handlers.get(type(event), ())):
            try:
                handler(event)
            except Exception as exc:  # isolate handler failures
                log.warning("Event handler %r failed for %r: %s", handler, event, exc)


bus = EventBus()
