"""Synchronization (Flow -> Synchronization Mechanism, Conflict Handling, Failure Handling).

One detection mechanism: the Global File Index event stream.
  * An event on a *source* PC under an active flow's source_path triggers propagation.
  * An event on a *destination* PC under a destination_path is checked against the flow's own
    last write (write attribution = hash + who). A matching hash is the flow's own write; a
    different one is an external modification -> conflict handling.

Propagation relays content through the Engine (spec 3.1: "route commands and data"):

    source event -> push flow.read {transfer_id, path}            to the source PC
    source PC    -> request flow.content {transfer_id, hash, content_b64}
    Engine       -> push flow.apply {transfer_id, destination, relative_path, stages, content}
                    to each destination PC (each destination independently)
    destination  -> request flow.sync_result {transfer_id, destination_id, status, failure?}

Conflict: the destination PC is told to rename the external version `<name>-modified.<ext>`
(flow.resolve_conflict) and a fresh copy is re-synced from source alongside it.

Failure: only that destination is paused (`paused_reason = "<stage>:<kind>"`); the creator
and the destination owner get a persistent status; the suggestion is returned reactively.

Large files travel in chunks (CHUNK_BYTES raw each) both ways, so one message never outgrows what a connection reads at a time. A destination
that cannot be reached is paused as `destination:unreachable`, not forgotten, and when it comes back it is resumed and CAUGHT UP: the Engine asks
the source machine what it holds now (`flow.list` / `flow.listing`) and sends each destination exactly what it is missing (what was last
sent from the source is remembered per file, `flow_sync_log.source_hash`). The same catch-up runs when a flow is created over files that are
already there, when it is resumed, and when consent is granted: a destination is "updated to match source", not only told about new events.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.flow import flows as flowdefs
from engine.flow import guard, steps
from engine.hierarchy import reports
from engine.permissions import int_field, org_wide, require_account, str_field
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)


@dataclass
class Transfer:
    id: str
    flow_id: int
    source_pc_id: int
    source_path: str          # the file's full path on the source PC
    relative_path: str        # relative to the flow's source directory
    hash: str | None
    pending_destinations: set[int] = field(default_factory=set)
    content_b64: str | None = None
    parts: dict[int, bytes] = field(default_factory=dict)      # chunks arriving from the source
    data: bytes | None = None                                  # the whole file, once it has arrived
    modified: str | None = None                                # when it was last changed at the source (dates a step uses)
    bundles: dict[int, str] = field(default_factory=dict)      # destination -> the bundle this file goes into there (a Bundling step's run)
    created: float = field(default_factory=time.monotonic)


@dataclass
class Bundle:
    """One run of a Bundling step at one destination: the files go to the destination machine one by one (through the steps before it),
    which keeps them aside; when the last has arrived, it is told to make the one file (`flow.bundle_close`)."""
    id: str
    flow_id: int
    destination_id: int
    snapshot: str                                              # what went in (each file and its version): the same again is not bundled again
    pending: set[str] = field(default_factory=set)             # transfers still to arrive there
    files: int = 0
    sent: bool = False                                         # every file has been sent
    failed: str | None = None
    created: float = field(default_factory=time.monotonic)


BUNDLE_KEY = "<bundle>"                 # the sync log's source path for a destination's bundle (its source hash is the run's snapshot)


@dataclass
class Listing:
    flow_id: int
    only: set[int] | None
    entries: list[dict[str, Any]] = field(default_factory=list)
    created: float = field(default_factory=time.monotonic)
    truncated: bool = False


CHUNK_BYTES = 512 * 1024            # raw bytes per message (about 700 KB once encoded: far below the 4 MB a connection reads at a time)
MAX_RELAY_BYTES = 64 * 1024 * 1024
TRANSFER_SECONDS = 600.0            # a transfer nobody finished in this long is failed, not kept forever
MAX_LISTING = 200000                # a source folder with more files than this is caught up in part; the next healing pass carries on (hot files first)
MAX_LISTING_BATCH = 2000            # entries taken from one listing message
IN_FLIGHT = 4                       # a catch-up sends this many files at a time, so thousands of files do not flood the Engine

_transfers: dict[str, Transfer] = {}
_bundles: dict[str, Bundle] = {}
_listings: dict[str, Listing] = {}
_background: set[asyncio.Task[Any]] = set()
_settling: dict[tuple[int, str], asyncio.Task[Any]] = {}


def reset_state() -> None:
    guard.reset_state()
    _routes.clear()
    _transfers.clear()
    _bundles.clear()
    _closing.clear()
    _listings.clear()
    for waiting in list(_settling.values()):
        waiting.cancel()
    _settling.clear()
    for task in list(_background):
        task.cancel()
    _background.clear()


def _spawn(coro: Any) -> None:
    task = asyncio.ensure_future(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)


def modified_name(path: str) -> str:
    """report.xlsx -> report-modified.xlsx. Keeps the client's own separators: these are the
    worker PC's paths, never the Engine host's."""
    head, sep, name = _rsplit_sep(path)
    stem, dot, ext = name.rpartition(".")
    new = f"{stem}-modified.{ext}" if dot and stem else f"{name}-modified"
    return f"{head}{sep}{new}"


def _rsplit_sep(path: str) -> tuple[str, str, str]:
    cut = max(path.rfind("/"), path.rfind("\\"))
    if cut < 0:
        return "", "", path
    return path[:cut], path[cut], path[cut + 1:]


def join_client_path(directory: str, relative: str) -> str:
    """Join using the separator the directory already uses."""
    sep = "\\" if "\\" in directory and "/" not in directory else "/"
    return directory.rstrip("/\\") + sep + relative.replace("/", sep).replace("\\", sep)


def relative_under(path: str, directory: str) -> str | None:
    p, d = path.replace("\\", "/"), directory.replace("\\", "/").rstrip("/")
    if p.lower().startswith(d.lower() + "/"):
        return p[len(d) + 1:]
    return None


def source_relative(flow: dict[str, Any], path: str) -> str | None:
    """Where a path sits in a flow's source: relative to the folder, or, for a single-file flow, the file's own name when it is that file."""
    if flow.get("source_kind") == "file":
        same = path.replace("\\", "/").lower() == str(flow["source_path"]).replace("\\", "/").lower()
        return _rsplit_sep(path)[2] if same else None
    return relative_under(path, flow["source_path"])


def source_file(flow: dict[str, Any], rel: str) -> str:
    """The source file a relative path stands for: the file itself for a single-file flow."""
    return str(flow["source_path"]) if flow.get("source_kind") == "file" else join_client_path(flow["source_path"], rel)


def install(engine: Engine) -> None:
    engine.file_index.subscribe(lambda event: _on_file_event(engine, event), stage="act", name="flow")
    engine.file_index.subscribe(lambda event: _flow_fact(engine, event), every_op=True, stage="act", name="flow.fact")


async def wrote_here(engine: Engine, pc_id: int, path: str, digest: str | None) -> bool:
    """Falcon's own flows write files too: did one write this file, with this content? (Then it is Falcon's doing, not a person's.)"""
    for dest in await engine.db.flows.destinations_for_pc(pc_id):
        if relative_under(path, dest["destination_path"]) is None:
            continue
        own = await engine.db.flows.last_flow_write_at(dest["id"], path)
        if own is not None and (digest is None or own.get("content_hash") == digest):
            return True
    return False


