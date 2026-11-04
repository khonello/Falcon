"""Flow definition and management (Flow -> Core Components, Failure Handling, Creation).

Before a flow (or an edit to its destinations/stages) is accepted, three checks run against
the same Global File Index / flow graph, and the creator hears about every issue rather than
having it resolved for them:
  * Destination Consent -- implicit only when the creator already has authority over the
    destination's owner (the head of the organisation over anyone; an Admin over Workers in their own
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
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.flow import steps
from engine.permissions import (
    in_scope,
    int_field,
    org_wide,
    outranks,
    require_account,
    require_role,
    str_field,
)
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

STAGE_TYPES = steps.STAGE_TYPES
STATUSES = ("active", "paused", "inactive")

# Predefined, reactive fix suggestions per (stage type, failure kind) -- built-in knowledge,
# never configured upfront. Keys match what worker clients report in flow.sync_result.
FAILURE_SUGGESTIONS: dict[tuple[str, str], str] = {
    ("bundling", "bundle_failed"): "The bundle could not be made at the destination (no room, or a file in it could not be read); run the flow again.",
    ("destination", "unreachable"): "Check the destination PC's connection, then resume the flow.",
    ("destination", "permission_denied"): "Grant write access at the destination path, then resume.",
    ("destination", "unsupported"): "Remote-storage destinations are not supported in v1; change the destination.",
    ("source", "unreadable"): "The source file could not be read; check it is not locked, then resume.",
    ("consent", "denied"): "The destination owner declined; choose another destination.",
    ("destination", "restricted"): "That destination folder is now marked restricted. A flow never writes into a restricted folder: choose another destination.",
    ("source", "restricted"): "The source folder is now marked restricted. A flow never reads from a restricted folder: choose another source, or unmark it.",
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
    """The steps that apply to one destination, in the order they run (engine/flow/steps.py): walk parent links from the destination back
    to the source; a branch, and a placing step made before placing was dropped, mean nothing to a file and are left out."""
    by_id = {s["id"]: s for s in flow["stages"]}
    chain: list[dict[str, Any]] = []
    cur = destination.get("parent_stage_id")
    while cur is not None and cur in by_id:
        st = by_id[cur]
        meant = steps.normal(st)
        if meant is not None:
            chain.append(meant)
        cur = st.get("parent_stage_id")
    chain.reverse()
    return sorted(chain, key=lambda x: steps.RANK[x["stage_type"]])             # (stable: steps of one kind keep the order they were put in)


def _chains(stages: list[dict[str, Any]], dests: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Each destination's path through steps not stored yet (parent_index links), in the order they were given."""
    out = []
    for d in dests:
        chain, cur = [], d.get("parent_index")
        while cur is not None:
            st = stages[int(cur)]
            if st["stage_type"] != "branch":
                chain.append({"stage_type": st["stage_type"], "config": st["config"]})
            cur = st.get("parent_index")
        out.append(list(reversed(chain)))
    return out


def check_steps(stages: list[dict[str, Any]], dests: list[dict[str, Any]], *, run_mode: str, sources: int, source_kind: str) -> None:
    """Each destination's steps in the kinds' order; Bundling only where a run has a whole folder to bundle."""
    chains = _chains(stages, dests)
    for chain in chains:
        steps.check_path(chain)
    if steps.bundles(chains):
        if run_mode == "realtime":
            raise ProtocolError(ErrorCode.INVALID, "a Bundling step makes one file at each run: set the flow to run every hour, or only when you run it")
        if sources > 1 or source_kind != "folder":
            raise ProtocolError(ErrorCode.INVALID, "a Bundling step bundles one folder: not a single file, and not several sources")


# --- creation checks ----------------------------------------------------------------------------

