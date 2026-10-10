"""The Global File Index (spec 6) -- the single most load-bearing shared mechanism.

Task verification, Flow collision/cycle checks, and Resource compliance all validate against
this one index. Populated by:
  * event-driven baseline: worker clients report OS file events (create/modify/move/copy) as they occur;
  * opportunistic full sweep: an idle worker client reports a full local sweep in batches, and stops the
    instant user input resumes (the throttling is client-side; the Engine just ingests batches).

Tracks: name, location, content hash, and a Resource access tag
(`admin` | `restricted` | `worker_dept` + scope department | `common`).

Wire shape of one entry/event (what worker clients send):
    {"op": "create|modify|move|copy|delete|attrib|security", "path": "C:/.../report.docx", "name": "report.docx",
     "hash": "<sha256>"?, "old_path": "..."?, "is_dir": true?, "resource_tag": "common"?, "scope_department_id": 3?}

`move` covers a rename (same folder) and a move; `old_path` is where it was. `attrib` and `security` are a change of
file attributes (read-only, hidden) and of permissions/owner, with the content untouched. Folders (`is_dir`) are
history and signals only: they are never rows in the index. Everything is recorded in `file_events`; a place a file has
left (moved away, deleted) is marked `gone_at`, the row kept.
"""

from __future__ import annotations

import logging
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_department_scope, require_role
from engine.resource.resource import allowed_tags_for
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.database import Database

log = logging.getLogger(__name__)

ACCESS_TAGS = ("admin", "restricted", "worker_dept", "common")  # file_index.resource_tag
OPS = ("create", "modify", "move", "copy", "delete", "attrib", "security")
# What Flow, Resource compliance and Task verification care about: the content of a file, or where it is. A change of
# attributes or permissions, or anything to a folder, is for the history and for automations only.
CONTENT_OPS = frozenset({"create", "modify", "move", "copy", "delete"})


class FileIndex:
    def __init__(self, db: Database) -> None:
        self.db = db
        # Modules interested in file events (Flow sync trigger, Resource compliance, Task
        # expectation) subscribe here rather than defining their own detection.
        self._subscribers: list[Any] = []
        self._observers: list[Any] = []

    def subscribe(self, callback: Any, *, every_op: bool = False) -> None:
        """callback(event: dict) -> Awaitable[None]. Called for every ingested file event that is about a file's
        content or place (CONTENT_OPS), after the index row is written, with `file_index_id` and `pc_id` added.
        `every_op=True` also hears attribute and permission changes and everything that happens to folders -- for
        automations, which can wait on any of them."""
        (self._observers if every_op else self._subscribers).append(callback)

    async def ingest_event(self, pc_id: int, event: dict[str, Any]) -> int | None:
        entry = _normalize(event)
        db = self.db.file_index
        op, path = entry["op"], entry["path"]
        file_index_id: int | None = None          # what subscribers are told (None for a delete, as before)
        known_id: int | None = None               # what the history refers to
        if entry["is_dir"]:
            pass                                  # a folder is history and a signal, never an index row
        elif op == "delete":
            known_id = await db.mark_gone(pc_id, path)       # the row is kept (no hard deletes), marked as gone
        elif op in ("attrib", "security"):
            row = await db.by_path(pc_id, path)              # nothing about the content changed: not re-indexed
            known_id = row["id"] if row else None
        else:
            file_index_id = known_id = await self._upsert(pc_id, entry, "event")
            if op == "move" and entry.get("old_path"):
                await db.mark_gone(pc_id, str(entry["old_path"]))    # it left its old place: this used to be forgotten
        await db.record_event(pc_id, op, path, old_path=entry.get("old_path"), is_dir=entry["is_dir"],
                              content_hash=entry.get("hash"), file_index_id=known_id)
        full = {"pc_id": pc_id, "file_index_id": file_index_id, **entry}
        if op in CONTENT_OPS and not entry["is_dir"]:
            for cb in self._subscribers:
                await cb(full)
        for cb in self._observers:
            await cb(full)
        return file_index_id

    async def ingest_sweep_batch(self, pc_id: int, entries: list[dict[str, Any]]) -> int:
        n = 0
        for raw in entries:
            entry = _normalize(raw)
            if entry["op"] == "delete":
                continue
            await self._upsert(pc_id, entry, "idle_sweep")
            n += 1
        return n

    async def _upsert(self, pc_id: int, entry: dict[str, Any], indexed_via: str) -> int:
        return await self.db.file_index.upsert(
            pc_id, entry["path"], entry["name"], entry.get("hash"), entry.get("resource_tag"),
            entry.get("scope_department_id"), indexed_via)

    # --- consumer queries -----------------------------------------------------------------------

    async def search(self, query: str, *, role: str, department_id: int | None) -> list[dict[str, Any]]:
        """Assistance search / Task target search, scoped to the caller's access tier."""
        return await self.db.file_index.search(query, allowed_tags=allowed_tags_for(role, department_id))

    async def name_collisions(self, name: str, *, pc_ids: list[int] | None = None) -> list[dict[str, Any]]:
        """Task Create-intent name-first check, scoped to the assignee's PCs when given.
        Surfaced to the assigner, never auto-resolved."""
        return await self.db.file_index.by_name(name, pc_ids=pc_ids)

    async def path_collision(self, pc_id: int | None, path: str) -> dict[str, Any] | None:
        """Flow Pre-Flight Collision Check: existing indexed content at a destination path."""
        if pc_id is None:
            return None  # remote storage is not indexed
        return await self.db.file_index.by_path(pc_id, path, present_only=True)

    async def restricted_copies(self, content_hash: str) -> list[dict[str, Any]]:
        """Resource Restricted File Tracking: every location a hash appears."""
        return await self.db.file_index.by_hash(content_hash)


