"""What the core features suggest to each other, and to the people running them.

Detective sees things the others cannot: a folder that keeps appearing in cases but is not restricted, a flow whose source machine is under an urgent case, a case escalated to the
Super User. The unified system lets it say so -- but it may only SAY so. A proposal is a suggestion written down for a person: nothing is marked, paused or assigned until somebody
accepts it, and accepting it is the person's act (audited as theirs), never the system's. Dismissing is kept too, so the same suggestion is not made again while it stands.

    proposals.list    {state?: open|accepted|dismissed, limit?}      what is waiting for you
    proposals.decide  {proposal_id, accept, note?}                   accept (and do the safe part) or dismiss

Accepting:  pause_flow  pauses the flow (the person must own the flow, or be the Super User)
            mark_folder says where to mark (a mark is made on the marker's own workstation, so this tells the console which folder; it does not mark anything itself)
            follow_up_task gives the words for a task to the department's Admin (the person creates it on the Tasks page)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from common.detective import folder_of
from engine.bus import Event
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

MAX_OPEN = 500                  # a worst case: the open proposals a person has to read are bounded (the oldest stay, new ones are dropped with a log line)


async def propose(engine: Engine, kind: str, key: str, title: str, *, detail: dict[str, Any], pc_id: int | None, case_id: int | None = None, flow_id: int | None = None) -> int | None:
    """Write a proposal (once per kind and key while it is open). Returns its id, or None if it is already there or the queue is full."""
    db = engine.db
    if not db.connected:
        return None
    if await db.proposals.open_count() >= MAX_OPEN:
        log.warning("proposals: %d are open; not adding %s", MAX_OPEN, key)
        return None
    pc = await db.accounts.pc(pc_id) if pc_id is not None else None
    new = await db.proposals.add(kind, key, title, detail, pc_id, (pc or {}).get("department_id"), case_id, flow_id)
    if new is None:
        return None
    await engine.audit.record(None, "proposal.made", target_type="proposals", target_id=new, pc_id=pc_id, detail={"kind": kind, "title": title, "case_id": case_id})
    note = {"proposal_id": new, "kind": kind, "title": title}
    await engine.push_to_role("super_user", "proposal.made", note)
    if (pc or {}).get("pc_type") == "client_pc" and pc.get("department_id") is not None:
        await engine.push_to_role("admin", "proposal.made", note, department_id=pc["department_id"])
    return new


def install(engine: Engine) -> None:
    async def on_case(event: Event) -> None:
        await on_case_raised(engine, event.data)

    async def on_reviewed(event: Event) -> None:
        await on_case_reviewed(engine, event.data)

    engine.bus.on("case.raised", on_case, stage="tell", name="proposals.case")
    engine.bus.on("case.reviewed", on_reviewed, stage="tell", name="proposals.reviewed")


async def on_case_raised(engine: Engine, data: dict[str, Any]) -> None:
    """A case has been raised: what else, in the other features, would this suggest? Said, not done."""
    case_id, pc_id = data["case_id"], data["pc_id"]
    behaviours = set(data.get("behaviours") or [])
    if not behaviours & {"exfiltration", "collection", "concealment", "capture", "reach"}:
        return
    host = data.get("host") or f"machine {pc_id}"
    # 1. the flows that start on that machine
    if data.get("level") == "urgent" and behaviours & {"exfiltration", "collection"}:
        for row in await engine.db.flows.list_all():
            if row["source_pc_id"] == pc_id and row["status"] == "active":
                await propose(engine, "pause_flow", f"case{case_id}:flow{row['id']}", f"Pause flow #{row['id']}? Its source machine {host} is under an urgent case",
                              detail={"flow_id": row["id"], "why": data.get("intent"), "case_id": case_id}, pc_id=pc_id, case_id=case_id, flow_id=row["id"])
    # 2. a folder that keeps turning up and is not restricted
    folder = await _unmarked_origin(engine, case_id)
    if folder:
        await propose(engine, "mark_folder", f"{pc_id}:{folder.lower()}", f"Mark {folder} as restricted? Files from there are in a case on {host}",
                      detail={"path": folder, "pc_id": pc_id, "host": host, "case_id": case_id, "why": data.get("intent")}, pc_id=pc_id, case_id=case_id)


async def _unmarked_origin(engine: Engine, case_id: int) -> str | None:
    """The folder most of the case's files came from, if they were not restricted (so there is something to suggest), and it is a real folder with several of them."""
    from common.detective import sig_from_dict

    counts: dict[str, int] = {}
    for f in await engine.db.detective.findings(case_id):
        for e in (sig_from_dict(x) for x in (f["evidence"] or [])):
            if e.verb not in ("copied", "moved", "opened", "deleted", "created") or "restricted" in e.tags:
                continue
            origin = folder_of(e.old) if e.old else (folder_of(e.path) if e.verb in ("opened", "deleted") else "")
            if origin and not origin.lower().startswith(("e:", "d:")):
                counts[origin] = counts.get(origin, 0) + 1
    if not counts:
        return None
    folder, n = max(counts.items(), key=lambda kv: kv[1])
    return folder.replace("/", "\\") if n >= 3 else None