def _parse_structure(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stages_in = payload.get("stages") or []
    dests_in = payload.get("destinations")
    if not isinstance(stages_in, list) or not isinstance(dests_in, list) or not dests_in:
        raise ProtocolError(ErrorCode.INVALID, "destinations (non-empty list) and stages (list) required")
    stages: list[dict[str, Any]] = []
    for i, st in enumerate(stages_in):
        if not isinstance(st, dict):
            raise ProtocolError(ErrorCode.INVALID, f"stage {i}: a step is an object")
        parent = st.get("parent_index")
        if parent is not None and not (0 <= int(parent) < i):
            raise ProtocolError(ErrorCode.INVALID, f"stage {i}: parent_index must reference an earlier stage")
        stype, config = steps.parse(st, i)
        stages.append({"stage_type": stype, "parent_index": parent, "config": config})
    dests: list[dict[str, Any]] = []
    for i, d in enumerate(dests_in):
        path = str(d.get("destination_path") or d.get("path") or "").strip()
        # Left empty, the destination chooses: another Admin picks the folder when they agree (checked once owners are known)
        if not path and not d.get("let_them_choose"):
            raise ProtocolError(ErrorCode.INVALID, f"destination {i}: destination_path required (or let_them_choose for another Admin's machine)")
        parent = d.get("parent_index")
        if parent is not None and not (0 <= int(parent) < len(stages)):
            raise ProtocolError(ErrorCode.INVALID, f"destination {i}: parent_index must reference a stage")
        pc = d.get("destination_pc_id")
        note = " ".join(str(d.get("note") or "").split())[:200] or None              # a line for whoever is asked to pick the folder
        dests.append({"destination_pc_id": int(pc) if pc is not None else None, "destination_path": path,
                      "parent_index": parent, "note": note})
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
    within their authority. One's own space never needs consent. Version 1 (Admins are IT): only a flow onto another Admin's machine
    needs consent, the destination Admin's; a Worker's machine needs none (docs/design/v1-it-admin.md)."""
    from engine import permissions

    if owner_account_id == creator["id"]:
        return False
    if permissions.ADMIN_SCOPE == "organisation":
        return owner_role == "admin"
    if creator["role"] == "super_user":
        return False
    if creator["role"] == "admin":
        return not (outranks("admin", owner_role) and owner_department_id == creator["department_id"])
    return True  # a worker never has authority over anyone else's space


async def run_checks(engine: Engine, creator: dict[str, Any], source_pc_id: int, source_path: str,
                     dests: list[dict[str, Any]], *, confirm_collisions: bool,
                     exclude_flow_id: int | None = None) -> dict[str, Any]:
    """Consent / collision / cycle. Raises for hard refusals; returns what needs consent."""
    for i, d in enumerate(dests):
        if not d["destination_path"] and not consent_required(creator, d["owner_role"], d["owner_department_id"], d["owner_account_id"]):
            raise ProtocolError(ErrorCode.INVALID, f"destination {i}: only another Admin chooses their own folder; name the folder for this machine")
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
        if d["destination_pc_id"] is None or not d["destination_path"]:
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

RUN_MODES = ("realtime", "hourly", "manual")
NAME_MAX = 80


def _name(payload: dict[str, Any]) -> str | None:
    """A flow's own name ("month-end"): one line, at most 80 characters. None when not given (it then reads as `<source folder>-<id>`)."""
    raw = payload.get("name")
    if raw is None:
        return None
    name = " ".join(str(raw).split())
    if not name or len(name) > NAME_MAX:
        raise ProtocolError(ErrorCode.INVALID, f"a flow's name is one line of 1 to {NAME_MAX} characters")
    return name


async def _sources(ctx: Context, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    """Where a new flow reads from: one source ({source_pc_id, source_path, source_kind?}), several merged into one flow ({"sources": [...]}), or
    the destination of a flow it carries on from ({"from_flow": {flow_id, destination_id}}). -> ([{source_pc_id, source_path, source_kind}], source_flow_id)."""
    db = ctx.engine.db
    if payload.get("from_flow") is not None:
        ref = payload["from_flow"]
        if not isinstance(ref, dict):
            raise ProtocolError(ErrorCode.INVALID, "from_flow is {flow_id, destination_id}")
        before = await db.flows.get(int_field(ref, "flow_id"))
        if before is None or before["status"] == "inactive":
            raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow to carry on from")
        dest = next((d for d in before["destinations"] if d["id"] == int_field(ref, "destination_id")), None)
        if dest is None or dest["destination_pc_id"] is None or not dest["destination_path"]:
            raise ProtocolError(ErrorCode.INVALID, "carry on from one of that flow's destinations, on a machine, with its folder chosen")
        return [{"source_pc_id": dest["destination_pc_id"], "source_path": dest["destination_path"], "source_kind": "folder"}], before["id"]
    given = payload.get("sources")
    if given is None:
        given = [{"source_pc_id": payload.get("source_pc_id"), "source_path": payload.get("source_path"), "source_kind": payload.get("source_kind")}]
    if not isinstance(given, list) or not given or len(given) > 10:
        raise ProtocolError(ErrorCode.INVALID, "sources is a list of 1 to 10 {source_pc_id, source_path, source_kind?}")
    out: list[dict[str, Any]] = []
    for s in given:
        if not isinstance(s, dict):
            raise ProtocolError(ErrorCode.INVALID, "each source is {source_pc_id, source_path, source_kind?}")
        src = {"source_pc_id": int_field(s, "source_pc_id"), "source_path": str_field(s, "source_path"),
               "source_kind": str_field(s, "source_kind", required=False, choices=("folder", "file")) or "folder"}
        if any(o["source_pc_id"] == src["source_pc_id"] and overlaps(o["source_path"], src["source_path"]) for o in out):
            raise ProtocolError(ErrorCode.INVALID, "two of the sources overlap: merge folders that are apart")
        out.append(src)
    return out, None


async def _group(engine: Engine, flow: dict[str, Any]) -> list[dict[str, Any]]:
    """The flow and the flows merged into it, as full flows (first one first)."""
    out = [flow]
    for r in (await engine.db.flows.group(flow["id"]))[1:]:
        full = await engine.db.flows.get(r["id"])
        if full is not None:
            out.append(full)
    return out


def _on_delete(payload: dict[str, Any]) -> str | None:
    """What happens at the destinations when a file is deleted at the source: "keep" (the default) or "mirror". None when not given."""
    if payload.get("on_source_delete") is None:
        return None
    return str_field(payload, "on_source_delete", choices=("keep", "mirror"))


async def _flow_view(engine: Engine, flow: dict[str, Any]) -> dict[str, Any]:
    view = row(flow) or {}
    view["suggestion"] = suggestion_for(flow.get("pause_reason"))
    # machines by name, never by id
    names = await engine.db.flows.hostnames([flow["source_pc_id"]] + [d["destination_pc_id"] for d in flow.get("destinations", [])
                                                                       if d.get("destination_pc_id")])
    view["source_hostname"] = names.get(flow["source_pc_id"])
    group = await engine.db.flows.group(flow["id"])
    view["sources"] = [{"source_pc_id": g["source_pc_id"], "source_path": g["source_path"], "source_kind": g.get("source_kind"),
                        "source_hostname": g.get("source_hostname")} for g in group] or [
                      {"source_pc_id": flow["source_pc_id"], "source_path": flow["source_path"], "source_kind": flow.get("source_kind"),
                       "source_hostname": view["source_hostname"]}]
    view["files_copied"] = row((await engine.db.flows.copied_counts([flow["id"]]))[flow["id"]])
    tools = await engine.db.accounts.converters([d["destination_pc_id"] for d in view.get("destinations", []) if d.get("destination_pc_id")])
    for d in view.get("destinations", []):
        d["converter"] = tools.get(d.get("destination_pc_id"))           # what converts Office files there (word, libreoffice), or None
        d["destination_hostname"] = names.get(d.get("destination_pc_id")) if d.get("destination_pc_id") else None
        d["suggestion"] = suggestion_for(d.get("paused_reason"))
        last = await engine.db.flows.last_sync(d["id"])
        d["last_sync"] = row(last)
    return view


async def _load_owned(ctx: Context, flow_id: int) -> dict[str, Any]:
    ident = ctx.identity
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow")
    if flow["created_by_account_id"] != ident.account_id and not org_wide(ident):       # (version 1: every IT Admin's; the audit trail shows who)
        raise ProtocolError(ErrorCode.FORBIDDEN, "not your flow")
    return flow


@handler("flow.create")
async def create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"source_pc_id", "source_path", "destinations": [{destination_pc_id?, destination_path,
    parent_index?}], "stages": [{stage_type, parent_index?, config?}], "confirm_collisions": bool,
    "name"?, "run_mode"?: realtime|hourly|manual, "sources"?: [{source_pc_id, source_path, source_kind?}], "from_flow"?: {flow_id, destination_id}}

    Several sources merge into one flow: the first is the flow, each further one a flow of its own pointing at it (`merged_into`) with the same
    name, steps and destinations. A file of the same name from two sources is never overwritten: the one already there is kept beside it.

    the head of the organisation: any source/destination. Admin: source on own PC or a Worker PC in their
    department. Consent, collision and cycle checks run before anything is stored."""
    ident = require_role(ctx, "super_user", "admin")
    creator = await ctx.engine.db.accounts.by_id(ident.account_id)
    assert creator is not None
    srcs, source_flow_id = await _sources(ctx, payload)
    source_pc_id, source_path = srcs[0]["source_pc_id"], srcs[0]["source_path"]
    name = _name(payload)
    run_mode = str_field(payload, "run_mode", required=False, choices=RUN_MODES) or "realtime"
    dests, stages = _parse_structure(payload)
    check_steps(stages, dests, run_mode=run_mode, sources=len(srcs), source_kind=srcs[0]["source_kind"])
    on_delete = _on_delete(payload)
    src = None
    for s in srcs:
        pc = await ctx.engine.db.accounts.pc(s["source_pc_id"])
        if pc is None:
            raise ProtocolError(ErrorCode.NOT_FOUND, "no such source pc")
        if ident.role == "admin" and not in_scope(ident, pc["department_id"]):
            raise ProtocolError(ErrorCode.FORBIDDEN, "source must be in your department")
        src = src or pc
    assert src is not None
    await _resolve_owners(ctx.engine, dests, creator)
    checks = await run_checks(ctx.engine, creator, source_pc_id, source_path, dests,
                              confirm_collisions=bool(payload.get("confirm_collisions")))
    for s in srcs[1:]:                                   # each further source is checked against the same destinations: no cycle, no own folder
        await run_checks(ctx.engine, creator, s["source_pc_id"], s["source_path"], dests, confirm_collisions=True)
    pending = checks["needs_consent"]
    for d in dests:
        d["pre_flight_check_status"] = "passed"
    made: list[int] = []
    for s in srcs:
        made.append(await ctx.engine.db.flows.create(
            {"created_by_account_id": ident.account_id, "source_pc_id": s["source_pc_id"], "source_path": s["source_path"],
             "consent_status": "pending" if pending else "not_required", "on_source_delete": on_delete or "keep", "source_kind": s["source_kind"],
             "name": name, "run_mode": run_mode, "merged_into": made[0] if made else None, "source_flow_id": source_flow_id},
            [dict(d) for d in dests], stages))
    flow_id = made[0]
    if pending:
        for fid in made:
            await ctx.engine.db.flows.set_status(fid, "paused", "consent:pending")
        names = await ctx.engine.db.accounts.display_names_for(pending[0]["owner_account_id"], [ident.account_id])
        for d in pending:
            await ctx.engine.push_to_account(d["owner_account_id"], "flow.consent_request",
                                             {"flow_id": flow_id, "destination_path": d["destination_path"],
                                              "creator_account_id": ident.account_id,
                                              "creator_name": names.get(ident.account_id), "note": d.get("note")})
        from engine.console import issues

        first = pending[0]
        who = await ctx.engine.db.accounts.display_names_for(ident.account_id, [first["owner_account_id"]])
        dest_pc = await ctx.engine.db.accounts.pc(first["destination_pc_id"]) if first.get("destination_pc_id") else None
        src_pc = await ctx.engine.db.accounts.pc(source_pc_id)
        await issues.raise_issue(
            ctx.engine, type_="flow", severity="low", title="Flow waiting for a folder",
            subject=f"{src['hostname']} -> {who.get(first['owner_account_id'])}", pc_id=source_pc_id, source_table="flow_consent", source_id=flow_id,
            owner_account_id=first["owner_account_id"], state="waiting", label="Waiting",
            detail={"flow_id": flow_id, "from": f"{src_pc['hostname'] if src_pc else ''} {source_path}".strip(),
                    "to": f"{dest_pc['hostname'] if dest_pc else 'remote storage'} {first['destination_path']}",
                    "consent_by": who.get(first["owner_account_id"]), "consent_account_id": first["owner_account_id"],
                    "destination_pc_id": first.get("destination_pc_id"), "asked_at": datetime.now(timezone.utc).isoformat()})
    await ctx.engine.audit.record(ctx, "flow.created", target_type="flows", target_id=flow_id,
                                  detail={"source_pc_id": source_pc_id, "destinations": len(dests), "on_source_delete": on_delete or "keep",
                                          "name": name, "run_mode": run_mode, "merged": made[1:], "source_flow_id": source_flow_id,
                                          "consent_pending": [d["owner_account_id"] for d in pending],
                                          "collisions_confirmed": len(checks["collisions"])})
    # A flow does not carry anything restricted without the owner's consent: if either end already is restricted, the flow starts paused and the owner is asked.
    from engine.flow import guard

    held = False
    for fid, s in zip(made, srcs):
        ends = [(s["source_pc_id"], s["source_path"])] + [(d["destination_pc_id"], d["destination_path"]) for d in dests]
        for pc, path in ends:
            if not path:
                continue                                 # a folder the destination Admin has not chosen yet: checked when they choose
            missing = await guard.unconsented(ctx.engine, fid, pc, path)
            if missing:
                await guard.request(ctx.engine, fid, missing, path, step="when the flow was made")
                held = True
    await ctx.engine.announce("flow.created", {"flow_id": flow_id, "source_pc_id": source_pc_id, "held": held, "pending": bool(pending)}, pc=source_pc_id)
    flow = await ctx.engine.db.flows.get(flow_id)
    assert flow is not None
    if not pending and not held:
        from engine.flow import sync

        for fid in made:
            sync.catch_up_later(ctx.engine, fid)               # what is already in the source folder is sent too (when it runs on its own)
    return {"flow": await _flow_view(ctx.engine, flow), "consent_pending": bool(pending), "restricted_pending": held,
            "collisions_confirmed": checks["collisions"]}


@handler("flow.consent")
async def consent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Destination owner answers a consent request. {"flow_id", "granted": bool, "destination_path"?}: when the flow left the folder to them, the
    destination Admin names it as they agree (docs/design/v1-it-admin.md: the destination chooses)."""
    ident = require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    granted = bool(payload.get("granted", False))
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None or flow["consent_status"] != "pending":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no flow awaiting your consent with that id")
    if ident.account_id not in {d["owner_account_id"] for d in flow["destinations"]}:
        raise ProtocolError(ErrorCode.FORBIDDEN, "you do not own a destination of this flow")
    db = ctx.engine.db
    unchosen = [d for d in flow["destinations"] if d["owner_account_id"] == ident.account_id and not d["destination_path"]]
    if granted and unchosen:
        chosen = str(payload.get("destination_path") or "").strip()
        if not chosen:
            raise ProtocolError(ErrorCode.INVALID, "this flow leaves the folder to you: name it (destination_path) as you agree")
        if is_resource_path(chosen):
            raise ProtocolError(ErrorCode.INVALID, "Resource folders cannot be a direct flow destination")
        for d in unchosen:
            if d["destination_pc_id"] == flow["source_pc_id"] and overlaps(chosen, flow["source_path"]):
                raise ProtocolError(ErrorCode.CONFLICT, "that folder overlaps the flow's own source -- that is a cycle")
            edges = [e for e in await db.flows.graph_edges() if e[1] != f"{d['destination_pc_id']}:"]
            if has_cycle(edges, [(f"{flow['source_pc_id']}:{flow['source_path']}", f"{d['destination_pc_id']}:{chosen}")]):
                raise ProtocolError(ErrorCode.CONFLICT, "that folder would create a cycle in the flow graph")
            await db.flows.set_destination_path(d["id"], chosen)
    if granted:
        await db.flows.set_consent(flow_id, "granted")
        waiting = await db.flows.consents(flow_id, states=("asked",))
        if waiting:
            await db.flows.set_status(flow_id, "paused", "restricted:consent")          # the destination agreed, but something restricted is still waiting for its owner
        else:
            await db.flows.set_status(flow_id, "active", None)
    else:
        await db.flows.set_status(flow_id, "inactive", "consent:denied")
    await ctx.engine.audit.record(ctx, "flow.consent", target_type="flows", target_id=flow_id,
                                  detail={"granted": granted})
    from engine.console import issues

    await issues.resolve_source(ctx.engine, "flow_consent", flow_id, "Agreed" if granted else "Declined")
    await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.consent_answered",
                                     {"flow_id": flow_id, "granted": granted, "by_account_id": ident.account_id})
    from engine.flow import sync

    if granted and not await db.flows.consents(flow_id, states=("asked",)):
        sync.catch_up_later(ctx.engine, flow_id)
    for other in (await _group(ctx.engine, flow))[1:]:      # a merged source shares the destinations, so the same answer is theirs
        if other["consent_status"] != "pending":
            continue
        chosen = [d["destination_path"] for d in (await db.flows.get(flow_id) or {}).get("destinations", [])]
        for d, path in zip(other["destinations"], chosen):
            if not d["destination_path"] and path:
                await db.flows.set_destination_path(d["id"], path)
        if granted:
            await db.flows.set_consent(other["id"], "granted")
            if await db.flows.consents(other["id"], states=("asked",)):
                await db.flows.set_status(other["id"], "paused", "restricted:consent")
            else:
                await db.flows.set_status(other["id"], "active", None)
                sync.catch_up_later(ctx.engine, other["id"])
        else:
            await db.flows.set_status(other["id"], "inactive", "consent:denied")
    return {"flow_id": flow_id, "granted": granted}


