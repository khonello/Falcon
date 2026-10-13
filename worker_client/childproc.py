"""Supervised child processes: the indexer and the event tracker each run as their own program under the service.

Why: the indexer walks disks and the tracker holds a kernel trace; either can fail or stall, and neither should be able to
take the Engine connection (and with it the whole machine's reporting) down with it. The service starts each one, restarts it
when it dies (waiting longer each time), and says so when it keeps dying.

Only the service holds the Engine connection and key. A child has none: it talks to the service over its own stdin/stdout,
one JSON object per line, and the service forwards what it asks.

    child  -> service   {"req": 7, "type": "index.event", "payload": {...}}     ask the service to send this to the Engine
                        {"reply": 3, "ok": true, "result": {...}}                answer to a command
                        {"status": {...}}                                        what the child wants shown (mode, counts)
    service -> child    {"reply": 7, "ok": true, "result": {...}}                the Engine's answer (or "ok": false, "error")
                        {"cmd": "sweep", "id": 3, "args": {}}                    a command

Both ends live here: `Link` in the child, `Supervised` in the service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)

Handler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
CommandFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

LINE_LIMIT = 32 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


# --- the child's end ---------------------------------------------------------------------------------------

class Link:
    """What a child program uses to reach the service: `report` (like the Engine call the code had before), commands in."""

    def __init__(self) -> None:
        self._out = sys.stdout
        sys.stdout = sys.stderr            # a stray print must never be taken for a message
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._next = 1
        self._commands: dict[str, CommandFn] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def command(self, name: str, fn: CommandFn) -> None:
        self._commands[name] = fn

    def _write(self, msg: dict[str, Any]) -> None:
        self._out.write(json.dumps(msg, separators=(",", ":")) + "\n")
        self._out.flush()

    def status(self, **fields: Any) -> None:
        self._write({"status": fields})

    async def report(self, type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        n = self._next
        self._next += 1
        fut: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[n] = fut
        self._write({"req": n, "type": type_, "payload": payload or {}})
        return await fut

    async def _run_command(self, msg: dict[str, Any]) -> None:
        fn = self._commands.get(str(msg.get("cmd")))
        try:
            if fn is None:
                raise ValueError(f"unknown command {msg.get('cmd')!r}")
            result = await fn(msg.get("args") or {})
            self._write({"reply": msg.get("id"), "ok": True, "result": result})
        except Exception as exc:  # noqa: BLE001 -- told to the service, which decides what it means
            self._write({"reply": msg.get("id"), "ok": False, "error": str(exc)})

    async def serve(self) -> None:
        """Read the service's lines until its end closes (the service stopped or restarted): then return."""
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                break
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if "reply" in msg:
                fut = self._pending.pop(int(msg["reply"]), None)
                if fut is not None and not fut.done():
                    if msg.get("ok"):
                        fut.set_result(msg.get("result") or {})
                    else:
                        fut.set_exception(RuntimeError(str(msg.get("error") or "refused")))
            elif msg.get("cmd") == "quit":
                break
            elif "cmd" in msg:
                task = asyncio.create_task(self._run_command(msg))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(ConnectionError("the service went away"))


# --- the service's end -------------------------------------------------------------------------------------

