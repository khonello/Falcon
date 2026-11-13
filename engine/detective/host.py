"""The Engine's end of Detective's own process (engine/detective/brain.py).

`ProcessMatcher` starts the process on first use and talks to it over its stdin and stdout, through two small threads (one writes, one reads), so the Engine's
loop only ever puts a request in a queue and awaits a future: it never blocks on the pipe, and it works the same under any event loop, on Linux and on
Windows. Requests are answered in the order they were sent, so what one machine does is read in the order it happened.

If the process dies (or is killed), every request waiting is told so (`MatcherGone`) and the next one starts a new process with a new `generation`: the
Engine sees the number change and puts the last days back into it from the database (`engine.detective._ensure`), as after a restart. Detective is
advisory, so an event read while the matcher was down is lost to it and to nothing else.

`LocalMatcher` is the same matcher inside the Engine, for `FALCON_DETECTIVE_PROCESS=0`.
"""

from __future__ import annotations

import asyncio
import logging
import pickle
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from engine.detective.brain import Brain, read_frame, write_frame

log = logging.getLogger(__name__)

BRAIN = Path(__file__).with_name("brain.py")


class MatcherGone(RuntimeError):
    """Detective's process ended while a request was waiting for it."""


class LocalMatcher:
    def __init__(self) -> None:
        self.brain = Brain()
        self.generation = 1

    async def ready(self) -> int:
        return self.generation

    async def call(self, op: str, *args: Any) -> Any:
        return self.brain.handle(op, args)

    def post(self, op: str, *args: Any) -> None:
        self.brain.handle(op, args)

    async def stop(self) -> None:
        return None

    def kill(self) -> None:
        return None


class ProcessMatcher:
    def __init__(self) -> None:
        self.generation = 0
        self.proc: subprocess.Popen[bytes] | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.pending: dict[int, asyncio.Future[Any]] = {}
        self.outbox: queue.Queue[bytes | None] = queue.Queue()
        self.next_id = 0
        self.lock = threading.Lock()

    # --- the process ---------------------------------------------------------------------------------------------

    def _start(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.outbox = queue.Queue()
        proc = subprocess.Popen([sys.executable, str(BRAIN)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None, bufsize=0)
        self.proc = proc
        self.generation += 1
        threading.Thread(target=self._write, args=(proc, self.outbox), name="detective-write", daemon=True).start()
        threading.Thread(target=self._read, args=(proc, self.loop, self.generation), name="detective-read", daemon=True).start()
        log.info("detective: matcher process %d started (generation %d)", proc.pid, self.generation)

    def _alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    async def ready(self) -> int:
        """Start the process if it is not running; the generation tells the Engine whether what it put in before is still there."""
        if not self._alive():
            if self.proc is not None:
                self._gone(self.generation)
            self._start()
        return self.generation

    @staticmethod
    def _write(proc: subprocess.Popen[bytes], outbox: queue.Queue[bytes | None]) -> None:
        assert proc.stdin is not None
        while (data := outbox.get()) is not None:
            try:
                write_frame(proc.stdin, data)
            except (OSError, ValueError):
                return                                       # the process is gone: the reader says so
        try:
            proc.stdin.close()
        except OSError:
            pass

    def _read(self, proc: subprocess.Popen[bytes], loop: asyncio.AbstractEventLoop, generation: int) -> None:
        assert proc.stdout is not None
        while True:
            try:
                frame = read_frame(proc.stdout)
            except (OSError, ValueError):
                frame = None
            if frame is None:
                break
            rid, ok, value = pickle.loads(frame)             # trusted: written by the process this Engine started
            try:
                loop.call_soon_threadsafe(self._answer, rid, ok, value)
            except RuntimeError:
                return                                       # the loop is closed: the Engine has gone
        try:
            loop.call_soon_threadsafe(self._gone, generation)
        except RuntimeError:
            pass

    def _answer(self, rid: int, ok: bool, value: Any) -> None:
        fut = self.pending.pop(rid, None)
        if fut is None or fut.done():
            return
        if ok:
            fut.set_result(value)
        else:
            fut.set_exception(RuntimeError(f"detective matcher: {value}"))

    def _gone(self, generation: int) -> None:
        if generation != self.generation:
            return
        waiting, self.pending = self.pending, {}
        for fut in waiting.values():
            if not fut.done():
                fut.set_exception(MatcherGone("Detective's process ended"))
        if self.proc is not None and self.proc.poll() is not None:
            log.warning("detective: the matcher process ended (code %s); the next event starts a new one and puts the last days back", self.proc.returncode)
        self.proc = None

    # --- requests --------------------------------------------------------------------------------------------------

    def _send(self, op: str, args: tuple[Any, ...]) -> asyncio.Future[Any]:
        assert self.loop is not None
        self.next_id += 1
        fut: asyncio.Future[Any] = self.loop.create_future()
        self.pending[self.next_id] = fut
        self.outbox.put(pickle.dumps((self.next_id, op, args), protocol=pickle.HIGHEST_PROTOCOL))
        return fut

    async def call(self, op: str, *args: Any) -> Any:
        await self.ready()
        return await self._send(op, args)

    def post(self, op: str, *args: Any) -> None:
        """A request whose answer nobody waits for (it is still read in its turn, before anything sent after it)."""
        if not self._alive():
            return                                           # a new process learns it from the database instead
        fut = self._send(op, args)
        fut.add_done_callback(lambda f: f.cancelled() or f.exception() is None or log.warning("detective: %s failed: %s", op, f.exception()))

    async def stop(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        self.outbox.put(None)                                # closes its stdin: it finishes what it has and ends
        try:
            await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=3)
        except (TimeoutError, asyncio.TimeoutError):
            proc.kill()

    def kill(self) -> None:
        proc, self.proc = self.proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