_routes: dict[int, tuple[float, list[tuple[int, str, str]], list[tuple[int, str]]]] = {}      # machine -> (when, [(flow, source, kind)], [(flow, destination folder)])
ROUTES_TTL = 30.0


async def _routes_of(engine: Engine, pc_id: int) -> tuple[list[tuple[int, str, str]], list[tuple[int, str]]]:
    hit = _routes.get(pc_id)
    if hit is not None and time.monotonic() - hit[0] < ROUTES_TTL:
        return hit[1], hit[2]
    sources = [(s["id"], s["source_path"], s.get("source_kind") or "folder") for s in await engine.db.flows.sources_for_pc(pc_id)]
    dests = [(d["flow_id"], d["destination_path"]) for d in await engine.db.flows.destinations_for_pc(pc_id)]
    _routes[pc_id] = (time.monotonic(), sources, dests)
    return sources, dests


async def _flow_fact(engine: Engine, event: dict[str, Any]) -> None:
    """Written onto the event for the stages after Flow, so nothing after it asks Flow's tables itself:
    `flow_wrote`   a flow's own write (Falcon's doing, not a person's)
    `flow_route`   the flows that read from, and write to, the folder this file is in
    `flow_bypass`  a person put here what a flow delivers here: the same content is in that flow's source folder, and the flow did not write this copy (the sanctioned way
                   to move it is the flow, which is checked, consented and audited; by hand is a way round it)"""
    facts = event.get("facts")
    if facts is None or not engine.db.connected or event.get("is_dir"):
        return
    path, pc_id = event["path"], event["pc_id"]
    sources, dests = await _routes_of(engine, pc_id)
    in_src = [fid for fid, src, kind in sources if source_relative({"source_path": src, "source_kind": kind}, path) is not None]
    in_dst = [fid for fid, folder in dests if relative_under(path, folder) is not None]
    if in_src or in_dst:
        facts["flow_route"] = {"source": in_src, "destination": in_dst}
    if event["op"] not in ("create", "modify", "move", "copy"):
        return
    digest = event.get("hash") or facts.get("hash")
    facts["flow_wrote"] = await wrote_here(engine, pc_id, path, digest)
    if in_dst and digest and not facts["flow_wrote"] and event["op"] in ("create", "copy", "move"):
        for fid in in_dst:
            flow = await engine.db.flows.get(fid)
            if flow is None or flow["status"] == "inactive":
                continue
            for other in await engine.db.file_index.by_hash(digest):
                if other["pc_id"] == flow["source_pc_id"] and source_relative(flow, other["path"]) is not None:
                    facts["flow_bypass"] = fid
                    return


# --- detection ----------------------------------------------------------------------------------

async def _on_file_event(engine: Engine, event: dict[str, Any]) -> None:
    if not engine.db.connected:
        return
    pc_id = event["pc_id"]
    if event["op"] == "move" and event.get("old_path"):
        await _follow_moves(engine, pc_id, str(event["old_path"]), event["path"])
    if event["op"] == "delete":
        for src in await engine.db.flows.sources_for_pc(pc_id):
            rel = source_relative(src, event["path"])
            if rel is None:
                continue
            if src.get("on_source_delete") == "mirror":
                if _live(src):
                    await remove_at_destinations(engine, src["id"], rel)
            else:
                await _ask_about_deleted(engine, src, pc_id, rel)
        return
    # A file under an unresolved Resource violation is ignored by the system (Resource ->
    # Compliance): Flow never moves it.
    if event.get("file_index_id") in await engine.db.resource.ignored_file_ids(pc_id):
        return
    # Source side: does this event fall under an active flow's source directory?
    for src in await engine.db.flows.sources_for_pc(pc_id):
        rel = source_relative(src, event["path"])
        if rel is not None and _live(src):                                    # an hourly or run-only flow copies what changed when it runs
            if not await guard.gate(engine, src["id"], pc_id, event["path"], event.get("hash"), step="seen at the source"):
                continue                                                      # paused, and the owner asked
            await _settle_then_propagate(engine, src["id"], event["path"], rel, event.get("hash"))
    # Destination side: attribution check.
    for dest in await engine.db.flows.destinations_for_pc(pc_id):
        followed = dest.get("followed_path")
        rel = (_rsplit_sep(event["path"])[2] if followed and _same_path(followed, event["path"])
               else relative_under(event["path"], dest["destination_path"]) if dest["destination_path"] else None)
        if rel is None or dest["flow_status"] != "active" or dest.get("paused_reason"):
            continue
        await _check_destination_write(engine, dest, event, rel)


def _live(flow: dict[str, Any]) -> bool:
    """Does this flow copy the moment a file changes? Hourly and run-only flows leave changes to be found when they run (a listing finds them)."""
    return (flow.get("run_mode") or "realtime") == "realtime"


# Why a flow is caught up, and which run modes that applies to: a flow that runs on its own is healed and caught up whenever; an hourly one
# on the hour or by Run; a run-only one by Run alone.
CATCH_UP_FOR = {"realtime": {"heal", "hourly", "run"}, "hourly": {"hourly", "run"}, "manual": {"run"}}


def _same_path(a: str, b: str) -> bool:
    return a.replace("\\", "/").lower() == b.replace("\\", "/").lower()