class Supervised:
    """One child program, kept running. `handle(type, payload)` answers what the child asks of the Engine."""

    def __init__(self, name: str, module: str, args: list[str], handle: Handler, *,
                 backoff: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 30.0), stable_after: float = 60.0,
                 unhealthy_after: int = 5, unhealthy_window: float = 300.0,
                 on_unhealthy: Callable[[str, bool], None] | None = None) -> None:
        self.name = name
        self.argv = [sys.executable, "-m", module, *args]
        self.handle = handle
        self.backoff = backoff
        self.stable_after = stable_after
        self.unhealthy_after = unhealthy_after
        self.unhealthy_window = unhealthy_window
        self.on_unhealthy = on_unhealthy
        self.proc: asyncio.subprocess.Process | None = None
        self.restarts = 0
        self.healthy = True
        self.last_exit: int | None = None
        self.state: dict[str, Any] = {}            # the latest {"status": ...} the child sent
        self._deaths: list[float] = []
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._next = 1
        self._jobs: set[asyncio.Task[None]] = set()

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    @property
    def pid(self) -> int | None:
        return self.proc.pid if self.running and self.proc is not None else None

    def info(self) -> dict[str, Any]:
        return {"name": self.name, "running": self.running, "pid": self.pid, "restarts": self.restarts,
                "healthy": self.healthy, "last_exit": self.last_exit}

    async def start(self) -> None:
        self._stopping = False
        self._task = asyncio.create_task(self._supervise())

    async def stop(self) -> None:
        self._stopping = True
        proc = self.proc
        if proc is not None and proc.returncode is None:
            try:
                await self._send({"cmd": "quit"})
                if proc.stdin is not None:
                    proc.stdin.close()
                await asyncio.wait_for(proc.wait(), 3)
            except (asyncio.TimeoutError, OSError, ConnectionError):
                proc.kill()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        for job in list(self._jobs):
            job.cancel()

    async def command(self, name: str, timeout: float = 15.0, **args: Any) -> dict[str, Any]:
        """Ask the child to do something and wait for its answer; raises if it is not running or does not answer."""
        if not self.running:
            raise ConnectionError(f"{self.name} is not running")
        n = self._next
        self._next += 1
        fut: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[n] = fut
        try:
            await self._send({"cmd": name, "id": n, "args": args})
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(n, None)

    async def _send(self, msg: dict[str, Any]) -> None:
        proc = self.proc
        if proc is None or proc.stdin is None or proc.returncode is not None:
            raise ConnectionError(f"{self.name} is not running")
        proc.stdin.write((json.dumps(msg, separators=(",", ":")) + "\n").encode())
        await proc.stdin.drain()

    async def _supervise(self) -> None:
        attempt = 0
        while not self._stopping:
            started = time.monotonic()
            try:
                kwargs: dict[str, Any] = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = CREATE_NO_WINDOW
                self.proc = await asyncio.create_subprocess_exec(
                    *self.argv, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE, limit=LINE_LIMIT, **kwargs)
                log.info("%s: started (pid %s)", self.name, self.proc.pid)
                await asyncio.gather(self._read_out(self.proc), self._read_err(self.proc), self.proc.wait())
                self.last_exit = self.proc.returncode
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("%s: could not start", self.name)
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(ConnectionError(f"{self.name} stopped"))
            if self._stopping:
                return
            now = time.monotonic()
            self.restarts += 1
            self._deaths = [t for t in self._deaths if now - t < self.unhealthy_window] + [now]
            if now - started >= self.stable_after:
                attempt = 0
            self._set_healthy(len(self._deaths) < self.unhealthy_after)
            wait = self.backoff[min(attempt, len(self.backoff) - 1)]
            attempt += 1
            log.warning("%s: stopped (exit %s), starting again in %.0fs%s", self.name, self.last_exit, wait,
                        "" if self.healthy else "  -- it keeps dying")
            await asyncio.sleep(wait)

    def _set_healthy(self, ok: bool) -> None:
        if ok == self.healthy:
            return
        self.healthy = ok
        (log.info if ok else log.error)("%s: %s", self.name, "healthy again" if ok else "UNHEALTHY: it keeps dying")
        if self.on_unhealthy is not None:
            self.on_unhealthy(self.name, ok)

    async def _read_err(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stderr is not None
        async for raw in proc.stderr:
            log.info("%s: %s", self.name, raw.decode("utf-8", "replace").rstrip())

    async def _read_out(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stdout is not None
        while True:
            try:
                raw = await proc.stdout.readline()
            except (ValueError, ConnectionError):
                break
            if not raw:
                break
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if "req" in msg:
                job = asyncio.create_task(self._answer(proc, msg))     # never inline: the Engine may take a while
                self._jobs.add(job)
                job.add_done_callback(self._jobs.discard)
            elif "reply" in msg:
                fut = self._pending.get(int(msg["reply"]))
                if fut is not None and not fut.done():
                    if msg.get("ok"):
                        fut.set_result(msg.get("result") or {})
                    else:
                        fut.set_exception(RuntimeError(str(msg.get("error") or "refused")))
            elif "status" in msg:
                self.state = dict(msg["status"] or {})
        self.state = {}

    async def _answer(self, proc: asyncio.subprocess.Process, msg: dict[str, Any]) -> None:
        try:
            result = await self.handle(str(msg.get("type")), msg.get("payload") or {})
            reply: dict[str, Any] = {"reply": msg["req"], "ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001 -- the child sees the refusal exactly as it saw one before
            reply = {"reply": msg["req"], "ok": False, "error": str(exc)}
        if proc is self.proc and proc.returncode is None:
            try:
                await self._send(reply)
            except (ConnectionError, OSError):
                pass
