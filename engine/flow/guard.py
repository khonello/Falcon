"""A flow never touches anything restricted.

Not by a rule that was true when the flow was made: by looking, every time. Restricted is not a one-off property of a folder at the day a flow was set up; a folder is marked
later, a file is moved into a tier folder, a copy of marked content turns up, and a flow that checked once would carry on regardless. So every step a flow takes with a file
asks again, against what is true now, and nothing here is cached:

    * when a flow is made or edited: its source folder and every destination folder
    * when a change at the source is seen, and again when a file is about to be read (catch-up, a manual trigger, a retry all come through there)
    * when the file's content arrives (its content may be marked even though its name and place are not)
    * before it is written to each destination (the destination folder may have become restricted since)
    * before a copy the flow wrote is put away on a mirrored delete

A file is restricted when ANY of these is so: the index tags it restricted (or admin); it sits in a restricted tier folder; a restricted mark names it or a folder above it;
its content is the content of a marked file (a copy of a restricted file is restricted wherever it is). The first reason found is returned, in words a person can read.

When something turns restricted under a running flow, that flow is paused at once (`sweep`), not left to find out file by file.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from engine.resource.resource import derive_tag

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

RESTRICTED_TAGS = ("restricted", "admin")           # the admin tier is above restricted: a flow does not touch it either
REFUSED_EVERY = 600.0                               # a flow says it is refusing a file once in this long, not on every look
_told: dict[tuple[int, str], float] = {}


def reset_state() -> None:
    _told.clear()


def _norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def _covers(mark: dict[str, Any], path: str) -> bool:
    m, p = _norm(mark["path"]), _norm(path)
    return p == m or (mark["kind"] == "folder" and p.startswith(m + "/"))


async def restricted_reason(engine: Engine, pc_id: int | None, path: str, digest: str | None = None) -> str | None:
    """Why this file or folder must not be touched by a flow, or None. Always asks the current state."""
    if pc_id is None or not path:
        return None
    db = engine.db
    entry = await db.file_index.by_path(pc_id, path)
    if entry is not None and entry.get("resource_tag") in RESTRICTED_TAGS:
        return f"it is tagged {entry['resource_tag']}"
    pc = await db.accounts.pc(pc_id) or {}
    tier = derive_tag(path, str(pc.get("pc_type") or ""), pc.get("department_id"))
    if tier is not None and tier[0] in RESTRICTED_TAGS:
        return f"it is in the {tier[0]} tier folder"
    for mark in await db.marks.active_on_pc(pc_id):
        if _covers(mark, path):
            return f"{mark['name']} is marked restricted" if mark["kind"] == "file" else f"the folder {mark['name']} is marked restricted"
    content = digest or (entry or {}).get("content_hash")
    if content:
        for mark in await db.marks.active_with_hash(content):
            return f"its content is a copy of {mark['name']}, which is marked restricted"
    return None


async def refuse(engine: Engine, flow_id: int, pc_id: int | None, path: str, reason: str, *, step: str) -> None:
    """Say it was refused: always on the record, and to the person who made the flow at most once in a while."""
    await engine.audit.record(None, "flow.refused_restricted", target_type="flows", target_id=flow_id, pc_id=pc_id, detail={"path": path, "why": reason, "at": step})
    key = (flow_id, _norm(path))
    now = time.monotonic()
    if now - _told.get(key, -1e9) < REFUSED_EVERY:
        return
    _told[key] = now
    flow = await engine.db.flows.get(flow_id)
    if flow is not None:
        await engine.push_to_account(flow["created_by_account_id"], "flow.refused", {"flow_id": flow_id, "path": path, "why": reason})


async def sweep(engine: Engine, pc_id: int) -> int:
    """Something on this machine just became restricted (a mark, a tag): pause every flow whose source or destination folder is now restricted, and say why."""
    if not engine.db.connected:
        return 0
    paused = 0
    for row in await engine.db.flows.list_all():
        if row["status"] != "active":
            continue
        flow = await engine.db.flows.get(row["id"])                # (the list does not carry the destinations)
        if flow is None:
            continue
        why = None
        if flow["source_pc_id"] == pc_id:
            why = await restricted_reason(engine, pc_id, flow["source_path"])
        if why:
            await engine.db.flows.set_status(flow["id"], "paused", "restricted:source")
            await engine.audit.record(None, "flow.paused_restricted", target_type="flows", target_id=flow["id"], detail={"where": "source", "path": flow["source_path"], "why": why})
            await engine.push_to_account(flow["created_by_account_id"], "flow.refused", {"flow_id": flow["id"], "path": flow["source_path"], "why": why})
            paused += 1
            continue
        for dest in flow["destinations"]:
            if dest.get("destination_pc_id") != pc_id or dest.get("paused_reason"):
                continue
            why = await restricted_reason(engine, pc_id, dest["destination_path"])
            if why:
                await engine.db.flows.set_destination_pause(dest["id"], "destination:restricted")
                await engine.audit.record(None, "flow.paused_restricted", target_type="flow_destinations", target_id=dest["id"],
                                          detail={"flow_id": flow["id"], "where": "destination", "path": dest["destination_path"], "why": why})
                await engine.push_to_account(flow["created_by_account_id"], "flow.refused", {"flow_id": flow["id"], "path": dest["destination_path"], "why": why})
                paused += 1
    return paused
