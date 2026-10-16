"""Update attempts on this PC (spec 9.4): retry when idle, never a stuck state.

`update.available {version}` marks a pending update. An attempt runs `config.update_command`
(the packaging/CI pipeline is a deferred infrastructure task -- spec 10.5 -- so the command is
whatever the deployment provides, with `{version}` substituted). No command configured means
the attempt fails honestly and is reported; the Engine escalates past its threshold.

Retries happen only when the machine is idle and connected -- the same "notice when idle,
act then" pattern the index sweep uses.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
import subprocess
from collections.abc import Awaitable, Callable
from typing import Any

from worker_client import idle
from worker_client.stopping import stop_tasks

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class Updater:
    def __init__(self, report: Reporter, *, running_version: str, update_command: str | None,
                 idle_after: float = 120.0, retry_seconds: float = 60.0) -> None:
        self.report = report
        self.running_version = running_version
        self.update_command = update_command
        self.idle_after = idle_after
        self.retry_seconds = retry_seconds
        self.pending: str | None = None
        self.attempts = 0
        self.last_error: str | None = None            # what the last failed attempt said, for the Engine to show
        self._task: asyncio.Task[None] | None = None

    def on_available(self, payload: dict[str, Any]) -> None:
        """An update is waiting. `now` (an Admin chose *Retry now*) tries at once instead of waiting for an idle moment."""
        version = str(payload.get("version", ""))
        if version and version != self.running_version:
            self.pending = version
            log.info("update %s available; will attempt %s", version, "now" if payload.get("now") else "when idle")
            if payload.get("now"):
                asyncio.create_task(self.attempt(force=True))
            elif self._task is None or self._task.done():
                self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            await stop_tasks([self._task])

    async def _loop(self) -> None:
        while self.pending:
            if idle.is_idle(self.idle_after):
                await self.attempt()
            await asyncio.sleep(self.retry_seconds)

    async def attempt(self, *, force: bool = False) -> bool:
        version = self.pending
        if not version:
            return False
        self.attempts += 1
        ok = await asyncio.to_thread(self._apply, version)
        payload = {"version": version, "succeeded": ok, "running": self.running_version}
        if not ok and self.last_error:
            payload["error"] = self.last_error
        try:
            await self.report("updates.report_status", payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("could not report update attempt: %s", exc)
        if ok:
            self.running_version = version
            self.pending = None
        return ok

    def _apply(self, version: str) -> bool:
        self.last_error = None
        if not self.update_command:
            log.warning("no update_command configured; update to %s cannot be applied on this PC", version)
            self.last_error = "No way to update has been set up on this machine"
            return False
        argv = [a.replace("{version}", version) for a in shlex.split(self.update_command)]
        try:
            result = subprocess.run(argv, check=False, timeout=600, capture_output=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("update command failed: %s", exc)
            self.last_error = "The update took too long" if isinstance(exc, subprocess.TimeoutExpired) else f"The update could not start ({exc.__class__.__name__})"
            return False
        if result.returncode != 0:
            log.warning("update command exited %s: %s", result.returncode, result.stderr[-500:])
            tail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            self.last_error = (tail[-1][:160] if tail else f"The update stopped with code {result.returncode}")
            return False
        return True
