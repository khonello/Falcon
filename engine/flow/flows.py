"""Flow definition and management (Flow -> Core Components, Failure Handling, Creation).

Before a flow (or an edit to its destinations/stages) is accepted, three checks run against
the same Global File Index / flow graph, and the creator hears about every issue rather than
having it resolved for them:
  * Destination Consent -- implicit only when the creator already has authority over the
    destination's owner (Super User over anyone; an Admin over Workers in their own
    department). Lateral or upward destinations need the owner's explicit consent: the flow
    is stored paused with `consent_status='pending'` until they answer.
  * Pre-Flight Collision Check -- existing indexed content under a destination path is
    surfaced; the creator changes the path or confirms the collision is intentional.
  * Cycle Prevention -- a destination that (transitively) feeds back into the source, or a
    destination inside its own source directory, is refused.

Resource folders are never a direct source/destination -- Flow moves resource files under the
hood within the same access tiers (Resource -> Security Isolation).

Failure handling: a failed sync pauses only the affected destination (`paused_reason`), the
status persists until resolved, and a predefined suggestion for that (stage, failure) pair is
returned reactively. `flow.resume` clears it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, outranks, require_account, require_role, str_field
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

STAGE_TYPES = ("branch", "transformation", "categorization")
STATUSES = ("active", "paused", "inactive")

# Predefined, reactive fix suggestions per (stage type, failure kind) -- built-in knowledge,
# never configured upfront. Keys match what worker clients report in flow.sync_result.
FAILURE_SUGGESTIONS: dict[tuple[str, str], str] = {
    ("transformation", "convert_failed"): "Remove or reconfigure the Transformation stage for this destination.",
    ("transformation", "unsupported_format"): "This file type cannot be converted; add a Categorization stage to "
                                              "route it around the Transformation, or remove the stage.",
    ("categorization", "place_failed"): "Add a fallback category or relax the categorization rule.",
    ("destination", "unreachable"): "Check the destination PC's connection, then resume the flow.",
    ("destination", "permission_denied"): "Grant write access at the destination path, then resume.",
    ("destination", "unsupported"): "Remote-storage destinations are not supported in v1; change the destination.",
    ("source", "unreadable"): "The source file could not be read; check it is not locked, then resume.",
    ("consent", "denied"): "The destination owner declined; choose another destination.",
}


def suggestion_for(reason: str | None) -> str | None:
    if not reason or ":" not in reason:
        return None
    stage, kind = reason.split(":", 1)
    return FAILURE_SUGGESTIONS.get((stage, kind))


# --- path helpers -------------------------------------------------------------------------------

def norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def overlaps(a: str, b: str) -> bool:
    """Same directory, or one inside the other."""
    a, b = norm(a), norm(b)
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def is_resource_path(path: str) -> bool:
    return "/resources/" in norm(path) + "/" or norm(path).endswith("/resources")


def node(pc_id: int | None, path: str) -> tuple[str, str]:
    return (str(pc_id) if pc_id is not None else "remote", path)


def has_cycle(edges: list[tuple[str, str]], new_edges: list[tuple[str, str]]) -> bool:
    """Would adding `new_edges` create a loop? Nodes are 'pc:path' strings; two nodes on the
    same PC are treated as connected if their paths overlap (a sync into a sub-folder of a
    source directory is a loop too)."""

    def parse(n: str) -> tuple[str, str]:
        pc, _, path = n.partition(":")
        return pc, path

    def same(x: str, y: str) -> bool:
        (px, ax), (py, ay) = parse(x), parse(y)
        return px == py and overlaps(ax, ay)

    all_edges = [*edges, *new_edges]
    for src, dst in new_edges:
        if same(src, dst):
            return True
        # DFS from dst; reach anything overlapping src -> cycle.
        seen: list[str] = []
        stack = [dst]
        while stack:
            cur = stack.pop()
            if any(same(cur, s) for s in seen):
                continue
            seen.append(cur)
            for a, b in all_edges:
                if same(a, cur):
                    if same(b, src):
                        return True
                    stack.append(b)
    return False


def stage_chain(flow: dict[str, Any], destination: dict[str, Any]) -> list[dict[str, Any]]:
    """Ordered processing stages that apply to one destination: walk parent links from the
    destination back to the source, drop Branch stages (structural only)."""
    by_id = {s["id"]: s for s in flow["stages"]}
    chain: list[dict[str, Any]] = []
    cur = destination.get("parent_stage_id")
    while cur is not None and cur in by_id:
        st = by_id[cur]
        if st["stage_type"] != "branch":
            chain.append({"stage_type": st["stage_type"], "config": st.get("config") or {}})
        cur = st.get("parent_stage_id")
    chain.reverse()
    return chain


# --- creation checks ----------------------------------------------------------------------------

def _parse_structure(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stages_in = payload.get("stages") or []
    dests_in = payload.get("destinations")
    if not isinstance(stages_in, list) or not isinstance(dests_in, list) or not dests_in:
        raise ProtocolError(ErrorCode.INVALID, "destinations (non-empty list) and stages (list) required")
    stages: list[dict[str, Any]] = []
    for i, st in enumerate(stages_in):
        stype = st.get("stage_type")
        if stype not in STAGE_TYPES:
            raise ProtocolError(ErrorCode.INVALID, f"stage {i}: stage_type must be one of {', '.join(STAGE_TYPES)}")
        parent = st.get("parent_index")
        if parent is not None and not (0 <= int(parent) < i):
            raise ProtocolError(ErrorCode.INVALID, f"stage {i}: parent_index must reference an earlier stage")
        stages.append({"stage_type": stype, "parent_index": parent, "config": st.get("config")})
    dests: list[dict[str, Any]] = []
    for i, d in enumerate(dests_in):
        path = str(d.get("destination_path") or d.get("path") or "").strip()
        if not path:
            raise ProtocolError(ErrorCode.INVALID, f"destination {i}: destination_path required")
        parent = d.get("parent_index")
        if parent is not None and not (0 <= int(parent) < len(stages)):
            raise ProtocolError(ErrorCode.INVALID, f"destination {i}: parent_index must reference a stage")
        pc = d.get("destination_pc_id")
        dests.append({"destination_pc_id": int(pc) if pc is not None else None, "destination_path": path,
                      "parent_index": parent})
    return dests, stages


async def _resolve_owners(engine: Engine, dests: list[dict[str, Any]], creator: dict[str, Any]) -> None:
    for d in dests:
        if d["destination_pc_id"] is None:
            d["owner_account_id"] = creator["id"]          # remote storage: the creator's own space
            d["owner_role"] = creator["role"]
            d["owner_department_id"] = creator["department_id"]
            continue
        pc = await engine.db.accounts.pc(d["destination_pc_id"])
        if pc is None:
            raise ProtocolError(ErrorCode.NOT_FOUND, f"no such destination pc {d['destination_pc_id']}")
        if pc["bound_account_id"] is None:
            raise ProtocolError(ErrorCode.INVALID, f"destination pc {pc['hostname']} has no bound account")
        d["owner_account_id"] = pc["bound_account_id"]
        d["owner_role"] = pc["bound_role"]
        d["owner_department_id"] = pc["department_id"]


def consent_required(creator: dict[str, Any], owner_role: str, owner_department_id: int | None,
                     owner_account_id: int) -> bool:
    """The general rule: consent unless the creator already outranks the destination owner
    within their authority. One's own space never needs consent."""
    if owner_account_id == creator["id"]:
        return False
    if creator["role"] == "super_user":
        return False
    if creator["role"] == "admin":
        return not (outranks("admin", owner_role) and owner_department_id == creator["department_id"])
    return True  # a worker never has authority over anyone else's space


