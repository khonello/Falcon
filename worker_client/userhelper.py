"""The Worker's side of the desktop helper (worker_client/helper.py).

`UserHelper` starts the helper where it can see the person's screen -- on their desktop through `winsession` when the Worker is a service, as a plain child
process otherwise (development, where the Worker is already on the desktop) -- and talks to it one JSON line at a time. `capture` and `HelperInput` plug into the
screen streamer and the remote input in place of the in-process versions, so the Engine and the console cannot tell the difference.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
from typing import Any

from worker_client import winsession

log = logging.getLogger(__name__)


class UserHelper:
    def __init__(self) -> None:
        self._proc: Any = None
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self) -> bool:
        if self.running:
            return True
        argv = [sys.executable, "-m", "worker_client.helper"]
        if winsession.in_service_session():
            self._proc = await asyncio.get_running_loop().run_in_executor(None, winsession.spawn_in_user_session, argv)
        else:
            self._proc = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                                                         limit=32 * 1024 * 1024)
        return self.running

    async def request(self, msg: dict[str, Any], timeout: float = 15.0) -> dict[str, Any]:
        async with self._lock:
            if not await self.start():
                return {"ok": False, "error": "no desktop to work on"}
            proc = self._proc
            proc.stdin.write((json.dumps(msg) + "\n").encode())
            await proc.stdin.drain()
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout)
            except asyncio.TimeoutError:
                await self.stop()
                return {"ok": False, "error": "the helper did not answer"}
            if not line:
                self._proc = None
                return {"ok": False, "error": "the helper ended"}
            return json.loads(line)

    async def capture(self, width: int) -> tuple[int, int, int, int, bytes]:
        """Same shape as `screenstream.capture_png`, taken on the person's desktop."""
        r = await self.request({"cmd": "capture", "width": width})
        if not r.get("ok"):
            raise OSError(r.get("error") or "no picture")
        return r["sw"], r["sh"], r["w"], r["h"], base64.b64decode(r["png_b64"])

    async def witness(self) -> tuple[float | None, str | None, str | None]:
        """Seconds since the person last touched the machine, the program in front and its window title, as the helper on their desktop sees them."""
        r = await self.request({"cmd": "witness"}, timeout=3.0)
        if not r.get("ok"):
            return None, None, None
        idle_s = r.get("idle_s")
        return (float(idle_s) if idle_s is not None else None), r.get("front"), r.get("title")

    async def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.stdin.write(b'{"cmd": "quit"}\n')
            await proc.stdin.drain()
            await asyncio.wait_for(proc.wait(), 3)
        except Exception:  # noqa: BLE001
            proc.terminate()


class HelperInput:
    """`RemoteInput`'s interface, carried out by the helper on the person's desktop."""

    def __init__(self, helper: UserHelper) -> None:
        self.helper = helper
        self.controlling = False
        self._tasks: set[asyncio.Task[Any]] = set()

    def _send(self, msg: dict[str, Any]) -> None:
        t = asyncio.ensure_future(self.helper.request(msg))
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)

    def control(self, on: bool) -> None:
        if bool(on) != self.controlling:
            self.controlling = bool(on)
            self._send({"cmd": "control", "on": self.controlling})

    def apply(self, events: list[dict[str, Any]]) -> int:
        if not self.controlling:
            return 0
        self._send({"cmd": "input", "events": events})
        return len(events)

    def stop(self) -> None:
        if self.controlling:
            self.controlling = False
            self._send({"cmd": "control", "on": False})
