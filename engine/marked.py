"""What is marked restricted, in memory, for the first question every file event is asked: "is this one of the marked?"

A mark covers a file or a folder by its place, and tracks the content of what it covers by hash, so a copy anywhere is recognised. Asking the database about that for every file
event would be four queries each time; this keeps the active marks and every marked hash in memory and answers in one lookup. It is a speed-up for the stages that only need to
know (the facts on an event, Detective's weights), never the authority: a Flow checks the database itself at every step (engine/flow/guard.py) and so does everything that
acts on the answer. It reloads when a mark changes (`invalidate`) and at least once a minute, and it is bounded: past MAX_HASHES it says so and the stages fall back to
asking the database.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.database import Database

log = logging.getLogger(__name__)

MAX_HASHES = 500_000
MAX_AGE = 60.0


def _norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


class MarkedIndex:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._hash: dict[str, str] = {}                    # content hash -> the name of a mark it belongs to
        self._marks: dict[int, list[dict[str, Any]]] = {}  # machine -> its active marks
        self._at = 0.0
        self._stale = True
        self.overflowed = False

    def invalidate(self) -> None:
        self._stale = True

    async def ensure(self) -> None:
        if not self._stale and time.monotonic() - self._at < MAX_AGE:
            return
        marks = await self.db.marks.list()
        by_pc: dict[int, list[dict[str, Any]]] = {}
        for m in marks:
            by_pc.setdefault(m["pc_id"], []).append(m)
        hashes = await self.db.marks.active_hashes(MAX_HASHES + 1)
        self.overflowed = len(hashes) > MAX_HASHES
        if self.overflowed:
            log.warning("more than %d marked hashes: the in-memory index is not used for content, the database is asked", MAX_HASHES)
            hashes = hashes[:MAX_HASHES]
        self._hash = {h: name for h, name in hashes}
        self._marks = by_pc
        self._at = time.monotonic()
        self._stale = False

    async def reason(self, pc_id: int, path: str, digest: str | None = None) -> str | None:
        """Why this is marked restricted (by its place, or by its content), or None. From memory."""
        await self.ensure()
        p = _norm(path)
        for m in self._marks.get(pc_id, []):
            mp = _norm(m["path"])
            if p == mp or (m["kind"] == "folder" and p.startswith(mp + "/")):
                return f"{m['name']} is marked restricted" if m["kind"] == "file" else f"the folder {m['name']} is marked restricted"
        if digest and digest in self._hash:
            return f"its content is a copy of {self._hash[digest]}, which is marked restricted"
        if digest and self.overflowed:
            rows = await self.db.marks.active_with_hash(digest)
            if rows:
                return f"its content is a copy of {rows[0]['name']}, which is marked restricted"
        return None
