"""Cross-Department Assisted Access (Hierarchy -> Cross-Department Assisted Access; spec 7.1).

A consent-based, temporary, peer-to-peer relationship between Admins. Deliberately its own
state machine -- it does NOT reuse the traversal code path, because entry is granted by
consent, not seized by authority (no block-or-end-first, no eviction mechanic).

    request  --match-->  offered (helper pushed an offer)  --accept-->  active  --close-->  closed
       \\--no match-->  no_match (row kept, never queued or retried)

Two entry paths, both live at once: requester-initiated (`request`, optionally targeting a
department) and helper-initiated (`set_available`, then a requester picks from
`available_helpers` via `request` with `helper_account_id`).

Access is two-layered: BASELINE_CEILING is the system-defined limit; the requester may only
narrow it. Once accepted, the helper occupies the requester's workstation session
(occupied_via='assisted_access', with the traversal time limit) and either party may close it.
Every instance is a Report under 'cross_department_assistance'; Super User always sees it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.database import Conflict
from engine.dispatch import Context, handler
from engine.hierarchy import reports
from engine.permissions import int_field, require_role
from engine.serialize import row
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

# System-defined baseline: what a helper can ever touch on a peer's workstation. A helper
# never sees Resource files or Message Channels; they get the operational surface needed
# for hands-on technical help.
BASELINE_CEILING: dict[str, bool] = {
    "control_actions": True,
    "monitoring_actions": True,
    "custom_actions": False,
    "tasks": False,
    "flows": False,
    "resource_files": False,
    "message_channels": False,
    "reports": False,
}

# request_id -> pending offer (helper_account_id) awaiting accept; in-memory is fine: an offer
# is moment-in-time and does not survive an Engine restart by design (no lingering requests).
_pending_offers: dict[int, dict[str, Any]] = {}


def reset_state() -> None:
    _pending_offers.clear()


def effective_scope(ceiling: dict[str, bool], narrowing: dict[str, Any] | None) -> dict[str, bool]:
    """Intersect: the requester can only remove from the ceiling, never add to it."""
    scope = dict(ceiling)
    for key, allowed in (narrowing or {}).items():
        if key in scope and not allowed:
            scope[key] = False
    return scope


@handler("assisted_access.set_available")
async def set_available(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Helper broadcasts / withdraws availability. {"available": bool}"""
    ident = require_role(ctx, "admin")
    available = bool(payload.get("available", True))
    await ctx.engine.db.accounts.set_assistance_available(ident.account_id, available)
    await ctx.engine.audit.record(ctx, "assisted_access.availability", detail={"available": available})
    return {"available": available}


@handler("assisted_access.available_helpers")
async def available_helpers(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Moment-in-time list of Admins reachable now (opted in, not occupying any session).
    {"department_id": int?}"""
    ident = require_role(ctx, "admin")
    department_id = int_field(payload, "department_id", required=False)
    helpers = await ctx.engine.db.sessions.available_helpers(department_id, ident.account_id)
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [h["id"] for h in helpers])
    return {"helpers": [{**h, "name": names.get(h["id"])} for h in helpers]}


@handler("assisted_access.request")
async def request(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"department_id": int?, "helper_account_id": int?, "narrowing": {key: bool}?}

    Matches an available helper (a specific one if given, else the first reachable in the
    department / anywhere) and pushes them an offer. No helper -> `matched: false`, try again
    later; the request row records the unmatched attempt and is never queued."""
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    department_id = int_field(payload, "department_id", required=False)
    wanted = int_field(payload, "helper_account_id", required=False)
    narrowing = payload.get("narrowing") or {}
    if not isinstance(narrowing, dict):
        raise ProtocolError(ErrorCode.INVALID, "narrowing must be an object")
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "requester has no bound workstation")

    candidates = await db.sessions.available_helpers(department_id, ident.account_id)
    if wanted is not None:
        candidates = [c for c in candidates if c["id"] == wanted]
    entry_path = "helper_broadcast" if wanted is not None else "requester_initiated"
    request_id = await db.sessions.create_assisted_request(
        ident.account_id, department_id, entry_path, BASELINE_CEILING, narrowing)
    if not candidates:
        await ctx.engine.audit.record(ctx, "assisted_access.no_match", target_type="assisted_access_requests",
                                      target_id=request_id)
        return {"request_id": request_id, "matched": False,
                "message": "no admin is available right now -- try again later"}

    helper = candidates[0]
    _pending_offers[request_id] = {"helper_account_id": helper["id"], "requester_account_id": ident.account_id,
                                   "requester_pc_id": ident.pc_id, "scope": effective_scope(BASELINE_CEILING, narrowing),
                                   "offered_at": datetime.now(timezone.utc)}
    names = await db.accounts.display_names_for(helper["id"], [ident.account_id])
    await ctx.engine.push_to_account(helper["id"], "assisted_access.offer", {
        "request_id": request_id, "requester_account_id": ident.account_id,
        "requester_name": names.get(ident.account_id), "department_id": ident.department_id,
        "scope": _pending_offers[request_id]["scope"]})
    await ctx.engine.audit.record(ctx, "assisted_access.offered", target_type="assisted_access_requests",
                                  target_id=request_id, detail={"helper_account_id": helper["id"]})
    my_names = await db.accounts.display_names_for(ident.account_id, [helper["id"]])
    return {"request_id": request_id, "matched": True, "helper_account_id": helper["id"],
            "helper_name": my_names.get(helper["id"])}


