"""Traversal & Session Blocking (Hierarchy -> Traversal Path & Depth, Traversal Boundaries).

Depth:  Super User -> Department -> Admin -> Client PC;  Admin -> Client PC (own department);
Client: none.

Session, not traversal, is the unit that gets blocked. One active session per PC, enforced by
the partial unique index `one_active_session_per_pc`. On an occupied target:
  * vertical superior (Super User -> Admin, Admin -> Worker): may block-or-end first, then enter
    (`force: true`); without `force` the caller is told the PC is occupied and by whom
  * horizontal peer (Admin <-> Admin): hard refusal until the session frees naturally
  * a Super User occupant is un-evictable

Traversal Time Limit: an Engine-side countdown per traversal session, extendable on request.
The same deadline governs a network drop mid-traversal -- no separate disconnect logic.

Native sessions: a Worker or Admin occupies its own PC ('native', no deadline) from handshake
to disconnect. Ending it (superior_ended) is what "blocked" means to that user; their client
shows the overlay until `session.released` arrives and it re-claims.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.database import Conflict
from engine.dispatch import Context, handler
from engine.permissions import (
    int_field,
    outranks,
    relationship,
    require_account,
    require_department_scope,
    require_role,
)
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

# Which PC types each role may traverse *into*.
TRAVERSAL_TARGETS = {
    "super_user": ("admin_workstation", "client_pc"),
    "admin": ("client_pc",),
    "worker": (),
}


def can_traverse_to(requester_role: str, target_pc_type: str) -> bool:
    return target_pc_type in TRAVERSAL_TARGETS.get(requester_role, ())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_view(s: dict[str, Any], names: dict[int, str]) -> dict[str, Any]:
    return {
        "session_id": s["id"],
        "pc_id": s["pc_id"],
        "occupant_account_id": s["occupant_account_id"],
        "occupant_name": names.get(s["occupant_account_id"]),
        "occupant_role": s["occupant_role"],
        "occupied_via": s["occupied_via"],
        "entered_at": s["entered_at"].isoformat(),
        "deadline_at": s["deadline_at"].isoformat() if s["deadline_at"] else None,
        "extended_count": s["extended_count"],
        "un_evictable": s["un_evictable"],
        # Conditional Rendering / Traversal-Restricted Files apply to a traversing Admin, never
        # to Super User (Traversal Boundaries -> Super User Exemption).
        "restricted_view": s["occupied_via"] != "native" and s["occupant_role"] != "super_user",
        # The red banner: Super User is inside someone else's view.
        "super_user_banner": s["occupied_via"] != "native" and s["occupant_role"] == "super_user",
    }


# --- native sessions (called from the connection lifecycle) -------------------------------------

async def claim_native_session(engine: Engine, ctx: Context) -> int | None:
    ident = ctx.identity
    if not engine.db.connected or ident.pc_id is None or ident.role == "super_user":
        return None
    active = await engine.db.sessions.active_for_pc(ident.pc_id)
    if active is not None:
        if active["occupant_account_id"] == ident.account_id:
            ctx.active_session_id = active["id"]
            return active["id"]
        # Someone has traversed in: this client is blocked until that session ends.
        names = await engine.db.accounts.display_names_for(ident.account_id, [active["occupant_account_id"]])
        await ctx.connection.push("session.blocked", _session_view(active, names))
        return None
    session_id = await engine.db.sessions.open(ident.pc_id, ident.account_id, "native", None, False)
    ctx.active_session_id = session_id
    return session_id


async def release_native_session(engine: Engine, ctx: Context) -> None:
    ident = ctx.identity
    if not engine.db.connected or ident.pc_id is None:
        return
    active = await engine.db.sessions.active_for_pc(ident.pc_id)
    if active and active["occupied_via"] == "native" and active["occupant_account_id"] == ident.account_id:
        await engine.db.sessions.end(active["id"], "voluntary")


async def end_session(engine: Engine, session: dict[str, Any], reason: str, *,
                      actor: Context | None) -> None:
    """End a session and tell everyone affected: the occupant, and the PC being released."""
    if not await engine.db.sessions.end(session["id"], reason):
        return
    duration = int((_now() - session["entered_at"]).total_seconds())
    await engine.audit.record(actor, "session.ended", target_type="session", target_id=session["id"],
                              detail={"pc_id": session["pc_id"], "reason": reason, "occupied_via": session["occupied_via"],
                                      "occupant_account_id": session["occupant_account_id"],
                                      "duration_seconds": duration})
    payload = {"session_id": session["id"], "pc_id": session["pc_id"], "reason": reason}
    await engine.push_to_account(session["occupant_account_id"], "session.ended", payload)
    if session["occupied_via"] != "native":
        # The PC's own user may re-claim; their client re-sends hierarchy.claim_native.
        await engine.push_to_pc(session["pc_id"], "session.released", payload)


async def expire_due_sessions(engine: Engine) -> None:
    """Scheduler hook: end every session whose deadline has passed and release its block.
    Whether the traverser is still connected is irrelevant (spec 7.1)."""
    if not engine.db.connected:
        return
    for session in await engine.db.sessions.list_expired():
        connected = any(c.ctx.identity.account_id == session["occupant_account_id"]
                        for c in engine.connections if c.authenticated)
        reason = "deadline_expired" if connected else "network_drop_deadline_expired"
        await end_session(engine, session, reason, actor=None)


# --- handlers -----------------------------------------------------------------------------------

@handler("hierarchy.tree")
async def tree(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The hierarchy as visible to the caller. Super User: every department; Admin: own
    department. Names are resolved for the caller only (Display Names)."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    departments = await db.accounts.list_departments()
    if ident.role == "admin":
        departments = [d for d in departments if d["id"] == ident.department_id]
    accounts = await db.accounts.list_all()
    active = {s["pc_id"]: s for s in await db.sessions.list_active()}
    names = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in accounts])

    def account_view(a: dict[str, Any]) -> dict[str, Any]:
        session = active.get(a["bound_pc_id"])
        return {"account_id": a["id"], "role": a["role"], "name": names.get(a["id"]), "status": a["status"],
                "pc_id": a["bound_pc_id"], "hostname": a["hostname"], "pc_type": a["pc_type"],
                "session": _session_view(session, names) if session else None}

    out = []
    for d in departments:
        members = [a for a in accounts if a["department_id"] == d["id"]]
        out.append({"department_id": d["id"], "name": d["name"],
                    "admins": [account_view(a) for a in members if a["role"] == "admin"],
                    "workers": [account_view(a) for a in members if a["role"] == "worker"]})
    return {"viewer": {"account_id": ident.account_id, "role": ident.role}, "departments": out}


@handler("hierarchy.traverse")
async def traverse(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Enter a target PC's session. {"pc_id": int, "force": bool}

    `force` = block-or-end-first; honoured only for vertical relationships and never against
    an un-evictable (Super User) occupant.
    """
    ident = require_role(ctx, "super_user", "admin")
    pc_id = int_field(payload, "pc_id")
    force = bool(payload.get("force", False))
    db = ctx.engine.db

    target = await db.accounts.pc(pc_id)
    if target is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such pc")
    if not can_traverse_to(ident.role, target["pc_type"]):
        raise ProtocolError(ErrorCode.FORBIDDEN, f"{ident.role} cannot traverse into a {target['pc_type']}")
    require_department_scope(ident, target["department_id"])
    if target["id"] == ident.pc_id:
        raise ProtocolError(ErrorCode.INVALID, "that is your own pc")

    active = await db.sessions.active_for_pc(pc_id)
    if active is not None:
        if active["occupant_account_id"] == ident.account_id:
            names = await db.accounts.display_names_for(ident.account_id, [ident.account_id])
            return {"session": _session_view(active, names), "already_occupying": True}
        names = await db.accounts.display_names_for(ident.account_id, [active["occupant_account_id"]])
        view = _session_view(active, names)
        rel = relationship(ident.role, active["occupant_role"])
        if active["un_evictable"]:
            raise ProtocolError(ErrorCode.CONFLICT, f"occupied by {view['occupant_name']} (un-evictable)")
        if rel != "vertical":
            raise ProtocolError(ErrorCode.CONFLICT,
                                f"occupied by {view['occupant_name']}; no rights to block a {rel} session")
        if not force:
            raise ProtocolError(ErrorCode.CONFLICT,
                                f"occupied by {view['occupant_name']}; pass force=true to block-or-end first")
        await end_session(ctx.engine, active, "superior_ended", actor=ctx)

    deadline = _now() + timedelta(minutes=ctx.engine.settings.traversal_limit_minutes)
    try:
        session_id = await db.sessions.open(pc_id, ident.account_id, "traversal", deadline,
                                            ident.role == "super_user")
    except Conflict as exc:  # raced with another entrant
        raise ProtocolError(ErrorCode.CONFLICT, "pc became occupied; try again") from exc
    ctx.active_session_id = session_id
    session = await db.sessions.by_id(session_id)
    assert session is not None
    await ctx.engine.audit.record(ctx, "session.traversed", target_type="session", target_id=session_id,
                                  detail={"pc_id": pc_id, "forced": force, "deadline_at": deadline.isoformat()})
    names = await db.accounts.display_names_for(target["bound_account_id"] or ident.account_id, [ident.account_id])
    view = _session_view(session, names)
    await ctx.engine.push_to_pc(pc_id, "session.blocked", view)
    my_names = await db.accounts.display_names_for(ident.account_id, [ident.account_id])
    return {"session": _session_view(session, my_names), "already_occupying": False}