async def on_case_reviewed(engine: Engine, data: dict[str, Any]) -> None:
    if data.get("outcome") != "escalated":
        return
    host = data.get("host") or f"machine {data['pc_id']}"
    await propose(engine, "follow_up_task", f"case{data['case_id']}", f"Ask the department's Admin to follow up on {host}?",
                  detail={"case_id": data["case_id"], "description": f"Please look into {data.get('intent', 'the case')} on {host} (case {data['case_id']}) and tell me what you find.",
                          "host": host}, pc_id=data["pc_id"], case_id=data["case_id"])


def _visible(ident: Any, row: dict[str, Any]) -> bool:
    return ident.role == "super_user" or (ident.role == "admin" and row.get("department_id") == ident.department_id)


@handler("proposals.list")
async def proposals_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    state = str(payload.get("state") or "open")
    if state not in ("open", "accepted", "dismissed"):
        raise ProtocolError(ErrorCode.INVALID, "state is open, accepted or dismissed")
    limit = max(1, min(int_field(payload, "limit", required=False) or 100, 500))
    found = [r for r in await ctx.engine.db.proposals.list(state, limit * 4) if _visible(ident, r)][:limit]
    return {"proposals": rows(found)}


@handler("proposals.decide")
async def proposals_decide(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    prop = await db.proposals.get(int_field(payload, "proposal_id"))
    if prop is None or not _visible(ident, prop):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such proposal")
    if prop["state"] != "open":
        raise ProtocolError(ErrorCode.CONFLICT, "it has been answered already")
    accept = bool(payload.get("accept", False))
    note = " ".join(str(payload.get("note") or "").split())[:300] or None
    result: dict[str, Any] = {}
    if accept and prop["kind"] == "pause_flow":
        flow = await db.flows.get(prop["flow_id"]) if prop.get("flow_id") else None
        if flow is None:
            raise ProtocolError(ErrorCode.NOT_FOUND, "that flow is gone")
        if ident.role != "super_user" and flow["created_by_account_id"] != ident.account_id:
            raise ProtocolError(ErrorCode.FORBIDDEN, "only the flow's owner, or the Super User, can pause it")
        if flow["status"] == "active":
            await db.flows.set_status(flow["id"], "paused", "manual")
            await ctx.engine.audit.record(ctx, "flow.paused", target_type="flows", target_id=flow["id"], detail={"because": "a proposal from Detective, accepted", "proposal_id": prop["id"]})
        result = {"flow_id": flow["id"], "paused": True}
    elif accept and prop["kind"] == "mark_folder":
        result = {"mark": prop["detail"].get("path"), "pc_id": prop["detail"].get("pc_id"), "how": "mark it from the machine it is on, on the Restricted page"}
    elif accept and prop["kind"] == "follow_up_task":
        result = {"task_description": prop["detail"].get("description"), "how": "create the task on the Tasks page"}
    await db.proposals.decide(prop["id"], "accepted" if accept else "dismissed", ident.account_id, note)
    await ctx.engine.audit.record(ctx, "proposal.accepted" if accept else "proposal.dismissed", target_type="proposals", target_id=prop["id"],
                                  detail={"kind": prop["kind"], "note": note, **result})
    return {"proposal_id": prop["id"], "accepted": accept, **result}
