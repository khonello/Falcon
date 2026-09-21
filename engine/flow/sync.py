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
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.flow import flows as flowdefs
from engine.hierarchy import reports
from engine.permissions import int_field, require_account, str_field
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


_transfers: dict[str, Transfer] = {}


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


def install(engine: Engine) -> None:
    engine.file_index.subscribe(lambda event: _on_file_event(engine, event))


# --- detection ----------------------------------------------------------------------------------

async def _on_file_event(engine: Engine, event: dict[str, Any]) -> None:
    if not engine.db.connected or event["op"] == "delete":
        return
    pc_id = event["pc_id"]
    # A file under an unresolved Resource violation is ignored by the system (Resource ->
    # Compliance): Flow never moves it.
    if event.get("file_index_id") in await engine.db.resource.ignored_file_ids(pc_id):
        return
    # Source side: does this event fall under an active flow's source directory?
    for src in await engine.db.flows.sources_for_pc(pc_id):
        rel = relative_under(event["path"], src["source_path"])
        if rel is not None:
            await propagate(engine, src["id"], event["path"], rel, event.get("hash"))
    # Destination side: attribution check.
    for dest in await engine.db.flows.destinations_for_pc(pc_id):
        rel = relative_under(event["path"], dest["destination_path"])
        if rel is None or dest["flow_status"] != "active" or dest.get("paused_reason"):
            continue
        await _check_destination_write(engine, dest, event, rel)


async def _check_destination_write(engine: Engine, dest: dict[str, Any], event: dict[str, Any], rel: str) -> None:
    last = await engine.db.flows.last_sync(dest["id"])
    if last is not None and last["written_by"] == "flow_sync" and last["content_hash"] == event.get("hash"):
        return  # our own write landing -- not a conflict
    if last is None:
        return  # nothing synced here yet; content predating the flow was handled at pre-flight
    # External modification: preserve it, then re-sync a fresh copy from source.
    await engine.db.flows.log_sync(dest["id"], event.get("hash") or "", "external", None, conflict_resolved=True)
    await engine.audit.record(None, "flow.conflict", target_type="flow_destinations", target_id=dest["id"],
                              detail={"path": event["path"], "hash": event.get("hash")})
    await engine.push_to_pc(dest["destination_pc_id"], "flow.resolve_conflict", {
        "flow_id": dest["flow_id"], "destination_id": dest["id"], "path": event["path"],
        "rename_to": modified_name(event["path"])})
    flow = await engine.db.flows.get(dest["flow_id"])
    if flow is not None:
        await propagate(engine, flow["id"], join_client_path(flow["source_path"], rel), rel, None,
                        only_destination=dest["id"])


# --- propagation --------------------------------------------------------------------------------

async def propagate(engine: Engine, flow_id: int, source_file: str, relative_path: str, file_hash: str | None,
                    *, only_destination: int | None = None) -> str | None:
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] != "active":
        return None
    targets = [d for d in flow["destinations"] if not d.get("paused_reason")
               and (only_destination is None or d["id"] == only_destination)]
    if not targets:
        return None
    transfer = Transfer(id=uuid.uuid4().hex, flow_id=flow_id, source_pc_id=flow["source_pc_id"],
                        source_path=source_file, relative_path=relative_path, hash=file_hash,
                        pending_destinations={d["id"] for d in targets})
    _transfers[transfer.id] = transfer
    await engine.push_to_pc(flow["source_pc_id"], "flow.read",
                            {"transfer_id": transfer.id, "flow_id": flow_id, "path": source_file})
    return transfer.id


async def _apply_to_destinations(engine: Engine, transfer: Transfer) -> None:
    flow = await engine.db.flows.get(transfer.flow_id)
    if flow is None:
        return
    for dest in flow["destinations"]:
        if dest["id"] not in transfer.pending_destinations:
            continue
        if dest["destination_pc_id"] is None:
            await _fail_destination(engine, flow, dest, "destination:unsupported")
            transfer.pending_destinations.discard(dest["id"])
            continue
        await engine.push_to_pc(dest["destination_pc_id"], "flow.apply", {
            "transfer_id": transfer.id, "flow_id": flow["id"], "destination_id": dest["id"],
            "destination_path": dest["destination_path"], "relative_path": transfer.relative_path,
            "hash": transfer.hash, "stages": flowdefs.stage_chain(flow, dest), "content_b64": transfer.content_b64})


async def _fail_destination(engine: Engine, flow: dict[str, Any], dest: dict[str, Any], reason: str) -> None:
    await engine.db.flows.set_destination_pause(dest["id"], reason)
    await engine.audit.record(None, "flow.failed", target_type="flow_destinations", target_id=dest["id"],
                              detail={"flow_id": flow["id"], "reason": reason})
    report_id = await reports.emit(engine, "flow_failure", source_table="flow_destinations", source_id=dest["id"],
                                   summary=f"flow #{flow['id']} -> {dest['destination_path']}: {reason}")
    payload = {"flow_id": flow["id"], "destination_id": dest["id"], "destination_path": dest["destination_path"],
               "reason": reason, "suggestion": flowdefs.suggestion_for(reason), "report_id": report_id}
    await engine.push_to_account(flow["created_by_account_id"], "flow.failed", payload)
    await engine.push_to_account(dest["owner_account_id"], "flow.failed", payload)


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
    transfer.content_b64 = str(payload.get("content_b64", ""))
    await _apply_to_destinations(ctx.engine, transfer)
    return {"accepted": True, "destinations": len(transfer.pending_destinations)}


@handler("flow.sync_result")
async def sync_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Destination PC reports the outcome of flow.apply:
    {"transfer_id", "destination_id", "status": "success"|"failed", "written_hash"?,
     "failure": {"stage_type": "transformation"|"categorization"|"destination", "kind": str}?}"""
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
    status = str_field(payload, "status", choices=("success", "failed"))
    if status == "success":
        written = payload.get("written_hash") or transfer.hash or ""
        await ctx.engine.db.flows.log_sync(dest_id, written, "flow_sync", None)
        await ctx.engine.audit.record(ctx, "flow.synced", target_type="flow_destinations", target_id=dest_id,
                                      detail={"flow_id": flow["id"], "relative_path": transfer.relative_path})
        await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.synced",
                                         {"flow_id": flow["id"], "destination_id": dest_id,
                                          "relative_path": transfer.relative_path})
    else:
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
    if flow["created_by_account_id"] != ident.account_id and ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "not your flow")
    if flow["status"] != "active":
        raise ProtocolError(ErrorCode.CONFLICT, f"flow is {flow['status']}")
    tid = await propagate(ctx.engine, flow_id, join_client_path(flow["source_path"], rel), rel, None)
    return {"transfer_id": tid}