async def run_checks(engine: Engine, creator: dict[str, Any], source_pc_id: int, source_path: str,
                     dests: list[dict[str, Any]], *, confirm_collisions: bool,
                     exclude_flow_id: int | None = None) -> dict[str, Any]:
    """Consent / collision / cycle. Raises for hard refusals; returns what needs consent."""
    if is_resource_path(source_path) or any(is_resource_path(d["destination_path"]) for d in dests):
        raise ProtocolError(ErrorCode.INVALID, "Resource folders cannot be a direct flow source or destination")
    for d in dests:
        if d["destination_pc_id"] == source_pc_id and overlaps(d["destination_path"], source_path):
            raise ProtocolError(ErrorCode.CONFLICT, "destination overlaps its own source -- that is a cycle")

    edges = await engine.db.flows.graph_edges()
    if exclude_flow_id is not None:
        own = await engine.db.flows.get(exclude_flow_id)
        if own:
            mine = {(f"{own['source_pc_id']}:{own['source_path']}",
                     f"{d['destination_pc_id'] if d['destination_pc_id'] is not None else 'remote'}:{d['destination_path']}")
                    for d in own["destinations"]}
            edges = [e for e in edges if e not in mine]
    new_edges = [(f"{source_pc_id}:{source_path}",
                  f"{d['destination_pc_id'] if d['destination_pc_id'] is not None else 'remote'}:{d['destination_path']}")
                 for d in dests]
    if has_cycle(edges, new_edges):
        raise ProtocolError(ErrorCode.CONFLICT, "this flow would create a cycle in the flow graph")

    collisions = []
    for i, d in enumerate(dests):
        if d["destination_pc_id"] is None:
            continue
        existing = await engine.db.file_index.under_path(d["destination_pc_id"], d["destination_path"])
        if existing:
            collisions.append({"destination_index": i, "destination_path": d["destination_path"],
                               "existing": [e["path"] for e in existing]})
    if collisions and not confirm_collisions:
        raise ProtocolError(ErrorCode.CONFLICT, "destination path collides with existing content: "
                            + "; ".join(f"{c['destination_path']} ({len(c['existing'])} files)" for c in collisions)
                            + " -- change the path or pass confirm_collisions=true")
    needs_consent = [d for d in dests if consent_required(creator, d["owner_role"], d["owner_department_id"],
                                                         d["owner_account_id"])]
    return {"collisions": collisions, "needs_consent": needs_consent}