@handler("hierarchy.end_session")
async def end_session_handler(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"session_id": int}. The occupant ends their own session (voluntary); a vertical
    superior may end someone else's (superior_ended); peers may not."""
    ident = require_account(ctx)
    session_id = int_field(payload, "session_id")
    session = await ctx.engine.db.sessions.by_id(session_id)
    if session is None or session["ended_at"] is not None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active session")
    if session["occupant_account_id"] == ident.account_id:
        reason = "voluntary"
    elif outranks(ident.role, session["occupant_role"]) and not session["un_evictable"]:
        target = await ctx.engine.db.accounts.pc(session["pc_id"])
        require_department_scope(ident, target["department_id"] if target else None)
        reason = "superior_ended"
    else:
        raise ProtocolError(ErrorCode.FORBIDDEN, "no rights over this session")
    await end_session(ctx.engine, session, reason, actor=ctx)
    if ctx.active_session_id == session_id:
        ctx.active_session_id = None
    return {"ended": True, "reason": reason}


@handler("hierarchy.extend_session")
async def extend_session(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Extend the Traversal Time Limit by one extension step. Occupant only."""
    ident = require_account(ctx)
    session_id = int_field(payload, "session_id")
    session = await ctx.engine.db.sessions.by_id(session_id)
    if session is None or session["ended_at"] is not None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active session")
    if session["occupant_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the occupant can extend")
    if session["deadline_at"] is None:
        raise ProtocolError(ErrorCode.INVALID, "native sessions have no time limit")
    base = max(session["deadline_at"], _now())
    new_deadline = base + timedelta(minutes=ctx.engine.settings.traversal_extension_minutes)
    await ctx.engine.db.sessions.extend(session_id, new_deadline)
    await ctx.engine.audit.record(ctx, "session.extended", target_type="session", target_id=session_id,
                                  detail={"deadline_at": new_deadline.isoformat()})
    await ctx.engine.push_to_pc(session["pc_id"], "session.extended",
                                {"session_id": session_id, "deadline_at": new_deadline.isoformat()})
    return {"deadline_at": new_deadline.isoformat(), "extended_count": session["extended_count"] + 1}


@handler("hierarchy.session_state")
async def session_state(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """What a client renders from. {"pc_id": int?} -- defaults to the caller's own PC.
    Returns the active session on that PC (if any) and the session the caller occupies."""
    ident = require_account(ctx)
    pc_id = int_field(payload, "pc_id", required=False) or ident.pc_id
    db = ctx.engine.db
    pc_session = await db.sessions.active_for_pc(pc_id) if pc_id is not None else None
    mine = await db.sessions.active_for_account(ident.account_id)
    subjects = [s["occupant_account_id"] for s in (pc_session, mine) if s]
    names = await db.accounts.display_names_for(ident.account_id, subjects)
    return {
        "pc_id": pc_id,
        "pc_session": _session_view(pc_session, names) if pc_session else None,
        "my_session": _session_view(mine, names) if mine else None,
        "blocked": bool(pc_session and pc_session["occupant_account_id"] != ident.account_id
                        and pc_id == ident.pc_id),
    }


@handler("hierarchy.claim_native")
async def claim_native(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """A Worker/Admin client (re-)claims its own PC after a block is released."""
    require_account(ctx)
    session_id = await claim_native_session(ctx.engine, ctx)
    return {"session_id": session_id, "blocked": session_id is None}
