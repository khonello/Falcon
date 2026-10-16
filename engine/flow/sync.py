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
    parts: dict[int, bytes] = field(default_factory=dict)      # chunks arriving from the source
    data: bytes | None = None                                  # the whole file, once it has arrived
    created: float = field(default_factory=time.monotonic)


@dataclass
class Listing:
    flow_id: int
    only: set[int] | None
    entries: list[dict[str, Any]] = field(default_factory=list)
    created: float = field(default_factory=time.monotonic)


CHUNK_BYTES = 512 * 1024            # raw bytes per message (about 700 KB once encoded: far below the 4 MB a connection reads at a time)
MAX_RELAY_BYTES = 64 * 1024 * 1024
TRANSFER_SECONDS = 600.0            # a transfer nobody finished in this long is failed, not kept forever
IN_FLIGHT = 4                       # a catch-up sends this many files at a time, so thousands of files do not flood the Engine

_transfers: dict[str, Transfer] = {}
_listings: dict[str, Listing] = {}
_background: set[asyncio.Task[Any]] = set()
_settling: dict[tuple[int, str], asyncio.Task[Any]] = {}


def reset_state() -> None:
    _transfers.clear()
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
            await _settle_then_propagate(engine, src["id"], event["path"], rel, event.get("hash"))
    # Destination side: attribution check.
    for dest in await engine.db.flows.destinations_for_pc(pc_id):
        rel = relative_under(event["path"], dest["destination_path"])
        if rel is None or dest["flow_status"] != "active" or dest.get("paused_reason"):
            continue
        await _check_destination_write(engine, dest, event, rel)


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
        await propagate(engine, flow["id"], join_client_path(flow["source_path"], source_rel), source_rel, None,
                        only_destination=dest["id"])


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


async def propagate(engine: Engine, flow_id: int, source_file: str, relative_path: str, file_hash: str | None,
                    *, only_destination: int | None = None, only: set[int] | None = None) -> str | None:
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] != "active":
        return None
    wanted = only if only is not None else ({only_destination} if only_destination is not None else None)
    targets = [d for d in flow["destinations"] if not d.get("paused_reason") and (wanted is None or d["id"] in wanted)]
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
    online = engine.online_pc_ids()
    for dest in flow["destinations"]:
        if dest["id"] not in transfer.pending_destinations:
            continue
        if dest["destination_pc_id"] is None:
            await _fail_destination(engine, flow, dest, "destination:unsupported")
            transfer.pending_destinations.discard(dest["id"])
            continue
        if dest["destination_pc_id"] not in online:
            # not forgotten: paused as unreachable, and resumed and caught up when the machine returns
            await _fail_destination(engine, flow, dest, "destination:unreachable")
            transfer.pending_destinations.discard(dest["id"])
            continue
        base = {"transfer_id": transfer.id, "flow_id": flow["id"], "destination_id": dest["id"],
                "destination_path": dest["destination_path"], "relative_path": transfer.relative_path,
                "hash": transfer.hash, "stages": flowdefs.stage_chain(flow, dest),
                # what the flow itself last wrote there: anything else already at that place is someone's, and is kept, not overwritten
                "previous": await engine.db.flows.last_written_for(dest["id"], transfer.relative_path)}
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
        await ctx.engine.db.flows.log_sync(dest_id, written, "flow_sync", None,
                                           source_relative_path=transfer.relative_path,
                                           written_path=payload.get("written_path"), source_hash=transfer.hash)
        await ctx.engine.audit.record(ctx, "flow.synced", target_type="flow_destinations", target_id=dest_id,
                                      detail={"flow_id": flow["id"], "relative_path": transfer.relative_path})
        if payload.get("preserved"):
            # the flow was about to write over a file it had not written: the Worker kept that file beside the new one
            await ctx.engine.db.flows.log_sync(dest_id, "", "external", None, conflict_resolved=True,
                                               source_relative_path=transfer.relative_path, written_path=str(payload["preserved"]))
            await ctx.engine.audit.record(ctx, "flow.conflict", target_type="flow_destinations", target_id=dest_id,
                                          detail={"flow_id": flow["id"], "kept": str(payload["preserved"]), "why": "a file the flow did not write was there"})
            note = {"flow_id": flow["id"], "destination_id": dest_id, "kept": str(payload["preserved"]), "relative_path": transfer.relative_path}
            await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.conflict", note)
            await ctx.engine.push_to_account(dest["owner_account_id"], "flow.conflict", note)
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
                await _fail_destination(engine, flow, dest, reason)
    for lid, found in list(_listings.items()):
        if now - found.created >= TRANSFER_SECONDS:
            _listings.pop(lid, None)


# --- catching a destination up -------------------------------------------------------------------

async def catch_up(engine: Engine, flow_id: int, only: set[int] | None = None) -> bool:
    """Ask the source machine what it holds now, then send the destinations what they are missing. False when it cannot be asked."""
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] != "active" or flow["consent_status"] == "pending":
        return False
    if flow["source_pc_id"] not in engine.online_pc_ids():
        return False
    request_id = uuid.uuid4().hex
    _listings[request_id] = Listing(flow_id, only)
    await engine.push_to_pc(flow["source_pc_id"], "flow.list", {"request_id": request_id, "flow_id": flow_id, "path": flow["source_path"]})
    return True


async def heal(engine: Engine) -> None:
    """Proactive: now and then every running flow is looked at again, whether or not anything seemed to go wrong. Each destination is sent only what
    it does not already hold, so when nothing was missed this costs a listing and no transfers; when an event was missed it is made good."""
    if not engine.db.connected:
        return
    for flow in await engine.db.flows.list_all():
        if flow["status"] == "active" and flow["consent_status"] != "pending":
            await catch_up(engine, flow["id"])


def catch_up_later(engine: Engine, flow_id: int, only: set[int] | None = None) -> None:
    _spawn(catch_up(engine, flow_id, only))


@handler("flow.listing")
async def listing(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Source PC answers flow.list, in batches: {"request_id", "entries": [{"relative_path", "hash"?}], "done": bool}."""
    ident = require_account(ctx)
    found = _listings.get(str_field(payload, "request_id"))
    flow = await ctx.engine.db.flows.get(found.flow_id) if found else None
    if found is None or flow is None or flow["source_pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such listing for this pc")
    for e in payload.get("entries") or []:
        rel = str(e.get("relative_path") or "")
        if rel:
            found.entries.append({"relative_path": rel, "hash": e.get("hash")})
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
    sent = 0
    for entry in found.entries:
        rel, digest = entry["relative_path"], entry["hash"]
        key = rel.replace("\\", "/").lower()
        need = {d["id"] for d in targets if digest is None or given[d["id"]].get(key) != digest}
        if not need:
            continue
        while sum(1 for t in _transfers.values() if t.flow_id == flow["id"]) >= IN_FLIGHT:
            await asyncio.sleep(0.05)
            if (await engine.db.flows.get(flow["id"]) or {}).get("status") != "active":
                return
        await propagate(engine, flow["id"], join_client_path(flow["source_path"], rel), rel, digest, only=need)
        sent += 1
    if sent:
        await engine.audit.record(None, "flow.caught_up", target_type="flows", target_id=flow["id"],
                                  detail={"files": sent, "destinations": [d["id"] for d in targets]})


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
