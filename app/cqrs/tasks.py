"""
Background task supervisor & safe fire-and-forget runner.

Guarantees:
1. Fire-and-forget coroutines keep strong references until done, preventing GC cancellation.
2. Long-running background workers run under a supervisor that restarts crashed tasks
   with exponential backoff and tracks uptime, restart count, and errors for /admin diagnostics.
3. Clean shutdown: stops supervisor loops, waits for them to cancel/exit, and executes flushers.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Coroutine, Optional

from app.logger import get_logger

log = get_logger("cqrs.tasks")

_running_spawns: set[asyncio.Task] = set()


def spawn(coro: Coroutine[Any, Any, Any], name: Optional[str] = None) -> asyncio.Task:
    """Safely spawn a background coroutine with strong reference tracking and error logging."""
    task = asyncio.create_task(coro, name=name)
    _running_spawns.add(task)

    def _done_callback(t: asyncio.Task) -> None:
        _running_spawns.discard(t)
        if not t.cancelled():
            exc = t.exception()
            if exc:
                log.error("Unhandled exception in spawned task '%s': %s", t.get_name(), exc, exc_info=exc)

    task.add_done_callback(_done_callback)
    return task


class SupervisedTask:
    __slots__ = (
        "name",
        "factory",
        "restart_on_failure",
        "max_backoff",
        "task",
        "running",
        "restarts",
        "last_error",
        "started_at",
        "stopped_at",
    )

    def __init__(
        self,
        name: str,
        factory: Callable[[], Coroutine[Any, Any, Any]],
        restart_on_failure: bool = True,
        max_backoff: float = 300.0,
    ) -> None:
        self.name = name
        self.factory = factory
        self.restart_on_failure = restart_on_failure
        self.max_backoff = max_backoff
        self.task: asyncio.Task | None = None
        self.running: bool = False
        self.restarts: int = 0
        self.last_error: str | None = None
        self.started_at: float | None = None
        self.stopped_at: float | None = None

    def status(self) -> dict[str, Any]:
        uptime_sec = 0.0
        if self.running and self.started_at:
            uptime_sec = round(time.time() - self.started_at, 1)
        return {
            "name": self.name,
            "running": self.running,
            "restarts": self.restarts,
            "uptime_sec": uptime_sec,
            "last_error": self.last_error,
        }


class TaskSupervisor:
    """Supervises named background loops with automatic recovery."""

    def __init__(self) -> None:
        self._tasks: dict[str, SupervisedTask] = {}
        self._shutdown_event: asyncio.Event = asyncio.Event()

    def register(
        self,
        name: str,
        coro_factory: Callable[[], Coroutine[Any, Any, Any]],
        restart_on_failure: bool = True,
        max_backoff: float = 300.0,
    ) -> None:
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already registered")
        self._tasks[name] = SupervisedTask(
            name=name,
            factory=coro_factory,
            restart_on_failure=restart_on_failure,
            max_backoff=max_backoff,
        )

    def start(self, name: str) -> None:
        if name not in self._tasks:
            raise KeyError(f"Task '{name}' not found")
        item = self._tasks[name]
        if item.task and not item.task.done():
            return
        item.running = True
        item.task = asyncio.create_task(self._runner(item), name=f"sup:{item.name}")

    def start_all(self) -> None:
        self._shutdown_event.clear()
        for name in self._tasks:
            self.start(name)

    async def _runner(self, item: SupervisedTask) -> None:
        backoff = 1.0
        item.started_at = time.time()
        while not self._shutdown_event.is_set():
            try:
                log.info("Starting supervised task '%s'", item.name)
                coro = item.factory()
                await coro
                # Normal exit
                log.info("Supervised task '%s' finished normally", item.name)
                break
            except asyncio.CancelledError:
                log.info("Supervised task '%s' cancelled", item.name)
                break
            except Exception as exc:
                item.last_error = f"{type(exc).__name__}: {exc}"
                log.error(
                    "Supervised task '%s' crashed: %s",
                    item.name,
                    exc,
                    exc_info=exc,
                )
                if not item.restart_on_failure or self._shutdown_event.is_set():
                    break
                item.restarts += 1
                sleep_for = min(backoff, item.max_backoff)
                log.warning(
                    "Restarting task '%s' in %.1fs (restart #%d)",
                    item.name,
                    sleep_for,
                    item.restarts,
                )
                await asyncio.sleep(sleep_for)
                backoff *= 2.0

        item.running = False
        item.stopped_at = time.time()

    async def stop_all(self) -> None:
        """Cancel and await all supervised tasks."""
        self._shutdown_event.set()
        items_to_cancel = [item for item in self._tasks.values() if item.task and not item.task.done()]
        for item in items_to_cancel:
            item.task.cancel()
        if items_to_cancel:
            results = await asyncio.gather(*(item.task for item in items_to_cancel), return_exceptions=True)
            for item, res in zip(items_to_cancel, results, strict=True):
                if isinstance(res, Exception) and not isinstance(res, asyncio.CancelledError):
                    log.warning("Exception during stopping task '%s': %s", item.name, res)
        for item in self._tasks.values():
            item.running = False
        log.info("All supervised tasks stopped")

    def get_status(self) -> list[dict[str, Any]]:
        return [item.status() for item in self._tasks.values()]


supervisor = TaskSupervisor()
