"""What the open tasks expect to happen to files -- Task's fact, which the other features read.

A task that asks a person to put a file somewhere, or to deal with a particular one, is a statement that something is MEANT to happen to that content. Task owns that knowledge. It
writes it onto every file event as the fact `task_expects` (so Detective, which weighs how much a movement means, does not ask Task's tables itself), and anything that needs the
whole set (Detective's findings, which span several files) asks for it here. Kept for a short while and dropped the moment any task changes (the `task.*` events on the spine).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.server import Engine

TTL = 120.0
MAX_PER_PC = 20000                 # a worst case: a machine with a great many tasks asking for files
_cache: dict[int, tuple[float, set[str]]] = {}


def reset_state() -> None:
    _cache.clear()


def invalidate() -> None:
    _cache.clear()


async def hashes_for(engine: Engine, pc_id: int) -> set[str]:
    """The content hashes that the open tasks assigned to the person at this machine ask for."""
    now = time.monotonic()
    hit = _cache.get(pc_id)
    if hit is not None and now - hit[0] < TTL:
        return hit[1]
    things: set[str] = set()
    for t in await engine.db.tasks.open_with_items():
        if t.get("assignee_pc_id") != pc_id:
            continue
        for item in t["items"]:
            if item.get("file_hash"):
                things.add(item["file_hash"])
            elif item.get("target_type") == "file" and item.get("name"):
                for hit_row in await engine.db.file_index.by_name(str(item["name"]), pc_ids=[pc_id]):
                    if hit_row.get("content_hash"):
                        things.add(hit_row["content_hash"])
            if len(things) >= MAX_PER_PC:
                break
    _cache[pc_id] = (now, things)
    return things