async def _follow_moves(engine: Engine, pc_id: int, old: str, new: str) -> None:
    """A single-file flow follows its file (docs/design/v1-it-admin.md). At the source: a rename or move of the file takes the flow's source along,
    so its changes keep syncing. At a destination: the flow's own copy moved or renamed there is where the next change is written."""
    db = engine.db
    for src in await db.flows.file_sources_at(pc_id, old):
        await db.flows.follow_source(src["id"], new)
        _routes.pop(pc_id, None)
        await engine.audit.record(None, "flow.source_followed", target_type="flows", target_id=src["id"], pc_id=pc_id,
                                  detail={"from": old, "to": new})
    for dest in await db.flows.destinations_for_pc(pc_id):
        flow = await db.flows.get(dest["flow_id"])
        if flow is None or flow.get("source_kind") != "file":
            continue
        current = dest.get("followed_path") or (await db.flows.last_flow_write_at_any(dest["id"]) or {}).get("written_path")
        if current and _same_path(current, old):
            await db.flows.follow_destination(dest["id"], new)
            await engine.audit.record(None, "flow.copy_followed", target_type="flow_destinations", target_id=dest["id"], pc_id=pc_id,
                                      detail={"flow_id": flow["id"], "from": old, "to": new})


async def _check_destination_write(engine: Engine, dest: dict[str, Any], event: dict[str, Any], rel: str) -> None:
    own = await engine.db.flows.last_flow_write_at(dest["id"], event["path"])
    if own is None:
        return  # this file was never written by the flow: pre-existing content, handled at pre-flight
    if own["content_hash"] == event.get("hash"):
        return  # our own write landing -- not a conflict
    # External modification of a file the flow owns: preserve it, then re-sync from its source.
    source_rel = own.get("source_relative_path") or rel
    await engine.db.flows.log_sync(dest["id"], event.get("hash") or "", "external", None, conflict_resolved=True,
                                   source_relative_path=source_rel, written_path=event["path"])
    await engine.audit.record(None, "flow.conflict", target_type="flow_destinations", target_id=dest["id"],
                              detail={"path": event["path"], "hash": event.get("hash")})
    await engine.push_to_pc(dest["destination_pc_id"], "flow.resolve_conflict", {
        "flow_id": dest["flow_id"], "destination_id": dest["id"], "path": event["path"],
        "rename_to": modified_name(event["path"])})
    flow = await engine.db.flows.get(dest["flow_id"])
    if flow is not None:
        await propagate(engine, flow["id"], source_file(flow, source_rel), source_rel, None,
                        only_destination=dest["id"])


# --- a file deleted at the source ---------------------------------------------------------------

REMOVED = "removed"             # the content hash a sync-log entry carries when the flow put a destination's copy away


async def remove_at_destinations(engine: Engine, flow_id: int, rel: str, *, only: set[int] | None = None, decided: bool = False) -> int:
    """A mirroring flow: the file is gone from the source, so each destination is asked to put away the copy THE FLOW WROTE (never anything else).
    The destination's machine moves it aside (nothing is destroyed) and says what it did. A destination that is away is dealt with on catch-up."""
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] != "active" or (flow.get("on_source_delete") != "mirror" and not decided):
        return 0                                                           # a flow that keeps its copies removes one only when a person decided so
    asked = 0
    online = engine.online_pc_ids()
    for dest in flow["destinations"]:
        if dest.get("paused_reason") or (only is not None and dest["id"] not in only) or dest["destination_pc_id"] not in online:
            continue
        last = await engine.db.flows.last_written_for(dest["id"], rel)
        if not last or not last.get("path") or not last.get("hash") or last["hash"] == REMOVED:
            continue                                                       # the flow never wrote it here, or it is already put away
        if not await guard.gate(engine, flow_id, dest["destination_pc_id"], last["path"], last["hash"], step="before putting a copy away"):
            continue
        await engine.push_to_pc(dest["destination_pc_id"], "flow.remove", {
            "flow_id": flow_id, "destination_id": dest["id"], "relative_path": rel, "path": last["path"], "hash": last["hash"],
            "root": dest["destination_path"]})
        asked += 1
    return asked


DELETED_LISTED = 50


async def _ask_about_deleted(engine: Engine, src: dict[str, Any], pc_id: int, rel: str) -> None:
    """A flow that keeps its copies when a file is deleted at its source (the default) keeps them, and says so on the Issues page, where an
    Admin may remove them after all (the user, 2 Nov 2026: "keep, or buttons to decide in the Issues page"). One open issue per flow gathers
    its deleted files; only the files the flow had actually copied are counted (a deleted file it never carried changes nothing)."""
    flow = await engine.db.flows.get(src["id"])
    if flow is None:
        return
    carried = False
    for d in flow["destinations"]:
        if await engine.db.flows.last_written_for(d["id"], rel):
            carried = True
            break
    if not carried:
        return
    group = flow.get("merged_into") or flow["id"]
    from engine.console import issues

    issue_id, created = await issues.raise_issue(
        engine, type_="flow", severity="low", title="A file was deleted at a flow's source", subject=rel, pc_id=pc_id,
        source_table="flow_source_delete", source_id=group,
        detail={"kind": "source_deleted", "flow_id": group, "files": [{"flow_id": flow["id"], "relative_path": rel}], "more": 0})
    if not created:
        issue = await engine.db.issues.get(issue_id)
        detail = dict((issue or {}).get("detail") or {})
        files = list(detail.get("files") or [])
        if not any(f["relative_path"] == rel and f["flow_id"] == flow["id"] for f in files):
            if len(files) < DELETED_LISTED:
                files.append({"flow_id": flow["id"], "relative_path": rel})
            else:
                detail["more"] = int(detail.get("more") or 0) + 1
            n = len(files) + int(detail.get("more") or 0)
            await engine.db.issues.set_detail(issue_id, {"files": files, "more": detail.get("more", 0)})
            await engine.db.issues.set_severity(issue_id, "low", title=f"{n} files were deleted at a flow's source", subject=rel)