@handler("assisted_access.accept")
async def accept(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Helper consents to an offer. Opens a session on the requester's workstation
    (occupied_via='assisted_access'); the requester's own native session ends by consent."""
    ident = require_role(ctx, "admin")
    request_id = int_field(payload, "request_id")
    offer = _pending_offers.get(request_id)
    if offer is None or offer["helper_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no pending offer for you with that id")
    db = ctx.engine.db
    from engine.hierarchy import traversal

    native = await db.sessions.active_for_pc(offer["requester_pc_id"])
    if native is not None:
        if native["occupant_account_id"] != offer["requester_account_id"]:
            raise ProtocolError(ErrorCode.CONFLICT, "requester's workstation is occupied by someone else")
        await traversal.end_session(ctx.engine, native, "voluntary", actor=ctx)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=ctx.engine.settings.traversal_limit_minutes)
    try:
        session_id = await db.sessions.open(offer["requester_pc_id"], ident.account_id, "assisted_access",
                                            deadline, False)
    except Conflict as exc:
        raise ProtocolError(ErrorCode.CONFLICT, "requester's workstation became occupied") from exc
    await db.sessions.match_assisted_request(request_id, ident.account_id, session_id)
    _pending_offers.pop(request_id, None)
    ctx.active_session_id = session_id
    await ctx.engine.audit.record(ctx, "assisted_access.accepted", target_type="assisted_access_requests",
                                  target_id=request_id, detail={"session_id": session_id})
    await reports.emit(ctx.engine, "cross_department_assistance", source_table="assisted_access_requests",
                       source_id=request_id, summary=f"assisted access #{request_id} started")
    await ctx.engine.push_to_account(offer["requester_account_id"], "assisted_access.started",
                                     {"request_id": request_id, "session_id": session_id,
                                      "helper_account_id": ident.account_id, "deadline_at": deadline.isoformat(),
                                      "scope": offer["scope"]})
    return {"request_id": request_id, "session_id": session_id, "deadline_at": deadline.isoformat(),
            "scope": offer["scope"]}


@handler("assisted_access.decline")
async def decline(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    request_id = int_field(payload, "request_id")
    offer = _pending_offers.get(request_id)
    if offer is None or offer["helper_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no pending offer for you with that id")
    _pending_offers.pop(request_id, None)
    await ctx.engine.push_to_account(offer["requester_account_id"], "assisted_access.declined",
                                     {"request_id": request_id})
    return {"request_id": request_id, "declined": True}


@handler("assisted_access.close")
async def close(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Either party ends the assistance session. {"request_id": int}"""
    ident = require_role(ctx, "admin")
    request_id = int_field(payload, "request_id")
    db = ctx.engine.db
    req = await db.sessions.assisted_request(request_id)
    if req is None or req["resulting_session_id"] is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no active assistance session with that id")
    if ident.account_id not in (req["requester_account_id"], req["helper_account_id"]):
        raise ProtocolError(ErrorCode.FORBIDDEN, "not a party to this assistance session")
    session = await db.sessions.by_id(req["resulting_session_id"])
    if session is None or session["ended_at"] is not None:
        return {"request_id": request_id, "closed": True, "already": True}
    from engine.hierarchy import traversal

    await traversal.end_session(ctx.engine, session, "voluntary", actor=ctx)
    await ctx.engine.audit.record(ctx, "assisted_access.closed", target_type="assisted_access_requests",
                                  target_id=request_id)
    other = req["helper_account_id"] if ident.account_id == req["requester_account_id"] else req["requester_account_id"]
    await ctx.engine.push_to_account(other, "assisted_access.closed", {"request_id": request_id})
    return {"request_id": request_id, "closed": True}


@handler("assisted_access.status")
async def status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    request_id = int_field(payload, "request_id")
    req = await ctx.engine.db.sessions.assisted_request(request_id)
    if req is None or ident.account_id not in (req["requester_account_id"], req["helper_account_id"]):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such request")
    session = await ctx.engine.db.sessions.by_id(req["resulting_session_id"]) if req["resulting_session_id"] else None
    return {"request": row(req), "session": row(session), "pending_offer": request_id in _pending_offers}


async def clear_offers_for(engine: Engine, account_id: int) -> None:
    """A helper disconnecting withdraws any offer made to them (moment-in-time availability)."""
    for rid, offer in list(_pending_offers.items()):
        if offer["helper_account_id"] == account_id:
            _pending_offers.pop(rid, None)
            await engine.push_to_account(offer["requester_account_id"], "assisted_access.declined",
                                         {"request_id": rid, "reason": "helper disconnected"})