def _normalize(event: dict[str, Any]) -> dict[str, Any]:
    op = str(event.get("op", "modify"))
    if op not in OPS:
        raise ProtocolError(ErrorCode.INVALID, f"unknown file op {op!r}")
    path = str(event.get("path", "")).strip()
    if not path:
        raise ProtocolError(ErrorCode.INVALID, "file event needs a path")
    tag = event.get("resource_tag")
    if tag is not None and tag not in ACCESS_TAGS:
        raise ProtocolError(ErrorCode.INVALID, f"unknown resource tag {tag!r}")
    return {
        "op": op,
        "path": path,
        "name": str(event.get("name") or PurePath(path).name),
        "hash": event.get("hash"),
        "old_path": event.get("old_path"),
        "is_dir": bool(event.get("is_dir")),
        "resource_tag": tag,
        "scope_department_id": event.get("scope_department_id"),
    }


# --- handlers (worker clients report in; operators query) ---------------------------------------

def _pc_id(ctx: Context, payload: dict[str, Any]) -> int:
    pc_id = ctx.identity.pc_id or payload.get("pc_id")
    if pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no pc_id for this connection")
    return int(pc_id)


@handler("index.event")
async def index_event(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    file_index_id = await ctx.engine.file_index.ingest_event(_pc_id(ctx, payload), payload.get("event") or {})
    return {"accepted": True, "file_index_id": file_index_id}


@handler("index.sweep_batch")
async def index_sweep_batch(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    n = await ctx.engine.file_index.ingest_sweep_batch(_pc_id(ctx, payload), payload.get("entries") or [])
    return {"accepted": n}


@handler("index.folders")
async def index_folders(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"pc_id"} -> the folders indexed on that machine, for choosing a flow's source or destination without typing a
    path. Operators only, and only for a machine in their scope."""
    ident = require_role(ctx, "super_user", "admin")
    pc_id = int_field(payload, "pc_id")
    pc = await ctx.engine.db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such pc")
    require_department_scope(ident, pc["department_id"])
    found = await ctx.engine.db.file_index.folders(pc_id)
    return {"pc_id": pc_id, "hostname": pc["hostname"],
            "folders": [{"path": f["folder"], "name": PurePath(f["folder"]).name or f["folder"], "files": f["files"]} for f in found]}


@handler("index.search")
async def index_search(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    if not query:
        raise ProtocolError(ErrorCode.INVALID, "query required")
    ident = ctx.identity
    results = await ctx.engine.file_index.search(query, role=ident.role or "worker",
                                                 department_id=ident.department_id)
    return {"results": results}