@handler("flow.remove_result")
async def remove_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The destination machine reports what it did: {"destination_id", "relative_path", "status": "removed"|"kept"|"missing", "path", "moved_to"?}"""
    ident = require_account(ctx)
    dest = await ctx.engine.db.flows.destination(int_field(payload, "destination_id"))
    if dest is None or dest["destination_pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "not the destination pc")
    status = str_field(payload, "status", choices=("removed", "kept", "missing"))
    rel, path = str_field(payload, "relative_path"), str(payload.get("path") or "")
    flow = await ctx.engine.db.flows.get(dest["flow_id"])
    if status in ("removed", "missing"):
        # recorded so a catch-up knows the destination no longer holds this file, and gives it back if the source brings it again
        await ctx.engine.db.flows.log_sync(dest["id"], REMOVED, "flow_sync", None, source_relative_path=rel, written_path=path or None, source_hash=None)
        await ctx.engine.audit.record(ctx, "flow.removed", target_type="flow_destinations", target_id=dest["id"],
                                      detail={"flow_id": dest["flow_id"], "relative_path": rel, "moved_to": payload.get("moved_to"), "status": status})
    else:
        await ctx.engine.audit.record(ctx, "flow.kept", target_type="flow_destinations", target_id=dest["id"],
                                      detail={"flow_id": dest["flow_id"], "relative_path": rel, "why": "it was changed after the flow wrote it"})
        if flow is not None:
            await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.conflict",
                                             {"flow_id": flow["id"], "destination_id": dest["id"], "kept": path, "relative_path": rel,
                                              "why": "deleted at the source, but changed here since: kept"})
    return {"recorded": True}


# --- propagation --------------------------------------------------------------------------------

async def _settle_then_propagate(engine: Engine, flow_id: int, path: str, rel: str, digest: str | None) -> None:
    """A file being written (a big copy, an editor saving) raises event after event: read it once, a moment after the last, not once per event
    (each early read would be a half-written file, sent and then replaced)."""
    delay = engine.settings.flow_settle_seconds
    if delay <= 0:
        await propagate(engine, flow_id, path, rel, digest)
        return
    key = (flow_id, rel.replace("\\", "/").lower())
    previous = _settling.pop(key, None)
    if previous is not None:
        previous.cancel()

    async def later() -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        _settling.pop(key, None)
        await propagate(engine, flow_id, path, rel, digest)

    task = asyncio.ensure_future(later())
    _settling[key] = task
    _background.add(task)
    task.add_done_callback(_background.discard)


def bundling(flow: dict[str, Any], dest: dict[str, Any]) -> dict[str, Any] | None:
    """The Bundling step on this destination's path, if it has one."""
    return next((st for st in flowdefs.stage_chain(flow, dest) if st["stage_type"] == "bundling"), None)


async def propagate(engine: Engine, flow_id: int, source_file: str, relative_path: str, file_hash: str | None,
                    *, only_destination: int | None = None, only: set[int] | None = None, bundle_for: dict[int, str] | None = None) -> str | None:
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] != "active":
        return None
    if not await guard.gate(engine, flow_id, flow["source_pc_id"], source_file, file_hash, step="before reading"):
        return None
    wanted = only if only is not None else ({only_destination} if only_destination is not None else None)
    # A destination that bundles takes files only in its run (bundle_for); a Choosing step that does not take this file: never read for it
    targets = [d for d in flow["destinations"] if not d.get("paused_reason") and (wanted is None or d["id"] in wanted)
               and (bundling(flow, d) is None or (bundle_for or {}).get(d["id"]))
               and steps.chosen(flowdefs.stage_chain(flow, d), relative_path)]
    if not targets:
        return None
    transfer = Transfer(id=uuid.uuid4().hex, flow_id=flow_id, source_pc_id=flow["source_pc_id"],
                        source_path=source_file, relative_path=relative_path, hash=file_hash,
                        pending_destinations={d["id"] for d in targets},
                        bundles={d["id"]: (bundle_for or {})[d["id"]] for d in targets if (bundle_for or {}).get(d["id"])})
    for bundle_id in transfer.bundles.values():
        if bundle_id in _bundles:
            _bundles[bundle_id].pending.add(transfer.id)
    _transfers[transfer.id] = transfer
    await engine.push_to_pc(flow["source_pc_id"], "flow.read",
                            {"transfer_id": transfer.id, "flow_id": flow_id, "path": source_file})
    return transfer.id


async def _apply_to_destinations(engine: Engine, transfer: Transfer) -> None:
    flow = await engine.db.flows.get(transfer.flow_id)
    if flow is None:
        return
    online = engine.online_pc_ids()
    for dest in flow["destinations"]:
        if dest["id"] not in transfer.pending_destinations:
            continue
        if dest["destination_pc_id"] is None:
            await _fail_destination(engine, flow, dest, "destination:unsupported")
            transfer.pending_destinations.discard(dest["id"])
            await _bundle_skip(engine, transfer, dest["id"])
            continue
        if dest["destination_pc_id"] not in online:
            # not forgotten: paused as unreachable, and resumed and caught up when the machine returns
            await _fail_destination(engine, flow, dest, "destination:unreachable")
            transfer.pending_destinations.discard(dest["id"])
            await _bundle_skip(engine, transfer, dest["id"])
            continue
        followed = dest.get("followed_path") if flow.get("source_kind") == "file" else None
        # a single-file flow writes where its copy now is when someone moved it; the destination folder otherwise
        folder, name = (_rsplit_sep(followed)[0], _rsplit_sep(followed)[2]) if followed else (dest["destination_path"], transfer.relative_path)
        target = join_client_path(folder, name)
        if not (await guard.gate(engine, flow["id"], dest["destination_pc_id"], dest["destination_path"], step="before writing")
                and await guard.gate(engine, flow["id"], dest["destination_pc_id"], target, step="before writing")):
            transfer.pending_destinations.discard(dest["id"])               # the flow is paused; what is left of this transfer is caught up after consent
            await _bundle_skip(engine, transfer, dest["id"])
            continue
        chain = flowdefs.stage_chain(flow, dest)
        data = transfer.data
        size = len(data) if data is not None else (len(base64.b64decode(transfer.content_b64)) if transfer.content_b64 else None)
        if not steps.chosen(chain, transfer.relative_path, size):           # a Choosing step by size: decided now its size is known
            transfer.pending_destinations.discard(dest["id"])
            await _left_out(engine, flow, dest, transfer, "not taken by a Choosing step")
            continue
        base = {"transfer_id": transfer.id, "flow_id": flow["id"], "destination_id": dest["id"],
                "destination_path": folder, "relative_path": name,
                "hash": transfer.hash, "modified": transfer.modified,
                # (a single-file copy someone moved keeps the name it has now: Renaming is for the copy the flow places)
                "stages": [st for st in chain if st["stage_type"] not in ("choosing", "bundling") and not (followed and st["stage_type"] == "renaming")],
                # what the flow itself last wrote there: anything else already at that place is someone's, and is kept, not overwritten
                "previous": await engine.db.flows.last_written_for(dest["id"], transfer.relative_path)}
        if transfer.bundles.get(dest["id"]):
            base["bundle"] = transfer.bundles[dest["id"]]                  # kept aside at the destination until its run's bundle is made
        data = transfer.data
        if data is None or len(data) <= CHUNK_BYTES:
            content = transfer.content_b64 if data is None else base64.b64encode(data).decode("ascii")
            await engine.push_to_pc(dest["destination_pc_id"], "flow.apply", {**base, "content_b64": content})
            continue
        total = (len(data) + CHUNK_BYTES - 1) // CHUNK_BYTES
        for index in range(total):
            piece = data[index * CHUNK_BYTES:(index + 1) * CHUNK_BYTES]
            await engine.push_to_pc(dest["destination_pc_id"], "flow.apply",
                                    {**base, "chunk": {"index": index, "total": total}, "content_b64": base64.b64encode(piece).decode("ascii")})
    if not transfer.pending_destinations:
        _transfers.pop(transfer.id, None)