# --- handlers -----------------------------------------------------------------------------------

async def _flow_view(engine: Engine, flow: dict[str, Any]) -> dict[str, Any]:
    view = row(flow) or {}
    view["suggestion"] = suggestion_for(flow.get("pause_reason"))
    for d in view.get("destinations", []):
        d["suggestion"] = suggestion_for(d.get("paused_reason"))
        last = await engine.db.flows.last_sync(d["id"])
        d["last_sync"] = row(last)
    return view


async def _load_owned(ctx: Context, flow_id: int) -> dict[str, Any]:
    ident = ctx.identity
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow")
    if flow["created_by_account_id"] != ident.account_id and ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "not your flow")
    return flow


@handler("flow.create")
async def create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"source_pc_id", "source_path", "destinations": [{destination_pc_id?, destination_path,
    parent_index?}], "stages": [{stage_type, parent_index?, config?}], "confirm_collisions": bool}

    Super User: any source/destination. Admin: source on own PC or a Worker PC in their
    department. Consent, collision and cycle checks run before anything is stored."""
    ident = require_role(ctx, "super_user", "admin")
    creator = await ctx.engine.db.accounts.by_id(ident.account_id)
    assert creator is not None
    source_pc_id = int_field(payload, "source_pc_id")
    source_path = str_field(payload, "source_path")
    dests, stages = _parse_structure(payload)
    src = await ctx.engine.db.accounts.pc(source_pc_id)
    if src is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such source pc")
    if ident.role == "admin" and src["department_id"] != ident.department_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "source must be in your department")
    await _resolve_owners(ctx.engine, dests, creator)
    checks = await run_checks(ctx.engine, creator, source_pc_id, source_path, dests,
                              confirm_collisions=bool(payload.get("confirm_collisions")))
    pending = checks["needs_consent"]
    for d in dests:
        d["pre_flight_check_status"] = "passed"
    flow_id = await ctx.engine.db.flows.create(
        {"created_by_account_id": ident.account_id, "source_pc_id": source_pc_id, "source_path": source_path,
         "consent_status": "pending" if pending else "not_required"}, dests, stages)
    if pending:
        await ctx.engine.db.flows.set_status(flow_id, "paused", "consent:pending")
        names = await ctx.engine.db.accounts.display_names_for(pending[0]["owner_account_id"], [ident.account_id])
        for d in pending:
            await ctx.engine.push_to_account(d["owner_account_id"], "flow.consent_request",
                                             {"flow_id": flow_id, "destination_path": d["destination_path"],
                                              "creator_account_id": ident.account_id,
                                              "creator_name": names.get(ident.account_id)})
    await ctx.engine.audit.record(ctx, "flow.created", target_type="flows", target_id=flow_id,
                                  detail={"source_pc_id": source_pc_id, "destinations": len(dests),
                                          "consent_pending": [d["owner_account_id"] for d in pending],
                                          "collisions_confirmed": len(checks["collisions"])})
    flow = await ctx.engine.db.flows.get(flow_id)
    assert flow is not None
    return {"flow": await _flow_view(ctx.engine, flow), "consent_pending": bool(pending),
            "collisions_confirmed": checks["collisions"]}


@handler("flow.consent")
async def consent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Destination owner answers a consent request. {"flow_id", "granted": bool}"""
    ident = require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    granted = bool(payload.get("granted", False))
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None or flow["consent_status"] != "pending":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no flow awaiting your consent with that id")
    if ident.account_id not in {d["owner_account_id"] for d in flow["destinations"]}:
        raise ProtocolError(ErrorCode.FORBIDDEN, "you do not own a destination of this flow")
    db = ctx.engine.db
    if granted:
        await db.flows.set_consent(flow_id, "granted")
        await db.flows.set_status(flow_id, "active", None)
    else:
        await db.flows.set_status(flow_id, "inactive", "consent:denied")
    await ctx.engine.audit.record(ctx, "flow.consent", target_type="flows", target_id=flow_id,
                                  detail={"granted": granted})
    await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.consent_answered",
                                     {"flow_id": flow_id, "granted": granted, "by_account_id": ident.account_id})
    return {"flow_id": flow_id, "granted": granted}


