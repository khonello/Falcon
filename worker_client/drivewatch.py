"""What is written to an external drive while it is attached.

The file watcher follows the folders it was given, and a stick or a USB hard disk is not one of them, so a file copied out went unseen. This follows each external drive for
new files only. What was already on a drive is never read or listed: an 880 GB disk costs nothing to attach, and the person's own files there stay their own.

It finds the drives itself (`ossignals.drives`), so it also covers one that was plugged in before the Worker started and never gave a signal. Each file is told once it has
stopped changing, as a file event carrying `drive`, through the same path as every other: the Engine indexes it, and Detective and Restricted hear of it as usual.

Who was at the keyboard is asked the moment a file first appears on the drive, not when it is told: a file is told only after it has been quiet for SETTLED seconds,
and by then the person who pasted it has usually taken their hands off, so a copy by hand read as "a program the person started" (hands-on test, 10 Nov 2026).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from worker_client import ossignals
from worker_client.watcher import hash_file

log = logging.getLogger(__name__)

Reporter = Callable[..., Awaitable[Any]]
Stamp = Callable[[str], Awaitable[dict[str, Any]]]
LOOK_EVERY = 5.0                # how often the drives are looked at
SETTLED = 2.0                   # a file quiet for this long has finished being written
MAX_WAITING = 20000             # a copy of more than this at once: the rest are not told, and the log says so
FRESH = 60.0                    # a change to a file is only news if the file itself says it just changed: Windows also reports reads
NOT_THE_PERSONS = ("system volume information", "$recycle.bin", ".trashes", ".spotlight-v100", ".fseventsd")


def _drive_of(path: str, drives: Any) -> str:
    low = path.lower()
    return next((d for d in drives if low.startswith(d.lower())), "")


class DriveWatch:
    def __init__(self, report: Reporter, *, hash_limit: int, find: Callable[[], Any] | None = None, look_every: float = LOOK_EVERY, settled: float = SETTLED,
                 stamp: Stamp | None = None) -> None:
        self.report = report
        self.stamp = stamp
        self.seen: dict[str, tuple[float, dict[str, Any]]] = {}   # when a file first appeared, and who was at the keyboard then
        self._stamping: set[asyncio.Task[None]] = set()
        self.hash_limit = hash_limit
        self.find = find or (lambda: list(ossignals.drives()))
        self.look_every = look_every
        self.settled = settled
        self.observers: dict[str, Any] = {}
        self.waiting: dict[str, float] = {}
        self.told: dict[str, tuple[int, int]] = {}
        self.removed: list[str] = []                 # files gone from a drive, to be told: otherwise the index keeps them, and a mark finds a copy that is not there
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._said_full = False

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        for drive in list(self.observers):
            self._stop_watching(drive)

    async def _run(self) -> None:
        looked = 0.0
        while True:
            if time.monotonic() - looked >= self.look_every:
                looked = time.monotonic()
                try:
                    await self._follow(set(await asyncio.to_thread(self.find)))
                except Exception as exc:  # noqa: BLE001 -- a drive pulled out mid-look must not end this
                    log.warning("could not look at the drives: %s", exc)
            await self._tell_what_settled()
            await asyncio.sleep(min(0.5, self.settled))

    async def _follow(self, now: set[str]) -> None:
        for drive in set(self.observers) - now:
            self._stop_watching(drive)
        for drive in now - set(self.observers):
            self._start_watching(drive)

    def _start_watching(self, drive: str) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            log.warning("watchdog is not installed: what is written to %s will not be seen", drive)
            return
        watch = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: Any) -> None:
                if getattr(event, "is_directory", False) or watch._loop is None:
                    return
                kind = event.event_type
                if kind in ("deleted", "moved"):
                    watch._loop.call_soon_threadsafe(watch.gone, str(event.src_path))
                path = str(getattr(event, "dest_path", "") or "") if kind == "moved" else str(event.src_path)
                if kind in ("created", "modified", "moved") and path:
                    watch._loop.call_soon_threadsafe(watch.touched, kind, path)

        try:
            observer = Observer()
            observer.schedule(Handler(), drive, recursive=True)
            observer.daemon = True
            observer.start()
        except Exception as exc:  # noqa: BLE001 -- a drive that cannot be watched is said, and looked at again
            log.warning("could not follow %s: %s", drive, exc)
            return
        self.observers[drive] = observer
        log.info("following what is written to %s", drive)

    def _stop_watching(self, drive: str) -> None:
        observer = self.observers.pop(drive, None)
        if observer is not None:
            try:
                observer.stop()
            except Exception:
                log.debug("stopping the watch on %s", drive, exc_info=True)
        log.info("no longer following %s", drive)
        for path in [p for p in self.waiting if p.lower().startswith(drive.lower())]:
            del self.waiting[path]
        for path in [p for p in self.told if p.lower().startswith(drive.lower())]:
            del self.told[path]
        for path in [p for p in self.seen if p.lower().startswith(drive.lower())]:
            del self.seen[path]

    def gone(self, path: str) -> None:
        """A file left a drive. One made and gone before it was ever told (a temporary file) is nobody's news; any other is, even one told before a restart."""
        self.told.pop(path, None)
        self.seen.pop(path, None)
        if self.waiting.pop(path, None) is None and len(self.removed) < MAX_WAITING:
            self.removed.append(path)

    def touched(self, kind: str, path: str) -> None:
        if any(part.lower() in NOT_THE_PERSONS for part in Path(path).parts):
            return
        if kind == "modified" and path not in self.waiting:
            try:
                if time.time() - os.stat(path).st_mtime > FRESH:
                    return
            except OSError:
                return
        if len(self.waiting) >= MAX_WAITING and path not in self.waiting:
            if not self._said_full:
                self._said_full = True
                log.warning("over %d files are being written to a drive at once: the rest are not told", MAX_WAITING)
            return
        if path not in self.waiting and self.stamp is not None:
            task = asyncio.ensure_future(self._take_stamp(path, time.time()))
            self._stamping.add(task)
            task.add_done_callback(self._stamping.discard)
        self.waiting[path] = time.monotonic()

    async def _take_stamp(self, path: str, at: float) -> None:
        try:
            got = await self.stamp(path)                # type: ignore[misc]
        except Exception as exc:  # noqa: BLE001 -- no stamp is "asked when told", never a lost file
            log.debug("could not take a witness stamp for %s: %s", path, exc)
            return
        self.seen.setdefault(path, (at, got))

    async def _tell_what_settled(self) -> None:
        while self.removed:
            path = self.removed.pop(0)
            if os.path.exists(path):
                continue                                # put back before it was told: nothing went
            event = {"op": "delete", "path": path, "name": os.path.basename(path), "drive": _drive_of(path, self.observers)}
            try:
                await self.report("index.event", {"event": event})
            except Exception as exc:  # noqa: BLE001 -- never let a report failure end the watch
                log.warning("could not tell that %s went: %s", path, exc)
        now = time.monotonic()
        for path in [p for p, at in self.waiting.items() if now - at >= self.settled]:
            del self.waiting[path]
            await self._tell(path)
        if not self.waiting:
            self._said_full = False

    async def _tell(self, path: str) -> None:
        try:
            st = os.stat(path)
        except OSError:
            return                                     # gone again: a temporary file
        if self.told.get(path) == (st.st_size, st.st_mtime_ns):
            return
        digest = await asyncio.to_thread(hash_file, Path(path), self.hash_limit)
        event: dict[str, Any] = {"op": "create", "path": path, "name": os.path.basename(path), "hash": digest, "drive": _drive_of(path, self.observers)}
        if (first := self.seen.pop(path, None)) is not None:
            event["at"], event["witness"] = first        # when it was put there, and by whom: not two seconds later, when the hands are off
        try:
            await self.report("index.event", {"event": event})
            self.told[path] = (st.st_size, st.st_mtime_ns)
        except Exception as exc:  # noqa: BLE001 -- never let a report failure end the watch
            log.warning("could not tell of %s: %s", path, exc)