async def _left_out(engine: Engine, flow: dict[str, Any], dest: dict[str, Any], transfer: Transfer, why: str) -> None:
    """A file a step did not take or could not convert, set to be left out: kept on the record with its source version (so it is not sent
    again for nothing), and said. In a bundle's run it is simply not in the bundle."""
    if transfer.bundles.get(dest["id"]):
        await _bundle_step(engine, transfer, dest["id"])
        return
    await engine.db.flows.log_sync(dest["id"], "", "flow_sync", None, source_relative_path=transfer.relative_path, source_hash=transfer.hash,
                                   outcome="left_out")
    await engine.audit.record(None, "flow.left_out", target_type="flow_destinations", target_id=dest["id"],
                              detail={"flow_id": flow["id"], "relative_path": transfer.relative_path, "why": why})


# --- a Bundling step's run -----------------------------------------------------------------------------------------------------------

async def _bundle_skip(engine: Engine, transfer: Transfer, dest_id: int) -> None:
    """A file of a bundle's run that did not reach the destination (held for consent, the destination away): the run is given up quietly."""
    bundle_id = transfer.bundles.get(dest_id)
    b = _bundles.get(bundle_id) if bundle_id else None
    if b is not None:
        b.failed = b.failed or ""
        await _bundle_step(engine, transfer, dest_id)


async def _bundle_step(engine: Engine, transfer: Transfer, dest_id: int, *, arrived: bool = False, failed: str | None = None) -> None:
    bundle_id = transfer.bundles.get(dest_id)
    b = _bundles.get(bundle_id) if bundle_id else None
    if b is None:
        return
    b.pending.discard(transfer.id)
    if arrived:
        b.files += 1
    if failed and not b.failed:
        b.failed = failed
    await _bundle_close(engine, b)


async def _bundle_close(engine: Engine, b: Bundle) -> None:
    """Every file of the run has arrived (or not): the destination makes the bundle, or drops what it kept aside."""
    if not b.sent or b.pending:
        return
    _bundles.pop(b.id, None)
    flow = await engine.db.flows.get(b.flow_id)
    dest = next((d for d in (flow or {}).get("destinations", []) if d["id"] == b.destination_id), None)
    if flow is None or dest is None or dest["destination_pc_id"] is None:
        return
    step = bundling(flow, dest)
    if b.failed is not None or not b.files or step is None:
        await engine.push_to_pc(dest["destination_pc_id"], "flow.bundle_drop", {"bundle_id": b.id})
        if b.failed:
            await _fail_destination(engine, flow, dest, b.failed if ":" in b.failed else "bundling:bundle_failed")
        return
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    name = steps.bundle_name(step["config"], flow.get("name"), today)
    _closing[b.id] = b
    await engine.push_to_pc(dest["destination_pc_id"], "flow.bundle_close", {
        "bundle_id": b.id, "flow_id": flow["id"], "destination_id": dest["id"], "destination_path": dest["destination_path"], "name": name,
        "folders": step["config"]["settings"].get("folders", "keep"),
        "previous": await engine.db.flows.last_written_for(dest["id"], BUNDLE_KEY)})


async def start_bundles(engine: Engine, flow: dict[str, Any], entries: list[dict[str, Any]], targets: list[dict[str, Any]],
                        given: dict[int, dict[str, Any]]) -> None:
    """A run of a flow with Bundling: each bundling destination gets every file of the folder its Choosing steps take, as the folder is now,
    unless that is exactly what its last bundle was made from."""
    for dest in targets:
        if bundling(flow, dest) is None:
            continue
        chain = flowdefs.stage_chain(flow, dest)
        taken = sorted((e for e in entries if steps.chosen(chain, e["relative_path"])), key=lambda e: e["relative_path"].lower())
        snapshot = hashlib.sha256("\n".join(f"{e['relative_path']}\0{e['hash']}" for e in taken).encode("utf-8")).hexdigest()
        if not taken or given[dest["id"]].get(BUNDLE_KEY.lower()) == snapshot:
            continue                                                   # nothing to bundle, or nothing changed since the last bundle
        b = Bundle(uuid.uuid4().hex, flow["id"], dest["id"], snapshot)
        _bundles[b.id] = b
        for entry in taken:
            while sum(1 for t in _transfers.values() if t.flow_id == flow["id"]) >= IN_FLIGHT:
                await asyncio.sleep(0.05)
            rel = entry["relative_path"]
            await propagate(engine, flow["id"], source_file(flow, rel), rel, entry["hash"], only={dest["id"]}, bundle_for={dest["id"]: b.id})
        b.sent = True
        await _bundle_close(engine, b)


_closing: dict[str, Bundle] = {}            # bundles the destination was told to make: waiting for flow.bundle_result


