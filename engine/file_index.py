"""The Global File Index (spec 6) -- the single most load-bearing shared mechanism.

Task verification, Flow collision/cycle checks, and Resource compliance all validate against
this one index. Populated by:
  * event-driven baseline: worker clients report OS file events (create/modify/move/copy) as they occur;
  * opportunistic full sweep: an idle worker client reports a full local sweep in batches, and stops the
    instant user input resumes (the throttling is client-side; the Engine just ingests batches).

Tracks: name, location, content hash, and a Resource access tag
(`admin` | `restricted` | `worker_dept` + scope department | `common`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub

if TYPE_CHECKING:
    from engine.database import Database

log = logging.getLogger(__name__)

ACCESS_TAGS = ("admin", "restricted", "worker_dept", "common")  # file_index.resource_tag


class FileIndex:
    def __init__(self, db: Database) -> None:
        self.db = db
        # Modules interested in file events (Flow sync trigger, Resource compliance, Task
        # expectation) subscribe here rather than defining their own detection.
        self._subscribers: list[Any] = []

    def subscribe(self, callback: Any) -> None:
        """callback(event: dict) -> Awaitable[None]. Called for every ingested file event."""
        self._subscribers.append(callback)

    async def ingest_event(self, pc_id: int, event: dict[str, Any]) -> None:
        """One OS file event from a worker client: {"op": "create|modify|move|copy|delete",
        "path": ..., "name": ..., "hash": ..., "old_path": ...?}."""
        await self.db.file_index.upsert(pc_id, event.get("path", ""), event.get("name", ""),
                                        event.get("hash"), event.get("access_tag"))
        for cb in self._subscribers:
            await cb({"pc_id": pc_id, **event})

    async def ingest_sweep_batch(self, pc_id: int, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            await self.db.file_index.upsert(pc_id, entry.get("path", ""), entry.get("name", ""),
                                            entry.get("hash"), entry.get("access_tag"))

    # --- consumer queries -----------------------------------------------------------------------

    async def search(self, query: str, *, allowed_tags: list[tuple[str, int | None]]) -> list[dict[str, Any]]:
        """Assistance search / Task target search, scoped to the caller's access tier."""
        return await self.db.file_index.search(query, allowed_tags=allowed_tags) or []

    async def name_collisions(self, name: str) -> list[dict[str, Any]]:
        """Task Create-intent name-first check: surfaced to the assigner, never auto-resolved."""
        return await self.db.file_index.by_name(name) or []

    async def path_collision(self, pc_id: int, path: str) -> dict[str, Any] | None:
        """Flow Pre-Flight Collision Check against existing indexed content."""
        return None  # SCAFFOLD

    async def restricted_copies(self, content_hash: str) -> list[dict[str, Any]]:
        """Resource Restricted File Tracking: every location a restricted hash appears."""
        return await self.db.file_index.by_hash(content_hash) or []


# --- handlers (worker clients report in; operators query) ------------------------------------------------

@handler("index.event")
async def index_event(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    pc_id = ctx.identity.pc_id or int(payload.get("pc_id", 0))
    await ctx.engine.file_index.ingest_event(pc_id, payload.get("event", {}))
    return {"accepted": True}


@handler("index.sweep_batch")
async def index_sweep_batch(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    pc_id = ctx.identity.pc_id or int(payload.get("pc_id", 0))
    entries = payload.get("entries", [])
    await ctx.engine.file_index.ingest_sweep_batch(pc_id, entries)
    return {"accepted": len(entries)}


@handler("index.search")
async def index_search(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("index.search", payload)
