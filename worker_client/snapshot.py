"""What this machine last told the Engine about its files, kept on disk so it survives a restart.

The watcher reacts to what happens while it is running. A machine is not always running it: it is off at night, the service restarts, the Engine
goes down for a minute, the network drops. Whatever changed in those gaps raised no event the Engine heard. So the Worker also keeps this snapshot
(path, size, modified time, hash: the state the Engine ACKNOWLEDGED) and, on start, on reconnect and now and then, walks the watched folders and tells
the Engine exactly what differs: files that appeared, changed or went (`Watcher.reconcile`). Nothing is lost to a gap, and nothing is sent twice.

A file is recorded here only after the Engine took the report, so a report that failed is simply found again at the next look.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path


def key(path: str) -> str:
    """One spelling per file: slashes forward, case folded (Windows paths are case-insensitive)."""
    return path.replace("\\", "/").casefold()


class Snapshot:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS files (k TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER, mtime_ns INTEGER, hash TEXT, seen INTEGER NOT NULL DEFAULT 0)")
        self._db.execute("CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value INTEGER NOT NULL)")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT count(*) FROM files").fetchone()[0])

    def known(self, path: str) -> tuple[int, int, str | None] | None:
        with self._lock:
            row = self._db.execute("SELECT size, mtime_ns, hash FROM files WHERE k = ?", (key(path),)).fetchone()
        return (row[0], row[1], row[2]) if row else None

    def upsert(self, rows: Iterable[tuple[str, int, int, str | None]], run: int | None = None) -> None:
        """(path, size, mtime_ns, hash) for each file the Engine now knows."""
        batch = [(key(p), p, size, mtime, digest, run or 0) for p, size, mtime, digest in rows]
        if not batch:
            return
        with self._lock:
            self._db.execute("BEGIN")
            self._db.executemany(
                "INSERT INTO files (k, path, size, mtime_ns, hash, seen) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(k) DO UPDATE SET "
                "path = excluded.path, size = excluded.size, mtime_ns = excluded.mtime_ns, hash = excluded.hash, seen = excluded.seen", batch)
            self._db.execute("COMMIT")

    def remove(self, paths: Iterable[str]) -> None:
        batch = [(key(p),) for p in paths]
        if batch:
            with self._lock:
                self._db.execute("BEGIN")
                self._db.executemany("DELETE FROM files WHERE k = ?", batch)
                self._db.execute("COMMIT")

    def remove_under(self, folder: str) -> None:
        prefix = key(folder).rstrip("/") + "/"
        with self._lock:
            self._db.execute("DELETE FROM files WHERE substr(k, 1, ?) = ?", (len(prefix), prefix))

    def move_under(self, old: str, new: str) -> None:
        """A folder moved or was renamed: what was recorded under it is now under the new name."""
        old_prefix = old.replace("\\", "/").rstrip("/") + "/"
        new_prefix = new.replace("\\", "/").rstrip("/") + "/"
        with self._lock:
            rows = self._db.execute("SELECT path, size, mtime_ns, hash FROM files WHERE substr(k, 1, ?) = ?", (len(old_prefix), key(old_prefix))).fetchall()
            self._db.execute("BEGIN")
            for p, size, mtime, digest in rows:
                tail = p.replace("\\", "/")[len(old_prefix):]
                self._db.execute("DELETE FROM files WHERE k = ?", (key(p),))
                moved = new_prefix + tail
                self._db.execute("INSERT OR REPLACE INTO files (k, path, size, mtime_ns, hash, seen) VALUES (?, ?, ?, ?, ?, 0)", (key(moved), moved, size, mtime, digest))
            self._db.execute("COMMIT")

    def baselined(self) -> bool:
        """Has a full first look been made? (An empty folder is a baseline too: what appears in it later is news, not the first look.)"""
        with self._lock:
            row = self._db.execute("SELECT value FROM meta WHERE name = 'baseline'").fetchone()
        return bool(row and row[0])

    def set_baselined(self) -> None:
        with self._lock:
            self._db.execute("INSERT INTO meta (name, value) VALUES ('baseline', 1) ON CONFLICT(name) DO UPDATE SET value = 1")

    def next_run(self) -> int:
        with self._lock:
            row = self._db.execute("SELECT value FROM meta WHERE name = 'run'").fetchone()
            n = (row[0] if row else 0) + 1
            self._db.execute("INSERT INTO meta (name, value) VALUES ('run', ?) ON CONFLICT(name) DO UPDATE SET value = excluded.value", (n,))
        return n

    def mark_seen(self, paths: Iterable[str], run: int) -> None:
        batch = [(run, key(p)) for p in paths]
        if batch:
            with self._lock:
                self._db.execute("BEGIN")
                self._db.executemany("UPDATE files SET seen = ? WHERE k = ?", batch)
                self._db.execute("COMMIT")

    def unseen_under(self, root: str, run: int) -> list[str]:
        """Recorded files under a folder that a walk of it (run N) did not meet: they are gone."""
        prefix = key(root).rstrip("/") + "/"
        with self._lock:
            return [r[0] for r in self._db.execute("SELECT path FROM files WHERE substr(k, 1, ?) = ? AND seen <> ?", (len(prefix), prefix, run))]
