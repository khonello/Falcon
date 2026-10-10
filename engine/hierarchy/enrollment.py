"""Registering machines by asking, instead of typing their names (ENGINE-GAPS #15, the user's idea of 27 Sep 2026).

A newly installed Worker finds the Engine and ASKS; the Engine does not hunt for machines on the network.

    enroll.request  {hostname, os?, mac?, department_id?, level?}   -- before the handshake (the machine has no key yet)
                    -> {enrollment_id, code, token, expires_at}
    enroll.wait     {token}                                         -- before the handshake: the machine collects its answer
                    -> {status: pending|confirmed|refused|expired, client_id?, client_key?}   (the key once, ever)
    enroll.list     {}                                              -- Super User: every waiting request; Admin: those for their department
    enroll.confirm  {enrollment_id, code, department_id?, level?}   -- a person confirms, typing the code the machine shows
    enroll.refuse   {enrollment_id}

What it says about itself is a REQUEST, never a grant (propose, never silently resolve): it waits here until a person
confirms it. Pairing: the machine shows a short code on its own screen and whoever confirms must type it, so a machine
that is not really in front of someone cannot finish; five wrong codes refuse it. An Admin confirms only Workers in
their own department; an Admin workstation needs the Super User. The request is audited, rate-limited per address, and
expires after 24 hours. The code is never sent to the people who confirm -- only to the machine that asked.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.hierarchy.accounts import provision
from engine.permissions import int_field, require_department_scope, require_role, str_field
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

LIFETIME = timedelta(hours=24)
MAX_PENDING_PER_ADDRESS = 5
MAX_PENDING = 100
MAX_WRONG_CODES = 5
LEVELS = ("worker", "admin")
PRE_AUTH = frozenset({"enroll.request", "enroll.wait"})        # accepted before the handshake (connection.py)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _peer_host(ctx: Context) -> str | None:
    peer = getattr(ctx.connection, "peer", None)
    return str(peer[0]) if peer else None


def _clean(value: Any, limit: int) -> str | None:
    text = " ".join(str(value or "").split())[:limit]
    return text or None


@handler("enroll.request")
async def request(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """A machine asks to be registered. Nothing is created but the waiting request."""
    db = ctx.engine.db
    hostname = _clean(payload.get("hostname"), 80)
    if not hostname:
        raise ProtocolError(ErrorCode.INVALID, "a machine must say its name")
    level = str(payload.get("level") or "worker")
    if level not in LEVELS:
        raise ProtocolError(ErrorCode.INVALID, f"level must be one of {LEVELS}")
    department_id = payload.get("department_id")
    if department_id is not None:
        try:
            department_id = int(department_id)
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ErrorCode.INVALID, "department_id must be a number") from exc
        if department_id not in {d["id"] for d in await db.accounts.list_departments()}:
            raise ProtocolError(ErrorCode.NOT_FOUND, "no such department")
    peer = _peer_host(ctx)
    if await db.enrollments.pending_count(peer) >= MAX_PENDING_PER_ADDRESS:
        raise ProtocolError(ErrorCode.CONFLICT, "too many requests are already waiting from this address")
    if await db.enrollments.pending_count() >= MAX_PENDING:
        raise ProtocolError(ErrorCode.UNAVAILABLE, "too many requests are waiting; try later")
    code = f"{secrets.randbelow(10000):04d}"
    token = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + LIFETIME
    enrollment_id = await db.enrollments.create(code, _hash(token), hostname, _clean(payload.get("os"), 80),
                                                _clean(payload.get("mac"), 40), department_id, level, peer, expires)
    await ctx.engine.audit.record(None, "enroll.requested", target_type="enrollments", target_id=enrollment_id,
                                  detail={"hostname": hostname, "level": level, "department_id": department_id, "peer": peer})
    ctx.connection.enrollment_id = enrollment_id                      # told the moment it is decided
    announce = {"enrollment_id": enrollment_id, "hostname": hostname, "level": level, "department_id": department_id}
    await ctx.engine.push_to_role("super_user", "enroll.requested", announce)
    if department_id is not None:
        await ctx.engine.push_to_role("admin", "enroll.requested", announce, department_id=department_id)
    return {"enrollment_id": enrollment_id, "code": code, "token": token, "expires_at": expires.isoformat()}


@handler("enroll.wait")
async def wait(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The machine asks how its request went. Once confirmed, it collects its client id and key -- once, ever."""
    db = ctx.engine.db
    token = str_field(payload, "token")
    enr = await db.enrollments.by_token(_hash(token))
    if enr is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such request")
    status = enr["status"]
    if status == "pending" and enr["expires_at"] < datetime.now(timezone.utc):
        await db.enrollments.expire_old()
        status = "expired"
    out: dict[str, Any] = {"status": status}
    if status == "refused":
        out["reason"] = enr["refused_reason"]
    if status == "confirmed":
        if not await db.enrollments.mark_delivered(enr["id"]):
            out["status"] = "collected"                       # the key was handed over already; ask an Admin to rekey
            return out
        pc = await db.accounts.pc(enr["pc_id"])
        out.update({"client_id": pc["client_id"], "client_key": ctx.engine.client_key(pc["client_id"], pc["key_generation"]),
                    "account_id": enr["account_id"], "pc_id": enr["pc_id"]})
        await ctx.engine.audit.record(None, "enroll.collected", target_type="enrollments", target_id=enr["id"])
    return out