@handler("flow.bundle_result")
async def bundle_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The destination made a bundle (or could not): {"bundle_id", "status": "success"|"failed", "written_path"?, "written_hash"?, "files"?,
    "size_before"?, "size_after"?, "preserved"?}."""
    ident = require_account(ctx)
    b = _closing.pop(str_field(payload, "bundle_id"), None)
    dest = await ctx.engine.db.flows.destination(b.destination_id) if b else None
    if b is None or dest is None or dest["destination_pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such bundle for this pc")
    flow = await ctx.engine.db.flows.get(b.flow_id)
    assert flow is not None
    if str_field(payload, "status", choices=("success", "failed")) == "failed":
        await _fail_destination(ctx.engine, flow, dest, "bundling:bundle_failed")
        return {"recorded": True}
    before = payload.get("size_before") if isinstance(payload.get("size_before"), int) else None
    await ctx.engine.db.flows.log_sync(dest["id"], str(payload.get("written_hash") or ""), "flow_sync", None, source_relative_path=BUNDLE_KEY,
                                       written_path=payload.get("written_path"), source_hash=b.snapshot, outcome="new" if before is None else "changed",
                                       bytes_before=before, bytes_after=payload.get("size_after") if isinstance(payload.get("size_after"), int) else None)
    if payload.get("preserved"):
        await ctx.engine.db.flows.log_sync(dest["id"], "", "external", None, conflict_resolved=True, source_relative_path=BUNDLE_KEY,
                                           written_path=str(payload["preserved"]), outcome="kept_beside", bytes_before=before)
    await ctx.engine.audit.record(ctx, "flow.bundled", target_type="flow_destinations", target_id=dest["id"],
                                  detail={"flow_id": flow["id"], "files": b.files, "path": payload.get("written_path")})
    await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.synced",
                                     {"flow_id": flow["id"], "destination_id": dest["id"], "relative_path": str(payload.get("written_path") or ""), "bundle": True})
    return {"recorded": True}


async def _fail_destination(engine: Engine, flow: dict[str, Any], dest: dict[str, Any], reason: str) -> None:
    await engine.db.flows.set_destination_pause(dest["id"], reason)
    await engine.audit.record(None, "flow.failed", target_type="flow_destinations", target_id=dest["id"],
                              detail={"flow_id": flow["id"], "reason": reason})
    await engine.announce("flow.failed", {"flow_id": flow["id"], "destination_id": dest["id"], "reason": reason}, source="system", pc=dest["destination_pc_id"])
    report_id = await reports.emit(engine, "flow_failure", source_table="flow_destinations", source_id=dest["id"],
                                   summary=f"flow #{flow['id']} -> {dest['destination_path']}: {reason}")
    payload = {"flow_id": flow["id"], "destination_id": dest["id"], "destination_path": dest["destination_path"],
               "reason": reason, "suggestion": flowdefs.suggestion_for(reason), "report_id": report_id}
    await engine.push_to_account(flow["created_by_account_id"], "flow.failed", payload)
    await engine.push_to_account(dest["owner_account_id"], "flow.failed", payload)
    from engine.control import events

    await events.on_signal(engine, dest["destination_pc_id"] or flow["source_pc_id"], "flow.failed",
                           {"flow_id": flow["id"], "destination_id": dest["id"], "reason": reason})


# --- handlers (worker clients report in) --------------------------------------------------------

@handler("flow.content")
async def content(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Source PC answers flow.read: {"transfer_id", "hash", "content_b64"} or
    {"transfer_id", "error": "unreadable"}."""
    ident = require_account(ctx)
    transfer = _transfers.get(str_field(payload, "transfer_id"))
    if transfer is None or transfer.source_pc_id != ident.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such transfer for this pc")
    if payload.get("error"):
        flow = await ctx.engine.db.flows.get(transfer.flow_id)
        if flow:
            for dest in flow["destinations"]:
                if dest["id"] in transfer.pending_destinations:
                    await _fail_destination(ctx.engine, flow, dest, f"source:{payload['error']}")
        _transfers.pop(transfer.id, None)
        return {"accepted": False}
    transfer.hash = payload.get("hash") or transfer.hash
    transfer.modified = str(payload["modified"]) if payload.get("modified") else transfer.modified
    if not await guard.gate(ctx.engine, transfer.flow_id, transfer.source_pc_id, transfer.source_path, transfer.hash, step="when its content arrived"):
        _transfers.pop(transfer.id, None)
        return {"accepted": False, "refused": "restricted"}
    chunk = payload.get("chunk")
    if chunk is not None:
        try:
            index, total = int(chunk["index"]), int(chunk["total"])
            transfer.parts[index] = base64.b64decode(str(payload.get("content_b64", "")))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProtocolError(ErrorCode.INVALID, "chunk needs an index and a total, and its content") from exc
        if not 0 <= index < total or total * CHUNK_BYTES > MAX_RELAY_BYTES + CHUNK_BYTES:
            raise ProtocolError(ErrorCode.INVALID, "chunk out of range")
        if len(transfer.parts) < total:
            return {"accepted": True, "waiting": total - len(transfer.parts)}
        transfer.data = b"".join(transfer.parts[i] for i in range(total))
        transfer.parts.clear()
        if transfer.hash and hashlib.sha256(transfer.data).hexdigest() != transfer.hash:
            flow = await ctx.engine.db.flows.get(transfer.flow_id)
            for dest in (flow or {}).get("destinations", []):
                if dest["id"] in transfer.pending_destinations:
                    await _fail_destination(ctx.engine, flow, dest, "source:unreadable")
            _transfers.pop(transfer.id, None)
            return {"accepted": False}
    else:
        transfer.content_b64 = str(payload.get("content_b64", ""))
    await _apply_to_destinations(ctx.engine, transfer)
    return {"accepted": True, "destinations": len(transfer.pending_destinations)}


