"""The service's side of the indexer and the tracker when they run as their own programs.

These stand in for `Watcher` and `OsSignals` with the same few calls the service and the narrow UI make on them, so the rest of
the service does not know the difference. Each one starts a supervised child (`childproc.Supervised`) and passes what the child
asks of the Engine through the service's own connection.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from worker_client.childproc import Supervised

log = logging.getLogger(__name__)

Call = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
Unhealthy = Callable[[str, bool], None]


class IsolatedWatcher:
    def __init__(self, roots: list[str], call: Call, *, poll_seconds: float, hash_limit: int, idle_after: float,
                 native: bool, on_unhealthy: Unhealthy | None = None, state_path: Any = None, reconcile_seconds: float = 1800.0) -> None:
        cfg = {"roots": roots, "poll_seconds": poll_seconds, "hash_limit": hash_limit, "idle_after": idle_after, "native": native,
               "state_path": str(state_path) if state_path else None, "reconcile_seconds": reconcile_seconds}
        self.child = Supervised("indexer", "worker_client.indexer", [json.dumps(cfg)], call, on_unhealthy=on_unhealthy)

    @property
    def mode(self) -> str:
        return str(self.child.state.get("mode") or ("off" if self.child.running else "stopped"))

    @property
    def events_reported(self) -> int:
        return int(self.child.state.get("events_reported") or 0)

    @property
    def sweeps_completed(self) -> int:
        return int(self.child.state.get("sweeps_completed") or 0)

    async def start(self) -> None:
        await self.child.start()

    async def stop(self) -> None:
        await self.child.stop()

    async def sweep(self) -> int:
        res = await self.child.command("sweep", timeout=3600)
        return int(res.get("n") or 0)

    async def reconcile(self) -> dict[str, Any]:
        if not self.child.running:
            return {"skipped": True}
        return await self.child.command("reconcile", timeout=3600)


class IsolatedSignals:
    def __init__(self, call: Call, on_unhealthy: Unhealthy | None = None) -> None:
        self._call = call
        self._on_unhealthy = on_unhealthy
        self.child: Supervised | None = None

    async def start(self, native: bool = True) -> None:
        self.child = Supervised("tracker", "worker_client.tracker", [json.dumps({"native": native})], self._call,
                                on_unhealthy=self._on_unhealthy)
        await self.child.start()

    async def stop(self) -> None:
        if self.child is not None:
            await self.child.stop()

    async def refresh(self) -> None:
        """Tell the tracker to ask the Engine what matters now. If it is between lives it asks by itself when it starts."""
        if self.child is None or not self.child.running:
            return
        try:
            await self.child.command("refresh")
        except (ConnectionError, RuntimeError, asyncio.TimeoutError) as exc:
            log.warning("tracker: could not refresh (%s)", exc)
