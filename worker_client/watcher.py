"""File event reporting for the Global File Index (spec 6.2).

Two mechanisms, same wire shape (`index.event` / `index.sweep_batch`):
  * native: `watchdog` (ReadDirectoryChangesW / inotify) when installed -- no polling cost;
  * polling fallback: rescan the watched roots every `poll_seconds`, diff (size, mtime).

Plus the opportunistic full sweep: once the user has been idle long enough, walk every root
and report entries in batches, checking idleness between batches and stopping the instant
input resumes (spec 6.2 self-throttling). The walk runs in a thread so the event loop keeps
serving pushes; cancellation is cooperative.

Content hashes are sha256, computed off the loop, skipped above `hash_limit_bytes`.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from worker_client import idle

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]  # (message type, payload)

SWEEP_BATCH = 200
SWEEP_CHECK_EVERY = 50  # files between idle re-checks


def hash_file(path: Path, limit: int) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


class Watcher:
    def __init__(self, roots: list[str], report: Reporter, *, poll_seconds: float = 5.0,
                 hash_limit: int = 64 << 20, idle_after: float = 300.0, native: bool = True) -> None:
        self.roots = [Path(r) for r in roots if Path(r).is_dir()]
        self.report = report
        self.poll_seconds = poll_seconds
        self.hash_limit = hash_limit
        self.idle_after = idle_after
        self.native = native
        self._snapshot: dict[str, tuple[int, float]] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._observer: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._sweep_cancel = threading.Event()
        self.mode = "off"
        self.events_reported = 0
        self.sweeps_completed = 0

    # --- lifecycle ------------------------------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        if not self.roots:
            log.warning("watcher: no existing roots to watch")
            self.mode = "off"
            return
        if self.native and self._start_native():
            self.mode = "native"
        else:
            self.mode = "polling"
            self._snapshot = await asyncio.to_thread(self._scan)
            self._tasks.append(asyncio.create_task(self._poll_loop()))
        self._tasks.append(asyncio.create_task(self._idle_sweep_loop()))
        log.info("watcher: %s over %s", self.mode, ", ".join(str(r) for r in self.roots))

    async def stop(self) -> None:
        self._sweep_cancel.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

    # --- native (watchdog) ----------------------------------------------------------------------

    def _start_native(self) -> bool:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            log.info("watchdog not installed; falling back to polling")
            return False
        loop = self._loop
        watcher = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: Any) -> None:
                if getattr(event, "is_directory", False):
                    return
                kind = event.event_type  # created|modified|moved|deleted|closed
                op = {"created": "create", "modified": "modify", "moved": "move", "deleted": "delete",
                      "closed": "modify"}.get(kind)
                if op is None or loop is None:
                    return
                path = str(getattr(event, "dest_path", "") or event.src_path)
                old = str(event.src_path) if op == "move" else None
                asyncio.run_coroutine_threadsafe(watcher.report_event(op, path, old_path=old), loop)

        try:
            self._observer = Observer()
            for root in self.roots:
                self._observer.schedule(Handler(), str(root), recursive=True)
            self._observer.daemon = True
            self._observer.start()
            return True
        except Exception as exc:  # noqa: BLE001 -- any native failure means: poll instead
            log.warning("native watcher failed (%s); falling back to polling", exc)
            self._observer = None
            return False

    # --- polling fallback -----------------------------------------------------------------------

    def _scan(self) -> dict[str, tuple[int, float]]:
        seen: dict[str, tuple[int, float]] = {}
        for root in self.roots:
            for dirpath, _dirs, files in os.walk(root):
                for name in files:
                    p = os.path.join(dirpath, name)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    seen[p] = (st.st_size, st.st_mtime)
        return seen

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self.poll_seconds)
            current = await asyncio.to_thread(self._scan)
            for path, sig in current.items():
                before = self._snapshot.get(path)
                if before is None:
                    await self.report_event("create", path)
                elif before != sig:
                    await self.report_event("modify", path)
            for path in set(self._snapshot) - set(current):
                await self.report_event("delete", path)
            self._snapshot = current

    # --- reporting ------------------------------------------------------------------------------

    async def report_event(self, op: str, path: str, *, old_path: str | None = None) -> None:
        digest = None
        if op != "delete":
            digest = await asyncio.to_thread(hash_file, Path(path), self.hash_limit)
        event: dict[str, Any] = {"op": op, "path": path, "name": os.path.basename(path), "hash": digest}
        if old_path:
            event["old_path"] = old_path
        try:
            await self.report("index.event", {"event": event})
            self.events_reported += 1
        except Exception as exc:  # noqa: BLE001 -- never let a report failure kill the watcher
            log.warning("index.event failed for %s: %s", path, exc)

    # --- idle-time full sweep -------------------------------------------------------------------

    async def _idle_sweep_loop(self) -> None:
        while True:
            await asyncio.sleep(min(30.0, max(1.0, self.idle_after / 10)))
            if not idle.is_idle(self.idle_after):
                continue
            await self.sweep()
            # After a full sweep, wait for a fresh idle period before doing it again.
            await asyncio.sleep(max(self.idle_after, 60.0))

    async def sweep(self) -> int:
        """Walk every root, reporting in batches; stops the moment the user is active.
        Returns entries reported (partial sweeps are fine -- the next idle period continues)."""
        self._sweep_cancel.clear()
        total = 0
        queue: asyncio.Queue[list[dict[str, Any]] | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def walk() -> None:
            batch: list[dict[str, Any]] = []
            n = 0
            for root in self.roots:
                for dirpath, _dirs, files in os.walk(root):
                    for name in files:
                        if self._sweep_cancel.is_set():
                            loop.call_soon_threadsafe(queue.put_nowait, None)
                            return
                        n += 1
                        if n % SWEEP_CHECK_EVERY == 0 and not idle.is_idle(self.idle_after):
                            self._sweep_cancel.set()
                            loop.call_soon_threadsafe(queue.put_nowait, None)
                            return
                        p = os.path.join(dirpath, name)
                        batch.append({"op": "modify", "path": p, "name": name, "hash": hash_file(Path(p), self.hash_limit)})
                        if len(batch) >= SWEEP_BATCH:
                            loop.call_soon_threadsafe(queue.put_nowait, batch)
                            batch = []
            if batch:
                loop.call_soon_threadsafe(queue.put_nowait, batch)
            loop.call_soon_threadsafe(queue.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(walk))
        interrupted = False
        try:
            while True:
                batch = await queue.get()
                if batch is None:
                    break
                await self.report("index.sweep_batch", {"entries": batch})
                total += len(batch)
            interrupted = self._sweep_cancel.is_set()
        finally:
            self._sweep_cancel.set()
            await worker
        if total:
            log.info("idle sweep reported %d entries%s", total, " (interrupted)" if interrupted else "")
        if not interrupted:
            self.sweeps_completed += 1
        return total