@handler("flow.sync_result")
async def sync_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Destination PC reports the outcome of flow.apply:
    {"transfer_id", "destination_id", "status": "success"|"failed"|"left_out"|"kept_aside", "written_hash"?, "replaced"?: {path, moved_to?, kept?},
     "as_is"?: [what a Conversion could not do], "failure": {"stage_type": "destination"|..., "kind": str}?}"""
    ident = require_account(ctx)
    transfer = _transfers.get(str_field(payload, "transfer_id"))
    dest_id = int_field(payload, "destination_id")
    if transfer is None or dest_id not in transfer.pending_destinations:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such pending transfer/destination")
    dest = await ctx.engine.db.flows.destination(dest_id)
    if dest is None or dest["destination_pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "not the destination pc")
    flow = await ctx.engine.db.flows.get(transfer.flow_id)
    assert flow is not None
    status = str_field(payload, "status", choices=("success", "failed", "left_out", "kept_aside"))
    if payload.get("as_is"):                    # a Conversion that could not be done here: the file went as it is, and that is said
        await ctx.engine.audit.record(ctx, "flow.not_converted", target_type="flow_destinations", target_id=dest_id,
                                      detail={"flow_id": flow["id"], "relative_path": transfer.relative_path, "steps": list(payload["as_is"])[:5]})
    if transfer.bundles.get(dest_id):           # a file of a bundle's run: kept aside at the destination, not a copy of its own
        failure = payload.get("failure") or {}
        await _bundle_step(ctx.engine, transfer, dest_id, arrived=status == "kept_aside",
                           failed=f"{failure.get('stage_type', 'destination')}:{failure.get('kind', 'unknown')}" if status == "failed" else None)
        status = "bundled"
    elif status == "left_out":
        await _left_out(ctx.engine, flow, dest, transfer, str(payload.get("why") or "a step could not convert it"))
    if status == "success":
        written = payload.get("written_hash") or transfer.hash or ""

        def size(key: str) -> int | None:
            value = payload.get(key)
            return int(value) if isinstance(value, int) and value >= 0 else None

        before, after = size("size_before"), size("size_after")
        # A Worker that says no size before was writing where nothing was: the file is new there. One that says nothing (older) leaves it unknown.
        outcome = None if "size_before" not in payload else "new" if before is None else "changed"
        older = payload.get("replaced") if isinstance(payload.get("replaced"), dict) else None
        if older and not older.get("kept"):      # this version has a new name (Add a date): the copy under the old one was put aside. Logged first: the new write is the latest
            await ctx.engine.db.flows.log_sync(dest_id, REMOVED, "flow_sync", None, source_relative_path=transfer.relative_path,
                                               written_path=str(older.get("path") or "") or None, outcome="removed")
            await ctx.engine.audit.record(ctx, "flow.replaced", target_type="flow_destinations", target_id=dest_id,
                                          detail={"flow_id": flow["id"], "relative_path": transfer.relative_path, "moved_to": older.get("moved_to")})
        elif older:
            await ctx.engine.audit.record(ctx, "flow.kept", target_type="flow_destinations", target_id=dest_id,
                                          detail={"flow_id": flow["id"], "relative_path": transfer.relative_path, "path": older.get("path"),
                                                  "why": "changed after the flow wrote it, so it stays beside the new version"})
            await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.conflict",
                                             {"flow_id": flow["id"], "destination_id": dest_id, "kept": str(older.get("path") or ""), "relative_path": transfer.relative_path,
                                              "why": "a newer version has a new name, but this copy was changed here: kept"})
        await ctx.engine.db.flows.log_sync(dest_id, written, "flow_sync", None,
                                           source_relative_path=transfer.relative_path,
                                           written_path=payload.get("written_path"), source_hash=transfer.hash,
                                           outcome=outcome, bytes_before=before, bytes_after=after)
        await ctx.engine.audit.record(ctx, "flow.synced", target_type="flow_destinations", target_id=dest_id,
                                      detail={"flow_id": flow["id"], "relative_path": transfer.relative_path})
        if payload.get("preserved"):
            # the flow was about to write over a file it had not written: the Worker kept that file beside the new one
            await ctx.engine.db.flows.log_sync(dest_id, "", "external", None, conflict_resolved=True,
                                               source_relative_path=transfer.relative_path, written_path=str(payload["preserved"]),
                                               outcome="kept_beside", bytes_before=before)
            await ctx.engine.audit.record(ctx, "flow.conflict", target_type="flow_destinations", target_id=dest_id,
                                          detail={"flow_id": flow["id"], "kept": str(payload["preserved"]), "why": "a file the flow did not write was there"})
            note = {"flow_id": flow["id"], "destination_id": dest_id, "kept": str(payload["preserved"]), "relative_path": transfer.relative_path}
            await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.conflict", note)
            await ctx.engine.push_to_account(dest["owner_account_id"], "flow.conflict", note)
        await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.synced",
                                         {"flow_id": flow["id"], "destination_id": dest_id,
                                          "relative_path": transfer.relative_path})
        await ctx.engine.announce("flow.synced", {"flow_id": flow["id"], "destination_id": dest_id, "relative_path": transfer.relative_path, "pc_id": ident.pc_id}, source="system", pc=ident.pc_id)
    elif status == "failed":
        failure = payload.get("failure") or {}
        reason = f"{failure.get('stage_type', 'destination')}:{failure.get('kind', 'unknown')}"
        await _fail_destination(ctx.engine, flow, dest, reason)
    transfer.pending_destinations.discard(dest_id)
    if not transfer.pending_destinations:
        _transfers.pop(transfer.id, None)
    return {"recorded": True}


@handler("flow.trigger")
async def trigger(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Manual sync of one file for a flow (sync_mode='manual' or after a fix).
    {"flow_id", "relative_path"}"""
    ident = require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    rel = str_field(payload, "relative_path")
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow")
    if flow["created_by_account_id"] != ident.account_id and not org_wide(ident):
        raise ProtocolError(ErrorCode.FORBIDDEN, "not your flow")
    if flow["status"] != "active":
        raise ProtocolError(ErrorCode.CONFLICT, f"flow is {flow['status']}")
    tid = await propagate(ctx.engine, flow_id, source_file(flow, rel), rel, None)
    return {"transfer_id": tid}


# --- transfers that never finished ----------------------------------------------------------------

async def expire_transfers(engine: Engine) -> None:
    """A transfer nobody finished (the source never answered, a destination went away mid-file) is failed rather than kept forever."""
    now = time.monotonic()
    for tid, transfer in list(_transfers.items()):
        if now - transfer.created < TRANSFER_SECONDS:
            continue
        _transfers.pop(tid, None)
        flow = await engine.db.flows.get(transfer.flow_id)
        if flow is None:
            continue
        reason = "source:unreadable" if transfer.data is None and transfer.content_b64 is None else "destination:unreachable"
        for dest in flow["destinations"]:
            if dest["id"] in transfer.pending_destinations:
                if transfer.bundles.get(dest["id"]):
                    await _bundle_step(engine, transfer, dest["id"], failed=reason)
                else:
                    await _fail_destination(engine, flow, dest, reason)
    for bid, b in list(_closing.items()):                   # told to make the bundle, and never said it did
        if now - b.created >= 2 * TRANSFER_SECONDS:
            _closing.pop(bid, None)
    for lid, found in list(_listings.items()):
        if now - found.created >= TRANSFER_SECONDS:
            _listings.pop(lid, None)


# --- catching a destination up -------------------------------------------------------------------

async def catch_up(engine: Engine, flow_id: int, only: set[int] | None = None, *, why: str = "heal") -> bool:
    """Ask the source machine what it holds now, then send the destinations what they are missing. False when it cannot be asked, or when the
    flow does not run for this reason (`why`: heal, hourly, run; see CATCH_UP_FOR)."""
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] != "active" or flow["consent_status"] == "pending":
        return False
    if why not in CATCH_UP_FOR.get(flow.get("run_mode") or "realtime", {"heal"}):
        return False
    if flow["source_pc_id"] not in engine.online_pc_ids():
        return False
    if flow.get("source_kind") == "file":
        return await _catch_up_file(engine, flow, only)
    request_id = uuid.uuid4().hex
    _listings[request_id] = Listing(flow_id, only)
    await engine.push_to_pc(flow["source_pc_id"], "flow.list", {"request_id": request_id, "flow_id": flow_id, "path": flow["source_path"]})
    return True


