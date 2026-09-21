"""Engine-side scheduled work, all on the event loop (spec 7.5, Events -> polled/evaluated).

Consumers:
  * Task deadlines (soft + final) -- scheduled Events, not a separate scheduler
  * Traversal Time Limit expiry -- ends the session and releases the block
  * Polled/threshold Event definitions (idle duration, resource thresholds, scheduled time)
  * Audit retention job (daily)
  * Flow polling fallback where native events are unavailable

Native/pushed events never come through here; they arrive as worker-client messages and are matched
by `engine.control.events`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

Job = Callable[[], Awaitable[None]]


class Scheduler:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._periodic: list[tuple[str, float, Job]] = []

    def every(self, name: str, seconds: float, job: Job) -> None:
        """Register a periodic job. Must be called before `start()`."""
        self._periodic.append((name, seconds, job))

    def at(self, name: str, when: datetime, job: Job) -> None:
        """Schedule a one-shot job (e.g. a Task deadline). Replaces any job with the same name."""
        self.cancel(name)
        delay = max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        self._tasks[name] = asyncio.create_task(self._run_once(name, delay, job))

    def cancel(self, name: str) -> None:
        task = self._tasks.pop(name, None)
        if task is not None:
            task.cancel()

    async def start(self) -> None:
        self.every("audit.retention", 24 * 3600, self.engine.audit.run_retention)
        self.every("sessions.expire", 5.0, self._expire_sessions)
        self.every("control.polled", float(self.engine.settings.control_poll_seconds), self._evaluate_polled)
        self.every("alerts.deliver", 30.0, self._deliver_alerts)
        for name, seconds, job in self._periodic:
            self._tasks[name] = asyncio.create_task(self._run_periodic(name, seconds, job))
        log.info("scheduler started with %d periodic jobs", len(self._periodic))

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    # --- internals ------------------------------------------------------------------------------

    async def _run_once(self, name: str, delay: float, job: Job) -> None:
        await asyncio.sleep(delay)
        try:
            await job()
        except Exception:
            log.exception("scheduled job %s failed", name)
        finally:
            self._tasks.pop(name, None)

    async def _run_periodic(self, name: str, seconds: float, job: Job) -> None:
        while True:
            await asyncio.sleep(seconds)
            try:
                await job()
            except Exception:
                log.exception("periodic job %s failed", name)

    async def _expire_sessions(self) -> None:
        """Traversal Time Limit / network-drop expiry: same deadline, same release path."""
        from engine.hierarchy import traversal

        await traversal.expire_due_sessions(self.engine)

    async def _evaluate_polled(self) -> None:
        from engine.control import events

        await events.evaluate_polled(self.engine)

    async def _deliver_alerts(self) -> None:
        from engine.hierarchy import alerts

        await alerts.deliver_due(self.engine)
