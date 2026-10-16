"""Stopping background tasks so they really stop.

`task.cancel()` followed by `await gather(...)` is not enough on Python 3.10: `asyncio.wait_for` can swallow a cancellation that arrives in the same
moment its inner future finishes (bpo-42130, fixed in 3.12), and the task then carries on as if nothing happened, so the `gather` waits forever and
the service never finishes stopping. `stop_tasks` cancels, waits a little, and cancels again for as long as something is still running.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable


async def stop_tasks(tasks: Iterable[asyncio.Task], *, patience: float = 1.0, tries: int = 6) -> None:
    pending = [t for t in tasks if not t.done()]
    for _ in range(tries):
        if not pending:
            return
        for t in pending:
            t.cancel()
        _, still = await asyncio.wait(pending, timeout=patience)
        pending = list(still)
    # whatever still will not stop is left to the event loop's own teardown; the caller must not wait on it forever