async def _catch_up_file(engine: Engine, flow: dict[str, Any], only: set[int] | None) -> bool:
    """A single-file flow needs no listing: the index says what the file is now, and each destination not last given that version is sent it."""
    name = _rsplit_sep(str(flow["source_path"]))[2]
    entry = next((f for f in await engine.db.file_index.by_name(name, pc_ids=[flow["source_pc_id"]])
                  if _same_path(f["path"], flow["source_path"])), None)
    if entry is None:
        return True                                  # the index has not seen the file yet: its first change will send it
    digest = entry.get("content_hash")
    targets = [d for d in flow["destinations"] if not d.get("paused_reason") and d["destination_path"] and (only is None or d["id"] in only)]
    need = set()
    for d in targets:
        given = await engine.db.flows.synced_source_hashes(d["id"])
        if digest is None or given.get(name.lower()) != digest:
            need.add(d["id"])
    if need:
        await propagate(engine, flow["id"], str(flow["source_path"]), name, digest, only=need)
    return True


async def heal(engine: Engine) -> None:
    """Proactive: now and then every running flow is looked at again, whether or not anything seemed to go wrong. Each destination is sent only what
    it does not already hold, so when nothing was missed this costs a listing and no transfers; when an event was missed it is made good."""
    if not engine.db.connected:
        return
    flows = engine.heat.hottest(await engine.db.flows.list_all(), key=lambda f: f"pc:{f['source_pc_id']}")
    for flow in flows:
        if flow["status"] == "active" and flow["consent_status"] != "pending":
            await catch_up(engine, flow["id"])


def catch_up_later(engine: Engine, flow_id: int, only: set[int] | None = None) -> None:
    _spawn(catch_up(engine, flow_id, only))


async def hourly(engine: Engine) -> None:
    """Flows set to copy every hour: each is listed and its destinations are sent what changed since. One whose source is away waits for the next hour."""
    if not engine.db.connected:
        return
    for flow in await engine.db.flows.by_run_mode("hourly"):
        if await catch_up(engine, flow["id"], why="hourly"):
            await engine.db.flows.mark_run(flow["merged_into"] or flow["id"])


@handler("flow.listing")
async def listing(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Source PC answers flow.list, in batches: {"request_id", "entries": [{"relative_path", "hash"?}], "done": bool}."""
    ident = require_account(ctx)
    found = _listings.get(str_field(payload, "request_id"))
    flow = await ctx.engine.db.flows.get(found.flow_id) if found else None
    if found is None or flow is None or flow["source_pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such listing for this pc")
    for e in (payload.get("entries") or [])[:MAX_LISTING_BATCH]:
        rel = str(e.get("relative_path") or "")
        if rel and len(found.entries) < MAX_LISTING:
            found.entries.append({"relative_path": rel, "hash": e.get("hash")})
        elif rel:
            found.truncated = True                                   # more than one catch-up will take on: the next healing pass continues where this left off
    if payload.get("done"):
        _listings.pop(str(payload["request_id"]), None)
        _spawn(_reconcile(ctx.engine, found))
    return {"accepted": True}


async def _reconcile(engine: Engine, found: Listing) -> None:
    """Send each destination the files whose source version it was not last given."""
    flow = await engine.db.flows.get(found.flow_id)
    if flow is None or flow["status"] != "active":
        return
    targets = [d for d in flow["destinations"] if not d.get("paused_reason") and (found.only is None or d["id"] in found.only)]
    if not targets:
        return
    given = {d["id"]: await engine.db.flows.synced_source_hashes(d["id"]) for d in targets}
    bundled = [d for d in targets if bundling(flow, d) is not None]
    if bundled:
        await start_bundles(engine, flow, found.entries, bundled, given)
        targets = [d for d in targets if d not in bundled]              # a bundle is the whole folder at each run, not files one by one
        if not targets:
            return
    await _mirror_deletes(engine, flow, found, targets, given)
    sent = 0
    ordered = engine.heat.hottest(found.entries, key=lambda e: f"file:{flow['source_pc_id']}:{join_client_path(flow['source_path'], e['relative_path'])}")
    for entry in ordered:
        rel, digest = entry["relative_path"], entry["hash"]
        key = rel.replace("\\", "/").lower()
        need = {d["id"] for d in targets if digest is None or given[d["id"]].get(key) != digest}
        if not need:
            continue
        while sum(1 for t in _transfers.values() if t.flow_id == flow["id"]) >= IN_FLIGHT:
            await asyncio.sleep(0.05)
            if (await engine.db.flows.get(flow["id"]) or {}).get("status") != "active":
                return
        await propagate(engine, flow["id"], source_file(flow, rel), rel, digest, only=need)
        sent += 1
    if sent:
        await engine.audit.record(None, "flow.caught_up", target_type="flows", target_id=flow["id"],
                                  detail={"files": sent, "destinations": [d["id"] for d in targets]})


async def _mirror_deletes(engine: Engine, flow: dict[str, Any], found: Listing, targets: list[dict[str, Any]], given: dict[int, dict[str, Any]]) -> None:
    """A mirroring flow also catches up on deletions it missed: what a destination was given from the source but the source no longer holds.
    Never from an empty listing (a source folder that cannot be read looks exactly like one emptied on purpose)."""
    if flow.get("on_source_delete") != "mirror":
        return
    present = {e["relative_path"].replace("\\", "/").lower() for e in found.entries}
    for d in targets:
        gone = [rel for rel, digest in given[d["id"]].items() if digest is not None and rel not in present]
        if not gone:
            continue
        if not present:
            await engine.audit.record(None, "flow.mirror_held", target_type="flows", target_id=flow["id"],
                                      detail={"why": "the source listing was empty; nothing was removed", "files": len(gone)})
            return
        for rel in gone:
            await remove_at_destinations(engine, flow["id"], rel, only={d["id"]})


async def on_pc_online(engine: Engine, pc_id: int) -> None:
    """A machine connected: any destination that was paused only because it could not be reached is resumed and caught up."""
    if not engine.db.connected:
        return
    by_flow: dict[int, set[int]] = {}
    for dest in await engine.db.flows.paused_unreachable_for_pc(pc_id):
        await engine.db.flows.set_destination_pause(dest["id"], None)
        by_flow.setdefault(dest["flow_id"], set()).add(dest["id"])
        await engine.audit.record(None, "flow.resumed", target_type="flow_destinations", target_id=dest["id"],
                                  detail={"flow_id": dest["flow_id"], "why": "the machine is back"})
    for flow_id, ids in by_flow.items():
        catch_up_later(engine, flow_id, ids)
