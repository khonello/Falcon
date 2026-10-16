"""File event reporting for the Global File Index (spec 6.2).

Two mechanisms, same wire shape (`index.event` / `index.sweep_batch`):
  * native: `watchdog` (ReadDirectoryChangesW / inotify) when installed -- no polling cost;
  * polling fallback: rescan the watched roots every `poll_seconds`, diff (size, mtime, attributes, file identity).

What is reported: a file created, edited, moved or renamed (with where it was), copied, deleted; a change of its
attributes (read-only, hidden) or of who may open it (permissions/owner), told apart from a content edit by comparing
two looks (fsmeta.py); and the same for FOLDERS (created, moved/renamed, deleted -- `is_dir`). The polling fallback
cannot see permissions or folders.

Plus the opportunistic full sweep: once the user has been idle long enough, walk every root
and report entries in batches, checking idleness between batches and stopping the instant
input resumes (spec 6.2 self-throttling). The walk runs in a thread so the event loop keeps
serving pushes; cancellation is cooperative.

Content hashes are sha256, computed off the loop, skipped above `hash_limit_bytes`.

Reconciliation (proactive, the core of this module): events only tell what happens while the watcher runs. `reconcile()` compares the watched
folders with what the Engine was last told (`worker_client.snapshot`, kept on disk) and reports exactly the difference -- files that appeared,
changed or went while the machine was off, the service restarting, or the Engine unreachable -- through `index.catchup`, which the Engine treats as
if each had happened live. It runs when the Worker connects, again now and then, and the very first time as a full baseline.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from worker_client import fsmeta, idle
from worker_client.snapshot import Snapshot
from worker_client.stopping import stop_tasks

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]  # (message type, payload)

SWEEP_BATCH = 200
CATCHUP_BATCH = 100
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
                 hash_limit: int = 64 << 20, idle_after: float = 300.0, native: bool = True,
                 state_path: Path | None = None, reconcile_seconds: float = 1800.0) -> None:
        self.state = Snapshot(state_path) if state_path is not None else None
        self.reconcile_seconds = reconcile_seconds
        self._reconciling = False
        self.reconciled = {"at": 0.0, "found": 0}
        self.roots = [Path(r) for r in roots if Path(r).is_dir()]
        self.report = report
        self.poll_seconds = poll_seconds
        self.hash_limit = hash_limit
        self.idle_after = idle_after
        self.native = native
        self._snapshot: dict[str, tuple[int, float, int, int]] = {}      # path -> (size, mtime, identity, attributes)
        self._meta: dict[str, fsmeta.Meta] = {}      # what each file looked like last time, to tell kinds of change apart
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
        if self.state is not None and self.reconcile_seconds > 0:
            self._tasks.append(asyncio.create_task(self._reconcile_loop()))
        log.info("watcher: %s over %s", self.mode, ", ".join(str(r) for r in self.roots))

    async def stop(self) -> None:
        self._sweep_cancel.set()
        await stop_tasks(self._tasks)
        self._tasks.clear()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None
        if self.state is not None:
            self.state.close()

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
                kind = event.event_type  # created|modified|moved|deleted|closed
                if kind not in ("created", "modified", "moved", "deleted", "closed") or loop is None:
                    return
                asyncio.run_coroutine_threadsafe(
                    watcher.on_fs_event(kind, str(event.src_path), str(getattr(event, "dest_path", "") or ""),
                                        bool(getattr(event, "is_directory", False))), loop)

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

    async def on_fs_event(self, kind: str, src: str, dest: str, is_dir: bool) -> None:
        """One OS event, turned into what the Engine is told. A folder: created, moved/renamed, deleted (its edits are
        noise). A file: created, moved/renamed (with where it was), deleted -- and a "modified" is looked at to see
        whether the content changed, the attributes did, or who may open it did."""
        if is_dir:
            op = {"created": "create", "moved": "move", "deleted": "delete"}.get(kind)
            if op:
                await self.report_event(op, dest or src, old_path=src if op == "move" else None, is_dir=True)
            return
        if kind == "created":
            await self._remember(src)
            await self.report_event("create", src)
        elif kind == "moved":
            self._meta.pop(src, None)
            await self._remember(dest)
            await self.report_event("move", dest, old_path=src)
        elif kind == "deleted":
            self._meta.pop(src, None)
            await self.report_event("delete", src)
        else:                                            # modified (or closed after a write)
            now = await asyncio.to_thread(fsmeta.meta, src)
            before = self._meta.get(src)
            if now is None:
                return                                   # it is already gone; the delete will follow
            self._meta[src] = now
            for op in (["modify"] if before is None else fsmeta.changes(before, now)):
                await self.report_event(op, src, detail=fsmeta.attr_detail(before.attrs, now.attrs) if op == "attrib" and before is not None else None)

    async def _remember(self, path: str) -> None:
        now = await asyncio.to_thread(fsmeta.meta, path)
        if now is not None:
            self._meta[path] = now
            if len(self._meta) > 50000:                  # bounded: forget the oldest looks
                for old in list(self._meta)[:5000]:
                    self._meta.pop(old, None)

    # --- polling fallback -----------------------------------------------------------------------

    def _scan(self) -> dict[str, tuple[int, float, int, int]]:
        seen: dict[str, tuple[int, float, int, int]] = {}
        for root in self.roots:
            for dirpath, _dirs, files in os.walk(root):
                for name in files:
                    p = os.path.join(dirpath, name)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    attrs = int(getattr(st, "st_file_attributes", st.st_mode))
                    seen[p] = (st.st_size, st.st_mtime, st.st_ino, attrs)
        return seen

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self.poll_seconds)
            current = await asyncio.to_thread(self._scan)
            created = [p for p in current if p not in self._snapshot]
            gone = {p: self._snapshot[p] for p in self._snapshot if p not in current}
            for path in created:
                # the same file identity that just vanished elsewhere: it was moved or renamed, not deleted and created
                old = next((g for g, sig in gone.items() if sig[2] and sig[2] == current[path][2]), None)
                if old is not None:
                    gone.pop(old)
                    await self.report_event("move", path, old_path=old)
                else:
                    await self.report_event("create", path)
            for path, sig in current.items():
                before = self._snapshot.get(path)
                if before is None:
                    continue
                if before[:2] != sig[:2]:
                    await self.report_event("modify", path)
                if before[3] != sig[3]:
                    await self.report_event("attrib", path, detail=fsmeta.attr_detail(before[3], sig[3]))
            for path in gone:
                await self.report_event("delete", path)
            self._snapshot = current

    # --- reporting ------------------------------------------------------------------------------

    async def report_event(self, op: str, path: str, *, old_path: str | None = None, is_dir: bool = False, detail: dict[str, bool] | None = None) -> None:
        digest = None
        if op not in ("delete", "attrib", "security") and not is_dir:        # the content did not change in the last two
            digest = await asyncio.to_thread(hash_file, Path(path), self.hash_limit)
        event: dict[str, Any] = {"op": op, "path": path, "name": os.path.basename(path), "hash": digest}
        if old_path:
            event["old_path"] = old_path
        if is_dir:
            event["is_dir"] = True
        if detail:
            event["detail"] = detail                         # for an attribute change: hidden, system, read-only, before and after
        try:
            await self.report("index.event", {"event": event})
            self.events_reported += 1
        except Exception as exc:  # noqa: BLE001 -- never let a report failure kill the watcher
            log.warning("index.event failed for %s: %s (the next reconcile will find it again)", path, exc)
            return
        if self.state is not None:
            await asyncio.to_thread(self._remember_told, op, path, old_path, is_dir, digest)

    def _remember_told(self, op: str, path: str, old_path: str | None, is_dir: bool, digest: str | None) -> None:
        """The Engine took this report: the snapshot now says what it says."""
        assert self.state is not None
        if is_dir:
            if op == "delete":
                self.state.remove_under(path)
            elif op == "move" and old_path:
                self.state.move_under(old_path, path)
            return
        if op == "delete":
            self.state.remove([path])
            return
        if op == "move" and old_path:
            self.state.remove([old_path])
        if op in ("attrib", "security"):
            return
        try:
            st = os.stat(path)
        except OSError:
            return
        self.state.upsert([(path, st.st_size, st.st_mtime_ns, digest)])

    # --- idle-time full sweep -------------------------------------------------------------------

    async def _idle_sweep_loop(self) -> None:
        while True:
            await asyncio.sleep(min(30.0, max(1.0, self.idle_after / 10)))
            if not idle.is_idle(self.idle_after):
                continue
            await self.sweep()
            # After a full sweep, wait for a fresh idle period before doing it again.
            await asyncio.sleep(max(self.idle_after, 60.0))

    async def sweep(self, *, force: bool = False) -> int:
        """Walk every root, reporting in batches; stops the moment the user is active (unless `force`: the first full look).
        Returns entries reported (partial sweeps are fine -- the next idle period continues)."""
        self._sweep_cancel.clear()
        run = self.state.next_run() if self.state is not None else 0
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
                        if n % SWEEP_CHECK_EVERY == 0 and not force and not idle.is_idle(self.idle_after):
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
        first = True
        try:
            while True:
                batch = await queue.get()
                if batch is None:
                    break
                await self.report("index.sweep_batch", {"entries": batch, "first": first})
                first = False
                total += len(batch)
                if self.state is not None:
                    await asyncio.to_thread(self._remember_swept, batch, run)
            interrupted = self._sweep_cancel.is_set()
        finally:
            self._sweep_cancel.set()
            await worker
        if total:
            log.info("idle sweep reported %d entries%s", total, " (interrupted)" if interrupted else "")
        if not interrupted:
            self.sweeps_completed += 1
            if self.state is not None:                                       # and the snapshot forgets what the sweep did not meet
                gone = [p for r in self.roots for p in self.state.unseen_under(str(r), run)]
                self.state.remove(gone)
            try:
                await self.report("index.sweep_done", {"roots": [str(r) for r in self.roots]})      # what it did not see is gone
            except Exception as exc:  # noqa: BLE001 -- a missed word costs only a stale row until the next sweep
                log.warning("could not say the sweep finished: %s", exc)
        return total


    def _remember_swept(self, batch: list[dict[str, Any]], run: int) -> None:
        assert self.state is not None
        rows = []
        for e in batch:
            try:
                st = os.stat(e["path"])
            except OSError:
                continue
            rows.append((e["path"], st.st_size, st.st_mtime_ns, e.get("hash")))
        self.state.upsert(rows, run)

    # --- reconciliation: tell the Engine what changed while it was not listening ----------------------------------

    async def _reconcile_loop(self) -> None:
        while True:
            await asyncio.sleep(self.reconcile_seconds)
            try:
                await self.reconcile()
            except Exception as exc:  # noqa: BLE001 -- a look that failed is simply made again next time
                log.warning("reconcile failed: %s", exc)

    async def reconcile(self) -> dict[str, Any]:
        """Bring the Engine up to date with this machine's folders. The first time (nothing recorded) that is a full baseline; after that only
        the difference is sent: created, changed and deleted files, as `index.catchup` events the Engine treats as live ones."""
        if self.state is None or not self.roots:
            return {"skipped": True}
        if self._reconciling:
            return {"busy": True}
        self._reconciling = True
        try:
            if not await asyncio.to_thread(self.state.baselined):
                before = self.sweeps_completed
                sent = await self.sweep(force=True)
                if self.sweeps_completed > before:                 # it ran to the end: that is the first full look
                    await asyncio.to_thread(self.state.set_baselined)
                self.sweeps_completed = before                     # ... which is not one of the idle sweeps that are counted
                self.reconciled = {"at": time.time(), "found": sent}
                return {"baseline": sent}
            found = await self._reconcile_changes()
            self.reconciled = {"at": time.time(), "found": found}
            if found:
                log.info("reconcile: told the Engine about %d change(s) it had not heard", found)
            return {"changes": found}
        finally:
            self._reconciling = False

    async def _reconcile_changes(self) -> int:
        assert self.state is not None
        state = self.state
        run = await asyncio.to_thread(state.next_run)
        queue: asyncio.Queue[list[dict[str, Any]] | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        cancel = threading.Event()
        self._sweep_cancel.clear()

        def walk() -> None:
            batch: list[dict[str, Any]] = []
            for root in self.roots:
                for dirpath, _dirs, files in os.walk(root):
                    unchanged: list[str] = []
                    for name in files:
                        if self._sweep_cancel.is_set() or cancel.is_set():
                            loop.call_soon_threadsafe(queue.put_nowait, None)
                            return
                        p = os.path.join(dirpath, name)
                        try:
                            st = os.stat(p)
                        except OSError:
                            continue
                        known = state.known(p)
                        if known is not None:
                            unchanged.append(p)          # met in this walk, changed or not: it is not one of the files that went
                        if known is not None and known[0] == st.st_size and known[1] == st.st_mtime_ns:
                            continue
                        batch.append({"op": "modify" if known else "create", "path": p, "name": name,
                                      "hash": hash_file(Path(p), self.hash_limit), "_size": st.st_size, "_mtime": st.st_mtime_ns})
                        if len(batch) >= CATCHUP_BATCH:
                            loop.call_soon_threadsafe(queue.put_nowait, batch)
                            batch = []
                    state.mark_seen(unchanged, run)
            if batch:
                loop.call_soon_threadsafe(queue.put_nowait, batch)
            gone = [p for r in self.roots for p in state.unseen_under(str(r), run)]
            for i in range(0, len(gone), CATCHUP_BATCH):
                loop.call_soon_threadsafe(queue.put_nowait, [{"op": "delete", "path": p, "name": os.path.basename(p)} for p in gone[i:i + CATCHUP_BATCH]])
            loop.call_soon_threadsafe(queue.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(walk))
        total = 0
        try:
            while True:
                batch = await queue.get()
                if batch is None:
                    break
                events = [{k: v for k, v in e.items() if not k.startswith("_")} for e in batch]
                await self.report("index.catchup", {"events": events})                  # raises if the Engine did not take it: nothing is recorded
                total += len(batch)
                await asyncio.to_thread(self._remember_caught_up, batch, run)
        finally:
            cancel.set()
            await worker
        return total

    def _remember_caught_up(self, batch: list[dict[str, Any]], run: int) -> None:
        assert self.state is not None
        self.state.upsert([(e["path"], e["_size"], e["_mtime"], e.get("hash")) for e in batch if e["op"] != "delete"], run)
        self.state.remove([e["path"] for e in batch if e["op"] == "delete"])
