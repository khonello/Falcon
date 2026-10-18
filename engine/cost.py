"""What work really costs here, and how much room the Engine has right now (measured, not assumed).

An estimate that says "about two minutes" should be built from how long this Engine actually took for the last such job on this hardware, and should say so when the Engine is busy. So
the jobs that matter (tracking a marked file, ...) report how long they took and for how many units, and this keeps a moving average; and a small probe measures how late the Engine's
own event loop is running. Nothing here needs Windows: the load average is read where the OS has one, and left out where it has not (the Engine deploys on Linux).
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

ALPHA = 0.3                    # how much the newest job counts against the history
LAG_PROBE = 0.05


class Cost:
    def __init__(self) -> None:
        self._per_unit: dict[str, tuple[float, int]] = {}      # kind -> (seconds per unit, how many jobs it is built from)
        self.lag_ms = 0.0                                       # how late the Engine's loop runs, smoothed

    def observe(self, kind: str, seconds: float, units: int) -> None:
        """A job took `seconds` for `units` of something (files tracked, rows written ...)."""
        if units <= 0 or seconds < 0:
            return
        per = seconds / units
        old, n = self._per_unit.get(kind, (per, 0))
        self._per_unit[kind] = (per if n == 0 else old + ALPHA * (per - old), n + 1)

    def per_unit(self, kind: str, assumed: float) -> tuple[float, int]:
        """(seconds a unit takes, how many jobs that is measured from). Nothing measured yet: the assumption, and 0."""
        got = self._per_unit.get(kind)
        return (got[0], got[1]) if got else (assumed, 0)

    async def probe(self) -> float:
        """Measure how late a very short sleep wakes: a loop with a lot to do wakes late."""
        began = time.perf_counter()
        await asyncio.sleep(LAG_PROBE)
        late = max(0.0, (time.perf_counter() - began - LAG_PROBE) * 1000.0)
        self.lag_ms = late if self.lag_ms == 0.0 else self.lag_ms + ALPHA * (late - self.lag_ms)
        return late

    def capacity(self) -> dict[str, Any]:
        """The room there is now: processors, the load per processor (where the OS says), how late the loop runs, and one word for it."""
        cpus = os.cpu_count() or 1
        load: float | None = None
        try:
            load = round(os.getloadavg()[0] / cpus, 2)
        except (AttributeError, OSError):
            load = None                                        # not on every OS
        busy = (load is not None and load > 1.5) or self.lag_ms > 250.0
        quiet = (load is None or load < 0.7) and self.lag_ms < 60.0
        return {"cpus": cpus, "load_per_cpu": load, "loop_lag_ms": round(self.lag_ms, 1), "state": "busy" if busy else "quiet" if quiet else "moderate"}

    def slowdown(self) -> float:
        """How much longer than measured a job is likely to take now: 1.0 when quiet, more when the Engine is already busy."""
        state = self.capacity()
        if state["state"] == "busy":
            return 2.5
        return 1.4 if state["state"] == "moderate" else 1.0