async def _load_visible(ctx: Context, flow_id: int) -> dict[str, Any]:
    """A flow as a party to it sees it: its creator, a destination's owner, the head of the organisation, or somebody who may answer one of its requests."""
    from engine.flow import guard

    ident = ctx.identity
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow")
    owners = {d["owner_account_id"] for d in flow["destinations"]}
    asked = await ctx.engine.db.flows.consents(flow_id, states=("asked", "granted", "declined", "revoked"))
    if not org_wide(ident) and ident.account_id != flow["created_by_account_id"] and ident.account_id not in owners and not any(guard.can_decide(ident, c) for c in asked):
        raise ProtocolError(ErrorCode.FORBIDDEN, "not a party to this flow")
    return flow


@handler("flow.restricted")
async def restricted(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"flow_id"} -> {"consents": [...], "can_decide": [ids]}: what a flow is waiting to carry, what has been consented to, and which of them this caller may answer."""
    ident = require_account(ctx)
    flow = await _load_visible(ctx, int_field(payload, "flow_id"))
    found = await ctx.engine.db.flows.consents(flow["id"], states=("asked", "granted", "declined", "revoked"))
    from engine.flow import guard

    return {"consents": rows(found), "can_decide": [c["id"] for c in found if guard.can_decide(ident, c)]}


@handler("flow.restricted_waiting")
async def restricted_waiting(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Every request to carry something restricted that is waiting for THIS caller to answer, across all flows: {"waiting": [{id, flow_id, name, sample_path, asked_at, source_hostname, ...}]}.
    What the Overview shows as waiting on you."""
    from engine.flow import guard

    ident = require_role(ctx, "super_user", "admin")
    mine = [c for c in await ctx.engine.db.flows.asked_consents() if guard.can_decide(ident, c)]
    out = rows(mine)
    for c in out:
        full = await ctx.engine.db.flows.get(c["flow_id"])
        places = (await _flow_view(ctx.engine, full))["destinations"] if full else []
        c["what"] = str(c.get("sample_path") or "").replace("\\", "/").rsplit("/", 1)[-1] or None
        c["from"] = c.get("source_hostname")
        c["to"] = ", ".join(str(d.get("destination_hostname") or d.get("destination_path")) for d in places)
    return {"waiting": out}


