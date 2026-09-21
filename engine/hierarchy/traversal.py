"""Traversal & Session Blocking (Hierarchy -> Traversal Path & Depth, Traversal Boundaries).

Depth:  Super User -> Department -> Admin -> Client PC;  Admin -> Client PC;  Client: none.

Session, not traversal, is the unit that gets blocked. One active session per PC, enforced by
the partial unique index `one_active_session_per_pc`. On an occupied target:
  * vertical superior (Super User -> Admin, Admin -> Worker): may block-or-end first, then enter
  * horizontal peer (Admin <-> Admin): hard refusal until the session frees naturally
  * a Super User occupant is un-evictable

Traversal Time Limit: an Engine-side countdown per Admin-level session, extendable on request.
The same deadline governs a network drop mid-traversal -- no separate disconnect logic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

DEFAULT_TRAVERSAL_LIMIT = timedelta(minutes=30)  # tunable; counted at the Admin level

ROLE_RANK = {"super_user": 3, "admin": 2, "worker": 1}


def relationship(requester_role: str, occupant_role: str) -> str:
    """'vertical' (requester outranks occupant), 'horizontal' (peers), or 'inferior'."""
    r, o = ROLE_RANK.get(requester_role, 0), ROLE_RANK.get(occupant_role, 0)
    if r > o:
        return "vertical"
    if r == o:
        return "horizontal"
    return "inferior"


def can_traverse_to(requester_role: str, target_pc_type: str) -> bool:
    if requester_role == "super_user":
        return target_pc_type in ("admin_workstation", "client_pc")
    if requester_role == "admin":
        return target_pc_type == "client_pc"
    return False


async def expire_due_sessions(engine: Engine) -> None:
    """Scheduler hook: end every session whose deadline has passed and release its block.
    Whether the traverser is still connected is irrelevant (spec 7.1)."""
    for session in await engine.db.sessions.list_expired() or []:
        await engine.db.sessions.end(session["id"], "deadline_expired")
        await engine.audit.record(None, "session.expired", target_type="session", target_id=session["id"])
        await engine.broadcast("session.ended", {"session_id": session["id"], "reason": "deadline_expired"})


# --- handlers -----------------------------------------------------------------------------------

@handler("hierarchy.tree")
async def tree(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The hierarchy as visible to the caller: Super User sees all; Admin sees own department."""
    return stub("hierarchy.tree", payload)


@handler("hierarchy.traverse")
async def traverse(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Enter a target PC's session. payload: {"pc_id": int, "force": bool}

    `force` = block-or-end-first; only honoured for vertical relationships and never against an
    un-evictable (Super User) occupant. Returns the new session with its deadline and the
    red-banner flag (`traversed_by_super_user`).
    """
    pc_id = payload.get("pc_id")
    if pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "pc_id required")
    # SCAFFOLD -- real flow:
    #   target = db.pcs.get(pc_id); check can_traverse_to(role, target.pc_type)
    #   active = db.sessions.active_for_pc(pc_id)
    #   if active: rel = relationship(...); if horizontal/inferior or un_evictable -> CONFLICT
    #              if vertical and force -> end(active, 'superior_ended'), push session.ended
    #   open session (occupied_via='traversal', deadline=now+limit, un_evictable=role=='super_user')
    #   audit; return {session_id, deadline_at, banner}
    return stub("hierarchy.traverse", payload)


@handler("hierarchy.end_session")
async def end_session(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("hierarchy.end_session", payload)


@handler("hierarchy.extend_session")
async def extend_session(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Extend the Traversal Time Limit; counted at the Admin level regardless of occupant."""
    return stub("hierarchy.extend_session", payload)


@handler("hierarchy.session_state")
async def session_state(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """What the client renders from: occupied?, by whom (display-name resolved), deadline,
    whether Conditional Rendering / Traversal-Restricted boundaries apply (never for Super User)."""
    return stub("hierarchy.session_state", payload)


def _deadline(now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)) + DEFAULT_TRAVERSAL_LIMIT