def _visible_department(ctx: Context) -> int | None:
    """None for the Super User (every request); an Admin's own department for an Admin."""
    ident = require_role(ctx, "super_user", "admin")
    return None if ident.role == "super_user" else ident.department_id


@handler("enroll.list")
async def listing(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Waiting requests. The Super User sees all of them; an Admin the ones that asked for their department. The code
    is not in this list: it is on the machine's own screen, and the person confirming types it."""
    return {"requests": rows(await ctx.engine.db.enrollments.pending(department_id=_visible_department(ctx)))}


async def _load_pending(ctx: Context, enrollment_id: int) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    enr = await ctx.engine.db.enrollments.get(enrollment_id)
    if enr is None or (ident.role == "admin" and enr["requested_department_id"] != ident.department_id):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such waiting request")
    if enr["status"] != "pending":
        raise ProtocolError(ErrorCode.CONFLICT, f"this request is already {enr['status']}")
    return enr


async def _tell_machine(engine: Engine, enrollment_id: int, status: str) -> None:
    """A nudge on the open connection that asked, so it collects its answer at once (it polls as well)."""
    for conn in list(engine.connections):
        if getattr(conn, "enrollment_id", None) == enrollment_id:
            await conn.push("enroll.decided", {"status": status})


@handler("enroll.confirm")
async def confirm(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"enrollment_id", "code", "department_id"?, "level"?}: the code the machine shows. The department and level
    default to what it asked for. An Admin confirms Workers in their own department only."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    enr = await _load_pending(ctx, int_field(payload, "enrollment_id"))
    if not hmac.compare_digest(str_field(payload, "code").strip(), enr["code"]):
        wrong = await db.enrollments.wrong_code(enr["id"])
        if wrong >= MAX_WRONG_CODES:
            await db.enrollments.refuse(enr["id"], ident.account_id, "too many wrong codes")
            await ctx.engine.audit.record(ctx, "enroll.refused", target_type="enrollments", target_id=enr["id"],
                                          detail={"reason": "too many wrong codes"})
            await _tell_machine(ctx.engine, enr["id"], "refused")
            raise ProtocolError(ErrorCode.FORBIDDEN, "too many wrong codes; the request was refused")
        raise ProtocolError(ErrorCode.INVALID, f"that is not the code on the machine ({MAX_WRONG_CODES - wrong} tries left)")
    level = str(payload.get("level") or enr["requested_level"])
    if level not in LEVELS:
        raise ProtocolError(ErrorCode.INVALID, f"level must be one of {LEVELS}")
    if ident.role == "admin" and level != "worker":
        raise ProtocolError(ErrorCode.FORBIDDEN, "an Admin workstation is confirmed by the Super User")
    department_id = int_field(payload, "department_id", required=False) or enr["requested_department_id"]
    if department_id is None:
        raise ProtocolError(ErrorCode.INVALID, "say which department this machine belongs to")
    require_department_scope(ident, department_id)
    made = await provision(ctx.engine, level, department_id, enr["hostname"])
    await db.enrollments.confirm(enr["id"], ident.account_id, made["account_id"], made["pc_id"])
    await ctx.engine.audit.record(ctx, "enroll.confirmed", target_type="enrollments", target_id=enr["id"],
                                  detail={"hostname": enr["hostname"], "level": level, "department_id": department_id,
                                          "account_id": made["account_id"], "pc_id": made["pc_id"]})
    await _tell_machine(ctx.engine, enr["id"], "confirmed")
    # The key is not in this answer: it goes only to the machine that asked, which collects it with its token.
    return {"enrollment_id": enr["id"], "status": "confirmed", "account_id": made["account_id"], "pc_id": made["pc_id"],
            "hostname": enr["hostname"], "role": level, "department_id": department_id}


@handler("enroll.refuse")
async def refuse(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    enr = await _load_pending(ctx, int_field(payload, "enrollment_id"))
    reason = _clean(payload.get("reason"), 200) or "refused"
    await ctx.engine.db.enrollments.refuse(enr["id"], ident.account_id, reason)
    await ctx.engine.audit.record(ctx, "enroll.refused", target_type="enrollments", target_id=enr["id"],
                                  detail={"hostname": enr["hostname"], "reason": reason})
    await _tell_machine(ctx.engine, enr["id"], "refused")
    return {"enrollment_id": enr["id"], "status": "refused"}


async def expire(engine: Engine) -> int:
    """Scheduler: waiting requests older than 24 hours are expired (the row stays; nothing is deleted)."""
    if not engine.db.connected:
        return 0
    return await engine.db.enrollments.expire_old()