@handler("flow.restricted_consent")
async def restricted_consent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The owner of a restriction answers a flow that wants to carry it. {"consent_id", "grant": bool, "days"?: int (0 or none = until taken back), "note"?}
    Granting makes the flow's destination folders a place the content may be, and lets the flow go on if nothing else is waiting. Declining leaves it paused."""
    from datetime import timedelta

    from engine.flow import guard

    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    consent = await db.flows.consent(int_field(payload, "consent_id"))
    if consent is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such request")
    flow = await db.flows.get(consent["flow_id"])
    if flow is None or consent["state"] != "asked":
        raise ProtocolError(ErrorCode.CONFLICT, "that request is not waiting for an answer")
    if not guard.can_decide(ident, consent):
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the person who made the restriction can allow a flow to carry it")
    grant = bool(payload.get("grant", False))
    days = int_field(payload, "days", required=False) or 0
    if days < 0 or days > 3650:
        raise ProtocolError(ErrorCode.INVALID, "days must be 0 (until taken back) to 3650")
    expires = datetime.now(timezone.utc) + timedelta(days=days) if days else None
    note = " ".join(str(payload.get("note") or "").split())[:300] or None
    await db.flows.decide_consent(consent["id"], "granted" if grant else "declined", ident.account_id, expires, note)
    allowed = 0
    if grant:
        for d in flow["destinations"]:
            if d.get("destination_pc_id") is not None:
                await db.resource.allow(d["destination_pc_id"], d["destination_path"], None, ident.account_id,
                                        f"flow #{flow['id']} carries it, by consent", consent.get("mark_id"), folder=True, consent_id=consent["id"])
                allowed += 1
    await ctx.engine.announce("flow.restricted_granted" if grant else "flow.restricted_declined", {"flow_id": flow["id"], "consent_id": consent["id"], "name": consent["name"]})
    await ctx.engine.audit.record(ctx, "flow.restricted_consented" if grant else "flow.restricted_declined", target_type="flows", target_id=flow["id"],
                                  detail={"consent_id": consent["id"], "name": consent["name"], "days": days, "places_allowed": allowed, "note": note})
    from engine.console import issues

    await issues.resolve_source(ctx.engine, "flow_restricted", consent["id"], "Allowed" if grant else "Declined", by=ctx)
    await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.restricted_answered", {"flow_id": flow["id"], "consent_id": consent["id"], "granted": grant, "name": consent["name"]})
    resumed = False
    if (grant and flow["status"] == "paused" and flow.get("pause_reason") == guard.PAUSE and flow["consent_status"] != "pending"
            and not await db.flows.consents(flow["id"], states=("asked",))):
        await db.flows.set_status(flow["id"], "active", None)
        resumed = True
        from engine.flow import sync

        sync.catch_up_later(ctx.engine, flow["id"])                    # what was held back is sent now
    return {"consent_id": consent["id"], "granted": grant, "flow_resumed": resumed}