@handler("flow.edit")
async def edit(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Replace destinations/stages; the same pre-flight checks run again. {"flow_id", ...}"""
    ident = require_role(ctx, "super_user", "admin")
    flow_id = int_field(payload, "flow_id")
    flow = await _load_owned(ctx, flow_id)
    creator = await ctx.engine.db.accounts.by_id(ident.account_id)
    assert creator is not None
    dests, stages = _parse_structure(payload)
    await _resolve_owners(ctx.engine, dests, creator)
    checks = await run_checks(ctx.engine, creator, flow["source_pc_id"], flow["source_path"], dests,
                              confirm_collisions=bool(payload.get("confirm_collisions")), exclude_flow_id=flow_id)
    if checks["needs_consent"]:
        raise ProtocolError(ErrorCode.FORBIDDEN, "new destinations outside your authority need a new flow "
                                                 "(consent is requested at creation)")
    await ctx.engine.db.flows.replace_structure(flow_id, dests, stages)
    await ctx.engine.audit.record(ctx, "flow.edited", target_type="flows", target_id=flow_id)
    updated = await ctx.engine.db.flows.get(flow_id)
    assert updated is not None
    return {"flow": await _flow_view(ctx.engine, updated)}


@handler("flow.pause")
async def pause(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    await _load_owned(ctx, flow_id)
    await ctx.engine.db.flows.set_status(flow_id, "paused", "manual")
    await ctx.engine.audit.record(ctx, "flow.paused", target_type="flows", target_id=flow_id)
    return {"flow_id": flow_id, "status": "paused"}


@handler("flow.resume")
async def resume(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Clears the flow-level pause and, with {"destination_id"}, a branch-level failure."""
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    flow = await _load_owned(ctx, flow_id)
    if flow["consent_status"] == "pending":
        raise ProtocolError(ErrorCode.CONFLICT, "still awaiting destination consent")
    dest_id = int_field(payload, "destination_id", required=False)
    if dest_id is not None:
        await ctx.engine.db.flows.set_destination_pause(dest_id, None)
    if flow["status"] == "paused":
        await ctx.engine.db.flows.set_status(flow_id, "active", None)
    await ctx.engine.audit.record(ctx, "flow.resumed", target_type="flows", target_id=flow_id,
                                  detail={"destination_id": dest_id})
    updated = await ctx.engine.db.flows.get(flow_id)
    assert updated is not None
    return {"flow": await _flow_view(ctx.engine, updated)}


@handler("flow.delete")
async def delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Status -> inactive; the row and its sync history are kept."""
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    await _load_owned(ctx, flow_id)
    await ctx.engine.db.flows.set_status(flow_id, "inactive", "deleted")
    await ctx.engine.audit.record(ctx, "flow.deleted", target_type="flows", target_id=flow_id)
    return {"flow_id": flow_id, "status": "inactive"}


@handler("flow.list")
async def list_flows(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    db = ctx.engine.db
    found = await db.flows.list_all() if ident.role == "super_user" else await db.flows.list_for(
        ident.account_id, department_id=ident.department_id)
    return {"flows": rows(found)}


@handler("flow.status")
async def status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Per-flow and per-destination status, incl. persistent failure state and suggestion.
    Visible to the creator, any destination owner, and Super User."""
    ident = require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow")
    owners = {d["owner_account_id"] for d in flow["destinations"]}
    if ident.role != "super_user" and ident.account_id != flow["created_by_account_id"] and ident.account_id not in owners:
        raise ProtocolError(ErrorCode.FORBIDDEN, "not a party to this flow")
    return {"flow": await _flow_view(ctx.engine, flow)}


@handler("flow.history")
async def history(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    await _load_owned(ctx, flow_id)
    return {"history": rows(await ctx.engine.db.flows.history(flow_id))}
