"""
Resilience utilities — retry transient DB errors, circuit breaker for external APIs.
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable, Coroutine, TypeVar

from pymongo.errors import AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError

from app.logger import get_logger

log = get_logger("cqrs.resilience")

T = TypeVar("T")

TRANSIENT_DB_ERRORS = (
    AutoReconnect,
    NetworkTimeout,
    ServerSelectionTimeoutError,
    ConnectionResetError,
    TimeoutError,
)


def retry_transient(
    max_retries: int = 3,
    initial_delay: float = 0.2,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = TRANSIENT_DB_ERRORS,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator to retry an async function on transient network/database errors."""

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        log.warning(
                            "Operation %s failed after %d retries: %s",
                            func.__name__,
                            max_retries,
                            exc,
                        )
                        raise
                    log.debug(
                        "Transient error in %s (attempt %d/%d), retrying in %.2fs: %s",
                        func.__name__,
                        attempt,
                        max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff
            if last_exc:
                raise last_exc
            raise RuntimeError(f"Unexpected exit in retry_transient for {func.__name__}")

        return wrapper

    return decorator


class CircuitBreaker:
    """Simple Circuit Breaker pattern for external API calls (e.g., CMC, Yahoo, fx-rate)."""

    __slots__ = ("name", "failure_threshold", "recovery_time", "failure_count", "state", "last_failure_time")

    def __init__(self, name: str, failure_threshold: int = 5, recovery_time: float = 60.0) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_failure_time = 0.0

    def allow_request(self) -> bool:
        now = time.monotonic()
        if self.state == "OPEN":
            if now - self.last_failure_time > self.recovery_time:
                log.info("Circuit breaker [%s] transitioning from OPEN to HALF-OPEN", self.name)
                self.state = "HALF-OPEN"
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state != "CLOSED":
            log.info("Circuit breaker [%s] recovered, closing circuit", self.name)
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                log.warning(
                    "Circuit breaker [%s] tripped OPEN after %d failures. Pausing for %.0fs",
                    self.name,
                    self.failure_count,
                    self.recovery_time,
                )
            self.state = "OPEN"