@handler("flow.restricted_revoke")
async def restricted_revoke(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Take a consent back. {"consent_id"}: the flow stops at once, and the places it made allowed are not allowed any more (what is already there is then reported)."""
    from engine.flow import guard

    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    consent = await db.flows.consent(int_field(payload, "consent_id"))
    if consent is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such consent")
    if not guard.can_decide(ident, consent):
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the person who made the restriction can take this back")
    if not await db.flows.decide_consent(consent["id"], "revoked", ident.account_id, None, "taken back"):
        raise ProtocolError(ErrorCode.CONFLICT, "that consent is not in force")
    removed = await db.resource.revoke_allowances(consent["id"])
    flow = await db.flows.get(consent["flow_id"])
    if flow is not None and flow["status"] == "active":
        await db.flows.set_status(flow["id"], "paused", guard.PAUSE)
    await ctx.engine.audit.record(ctx, "flow.restricted_revoked", target_type="flows", target_id=consent["flow_id"], detail={"consent_id": consent["id"], "places_no_longer_allowed": removed})
    if flow is not None:
        await ctx.engine.push_to_account(flow["created_by_account_id"], "flow.restricted_answered", {"flow_id": flow["id"], "consent_id": consent["id"], "granted": False, "name": consent["name"]})
    return {"consent_id": consent["id"], "revoked": True}


@handler("flow.edit")
async def edit(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Replace destinations/stages; the same pre-flight checks run again. {"flow_id", ..., "name"?, "run_mode"?}. A flow with merged sources
    changes as one: every source gets the new steps and destinations."""
    ident = require_role(ctx, "super_user", "admin")
    flow_id = int_field(payload, "flow_id")
    flow = await _load_owned(ctx, flow_id)
    creator = await ctx.engine.db.accounts.by_id(ident.account_id)
    assert creator is not None
    dests, stages = _parse_structure(payload)
    mode_after = str_field(payload, "run_mode", required=False, choices=RUN_MODES) or flow.get("run_mode") or "realtime"
    group = await _group(ctx.engine, flow)
    check_steps(stages, dests, run_mode=mode_after, sources=len(group), source_kind=flow.get("source_kind") or "folder")
    await _resolve_owners(ctx.engine, dests, creator)
    checks = await run_checks(ctx.engine, creator, flow["source_pc_id"], flow["source_path"], dests,
                              confirm_collisions=bool(payload.get("confirm_collisions")), exclude_flow_id=flow_id)
    if checks["needs_consent"]:
        raise ProtocolError(ErrorCode.FORBIDDEN, "new destinations outside your authority need a new flow "
                                                 "(consent is requested at creation)")
    for other in group[1:]:
        await run_checks(ctx.engine, creator, other["source_pc_id"], other["source_path"], dests, confirm_collisions=True, exclude_flow_id=other["id"])
    for member in group:
        await ctx.engine.db.flows.replace_structure(member["id"], [dict(d) for d in dests], stages)
    if "name" in payload or "run_mode" in payload:
        name = _name(payload) if "name" in payload else flow.get("name")
        mode = str_field(payload, "run_mode", required=False, choices=RUN_MODES) or flow.get("run_mode") or "realtime"
        await ctx.engine.db.flows.set_name_and_mode(flow_id, name=name, run_mode=mode)
    from engine.flow import guard

    for d in dests:
        missing = await guard.unconsented(ctx.engine, flow_id, d["destination_pc_id"], d["destination_path"])
        if missing:
            await guard.request(ctx.engine, flow_id, missing, d["destination_path"], step="when the flow was edited")
    on_delete = _on_delete(payload)
    if on_delete and on_delete != flow.get("on_source_delete"):
        for member in group:
            await ctx.engine.db.flows.set_on_source_delete(member["id"], on_delete)
        await ctx.engine.audit.record(ctx, "flow.delete_rule_changed", target_type="flows", target_id=flow_id, detail={"on_source_delete": on_delete})
    await ctx.engine.audit.record(ctx, "flow.edited", target_type="flows", target_id=flow_id)
    updated = await ctx.engine.db.flows.get(flow_id)
    assert updated is not None
    return {"flow": await _flow_view(ctx.engine, updated)}


@handler("flow.remind")
async def remind(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"flow_id"} -- remind whoever must pick a folder for a waiting flow. Any Admin who may see the flow may."""
    flow = await _load_visible(ctx, int_field(payload, "flow_id"))
    if flow["consent_status"] != "pending":
        raise ProtocolError(ErrorCode.CONFLICT, "this flow is not waiting for anyone")
    told = sorted({d["owner_account_id"] for d in flow["destinations"] if d.get("owner_account_id") and d["owner_account_id"] != flow["created_by_account_id"]})
    for account_id in told:
        await ctx.engine.push_to_account(account_id, "flow.consent_request", {"flow_id": flow["id"], "from_account_id": ctx.identity.account_id, "reminder": True})
    await ctx.engine.audit.record(ctx, "flow.reminded", target_type="flows", target_id=flow["id"], detail={"told": told})
    return {"flow_id": flow["id"], "reminded": len(told)}


@handler("flow.keep")
async def keep(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"flow_id", "path", "keep": "new"|"both"} -- settle a file the flow kept beside a new version: put it aside and keep only the new one, or keep both."""
    flow = await _load_visible(ctx, int_field(payload, "flow_id"))
    path = str_field(payload, "path")
    choice = str_field(payload, "keep", choices=("new", "both"))
    found = await ctx.engine.db.flows.kept_beside(flow["id"], path)
    if found is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "the flow kept no such file")
    if choice == "new":
        if found["destination_pc_id"] not in ctx.engine.online_pc_ids():
            raise ProtocolError(ErrorCode.UNAVAILABLE, "that machine is not connected")
        await ctx.engine.push_to_pc(found["destination_pc_id"], "flow.remove", {
            "flow_id": flow["id"], "destination_id": found["destination_id"], "relative_path": found["source_relative_path"] or path, "path": found["written_path"],
            "root": found["destination_path"], "settled": True})
    await ctx.engine.audit.record(ctx, "flow.keep_settled", target_type="flows", target_id=flow["id"], detail={"path": path, "keep": choice})
    return {"flow_id": flow["id"], "keep": choice}


@handler("flow.start")
async def start(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"flow_id"} -- start a stopped flow again: it resumes, under the same checks, and catches up on what it missed."""
    flow_id = int_field(payload, "flow_id")
    flow = await _load_owned(ctx, flow_id)
    if flow["status"] == "active":
        raise ProtocolError(ErrorCode.CONFLICT, "this flow is already running")
    for member in await ctx.engine.db.flows.member_ids(flow_id):
        await ctx.engine.db.flows.set_status(member, "paused", "manual")
    return await resume(ctx, {"flow_id": flow_id})


@handler("flow.steps")
async def steps_catalogue(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The steps a flow can have, as the tree New flow draws: category > kind > operation > settings (engine/flow/steps.py), with each
    setting's choices and default, the order the kinds run in, and what an operation needs."""
    require_role(ctx, "super_user", "admin")
    return {"tree": steps.catalogue(), "order": list(steps.KINDS)}


@handler("flow.pause")
async def pause(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    for member in await _group(ctx.engine, await _load_owned(ctx, flow_id)):
        await ctx.engine.db.flows.set_status(member["id"], "paused", "manual")
    await ctx.engine.audit.record(ctx, "flow.paused", target_type="flows", target_id=flow_id)
    await ctx.engine.announce("flow.paused", {"flow_id": flow_id, "by": "person"})
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
    from engine.flow import guard

    # a flow paused for a restricted folder does not resume into it until its owner has said so: looked at again now, not trusted from when it was paused
    for pc, path in [(flow["source_pc_id"], flow["source_path"])] + [(d.get("destination_pc_id"), d["destination_path"]) for d in flow["destinations"]
                                                                       if dest_id is None or d["id"] == dest_id]:
        missing = await guard.unconsented(ctx.engine, flow_id, pc, path)
        if missing:
            await guard.request(ctx.engine, flow_id, missing, path, step="when it was asked to resume")
            raise ProtocolError(ErrorCode.CONFLICT, f"This flow would carry something restricted ({missing[0].reason}); it needs the consent of {guard.deciders_text(missing[0])}")
    if dest_id is not None:
        await ctx.engine.db.flows.set_destination_pause(dest_id, None)
    others = (await _group(ctx.engine, flow))[1:]
    if flow["status"] == "paused":
        await ctx.engine.db.flows.set_status(flow_id, "active", None)
        for other in others:
            if other["status"] == "paused" and other["pause_reason"] == flow["pause_reason"]:
                await ctx.engine.db.flows.set_status(other["id"], "active", None)
    await ctx.engine.audit.record(ctx, "flow.resumed", target_type="flows", target_id=flow_id,
                                  detail={"destination_id": dest_id})
    updated = await ctx.engine.db.flows.get(flow_id)
    assert updated is not None
    if updated["status"] == "active":
        from engine.flow import sync

        for fid in [flow_id] + [o["id"] for o in others]:
            sync.catch_up_later(ctx.engine, fid)               # what was missed while it was paused or failed is sent now
    return {"flow": await _flow_view(ctx.engine, updated)}


@handler("flow.run")
async def run_now(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"flow_id"} -- Run: copy now what changed, whatever the flow's run mode (the only way a flow set to "only when I run it" moves anything).
    Every source of a merged flow is run. Any Admin who may see the flow may run it; changing it stays its maker's."""
    flow = await _load_visible(ctx, int_field(payload, "flow_id"))
    if flow["status"] != "active" or flow["consent_status"] == "pending":
        raise ProtocolError(ErrorCode.CONFLICT, f"the flow is {flow['status'] if flow['status'] != 'active' else 'waiting for consent'}: it cannot run")
    from engine.flow import sync

    started = []
    for member in await _group(ctx.engine, flow):
        if await sync.catch_up(ctx.engine, member["id"], why="run"):
            started.append(member["id"])
    if not started:
        raise ProtocolError(ErrorCode.CONFLICT, "the source machine is not connected: run it again when it is")
    await ctx.engine.db.flows.mark_run(flow["id"])
    await ctx.engine.audit.record(ctx, "flow.run", target_type="flows", target_id=flow["id"], detail={"sources": started})
    return {"flow_id": flow["id"], "sources_started": len(started)}


@handler("flow.delete")
async def delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Status -> inactive; the row and its sync history are kept."""
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    for member in await _group(ctx.engine, await _load_owned(ctx, flow_id)):
        await ctx.engine.db.flows.set_status(member["id"], "inactive", "deleted")
    await ctx.engine.audit.record(ctx, "flow.deleted", target_type="flows", target_id=flow_id)
    from engine.console import issues

    await issues.resolve_source(ctx.engine, "flow_consent", flow_id, "The flow was removed")
    return {"flow_id": flow_id, "status": "inactive"}


@handler("flow.list")
async def list_flows(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    db = ctx.engine.db
    found = await db.flows.list_all() if org_wide(ident) else await db.flows.list_for(
        ident.account_id, department_id=ident.department_id)
    # each flow's stages and destinations, batched: the Flows page draws every flow at once
    found = [f for f in found if not f.get("merged_into")]          # a merged source is shown on its flow, not as a flow of its own
    ids = [f["id"] for f in found]
    shapes, merged, copied = await db.flows.shapes(ids), await db.flows.merged_sources(ids), await db.flows.copied_counts(ids)
    out = rows(found)
    for f in out:
        f["sources"] = [{"source_pc_id": f["source_pc_id"], "source_path": f["source_path"], "source_kind": f.get("source_kind"),
                         "source_hostname": f.get("source_hostname"), "pause_reason": f.get("pause_reason"), "paused_at": f.get("paused_at")}] + rows(merged.get(f["id"], []))
        f["files_copied"] = row(copied[f["id"]])
        f["stages"] = rows(shapes[f["id"]]["stages"])
        f["destinations"] = rows(shapes[f["id"]]["destinations"])
        for d in f["destinations"]:
            d["suggestion"] = suggestion_for(d.get("paused_reason"))
        f["suggestion"] = suggestion_for(f.get("pause_reason"))
    return {"flows": out}


@handler("flow.status")
async def status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Per-flow and per-destination status, incl. persistent failure state and suggestion.
    Visible to the creator, any destination owner, and the head of the organisation."""
    ident = require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    flow = await ctx.engine.db.flows.get(flow_id)
    if flow is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such flow")
    owners = {d["owner_account_id"] for d in flow["destinations"]}
    if not org_wide(ident) and ident.account_id != flow["created_by_account_id"] and ident.account_id not in owners:
        raise ProtocolError(ErrorCode.FORBIDDEN, "not a party to this flow")
    return {"flow": await _flow_view(ctx.engine, flow)}


@handler("flow.history")
async def history(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_account(ctx)
    flow_id = int_field(payload, "flow_id")
    await _load_owned(ctx, flow_id)
    return {"history": rows(await ctx.engine.db.flows.history(flow_id))}


RUN_GAP = timedelta(minutes=2)          # writes this close together are one run of the flow
RUNS_DAYS = 90                          # as far back as a flow's history is kept
RUNS_SHOWN = 20


@handler("flow.runs")
async def flow_runs(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """A flow's last sync, as a diff (ENGINE-GAPS #11). {"flow_id"} -> `last`: the latest run in full, each file with what happened to it at its
    destination (new, changed, or kept beside: a file the flow did not write, kept next to the new one) and its size there before and after;
    `waiting`: what the flow holds now (for an owner's consent, or for a destination that is away); `earlier`: the runs before it as counts and bytes.
    A run is the writes that came close together (two minutes apart at most). Writes from before sizes were kept say `unknown`."""
    flow = await _load_visible(ctx, int_field(payload, "flow_id"))
    db = ctx.engine.db
    found = await db.flows.written_since(flow["id"], datetime.now(timezone.utc) - timedelta(days=RUNS_DAYS))
    runs: list[list[dict[str, Any]]] = []
    for w in found:                                          # newest first
        if runs and runs[-1][-1]["occurred_at"] - w["occurred_at"] <= RUN_GAP:
            runs[-1].append(w)
        else:
            runs.append([w])

    def file_of(w: dict[str, Any]) -> dict[str, Any]:
        bundle = w["source_relative_path"] == "<bundle>"
        return {"path": w["written_path"], "relative_path": None if bundle else w["source_relative_path"], "bundle": bundle, "outcome": w["outcome"] or "unknown",
                "bytes_before": w["bytes_before"], "bytes_after": w["bytes_after"], "destination_id": w["destination_id"],
                "machine": w["hostname"], "at": w["occurred_at"].isoformat()}

    def summary(run: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for w in run:
            counts[w["outcome"] or "unknown"] = counts.get(w["outcome"] or "unknown", 0) + 1
        return {"started_at": run[-1]["occurred_at"].isoformat(), "ended_at": run[0]["occurred_at"].isoformat(), "files": len(run), "counts": counts,
                "bytes": sum(w["bytes_after"] or 0 for w in run if w["outcome"] != "kept_beside")}

    waiting = []
    for d in flow.get("destinations") or []:
        if d.get("paused_reason"):
            waiting.append({"kind": "destination", "destination_id": d["id"], "why": d["paused_reason"]})
    for c in await db.flows.asked_consents():
        if c.get("flow_id") == flow["id"]:
            waiting.append({"kind": "consent", "consent_id": c["id"], "why": "held for its owner's consent"})
    return {"flow_id": flow["id"],
            "last": {**summary(runs[0]), "items": [file_of(w) for w in reversed(runs[0])]} if runs else None,
            "waiting": waiting, "earlier": [summary(r) for r in runs[1:RUNS_SHOWN + 1]], "runs": len(runs)}
