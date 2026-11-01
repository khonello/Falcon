"""Moving the Super User to another machine (the user's setup flow, 16 Oct 2026).

A first install is done from a temporary machine: it is the Super User while the departments are made and the first Admin and Workers are
onboarded. Then the Super User's real, dedicated machine takes over -- the SAME account, so every name, task, report and audit record stays; only
the machine it belongs to changes.

    handover.open     {}                          -- the current Super User allows ONE new machine to ask, for ten minutes
    handover.status   {}                          -- is it open; who is waiting (hostname, how long)
    handover.confirm  {enrollment_id, code}       -- the Super User types the code the new machine shows: it becomes the Super User's machine
    handover.cancel   {}                          -- close the window, refuse anyone waiting

The new machine asks the way any machine does (`enroll.request` with level "super_user"); that is refused unless a handover is open, and a
request is only ever a request: nothing moves until the person at the CURRENT Super User console confirms with the code on the new machine's own
screen. On confirming, in one transaction: the account is bound to the new machine, the old machine's key is rotated (its console and Worker stop
being the Super User's at once), and any session the old machine held is ended. If anything fails, nothing changes. There is always exactly one
Super User machine.
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

OPEN_FOR = timedelta(minutes=10)
MAX_WRONG_CODES = 5

_open: dict[str, Any] = {}          # {"until": datetime, "by": account_id}


def reset_state() -> None:
    _open.clear()


def is_open() -> bool:
    until = _open.get("until")
    if until is None:
        return False
    if until < datetime.now(timezone.utc):
        _open.clear()
        return False
    return True


@handler("handover.open")
async def open_handover(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    _open.update({"until": datetime.now(timezone.utc) + OPEN_FOR, "by": ident.account_id})
    await ctx.engine.audit.record(ctx, "handover.opened", target_type="accounts", target_id=ident.account_id,
                                  detail={"until": _open["until"].isoformat()})
    return {"open": True, "until": _open["until"].isoformat()}


@handler("handover.cancel")
async def cancel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    _open.clear()
    refused = 0
    for r in await ctx.engine.db.enrollments.pending():
        if r["requested_level"] == "super_user":
            await ctx.engine.db.enrollments.refuse(r["id"], ident.account_id, "handover cancelled")
            refused += 1
    await ctx.engine.audit.record(ctx, "handover.cancelled", target_type="accounts", target_id=ident.account_id, detail={"refused": refused})
    return {"open": False, "refused": refused}


@handler("handover.status")
async def status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user")
    waiting = [r for r in await ctx.engine.db.enrollments.pending() if r["requested_level"] == "super_user"]
    return {"open": is_open(), "until": _open["until"].isoformat() if is_open() else None, "waiting": rows(waiting)}


@handler("handover.confirm")
async def confirm(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    db = ctx.engine.db
    enr = await db.enrollments.get(int_field(payload, "enrollment_id"))
    if enr is None or enr["requested_level"] != "super_user":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such waiting handover")
    if enr["status"] != "pending":
        raise ProtocolError(ErrorCode.CONFLICT, f"this request is already {enr['status']}")
    if not is_open():
        raise ProtocolError(ErrorCode.CONFLICT, "the handover is not open; open it again (it closes after ten minutes)")
    if not hmac.compare_digest(str_field(payload, "code").strip(), enr["code"]):
        wrong = await db.enrollments.wrong_code(enr["id"])
        if wrong >= MAX_WRONG_CODES:
            await db.enrollments.refuse(enr["id"], ident.account_id, "too many wrong codes")
            await ctx.engine.audit.record(ctx, "handover.refused", target_type="enrollments", target_id=enr["id"], detail={"reason": "too many wrong codes"})
            raise ProtocolError(ErrorCode.FORBIDDEN, "too many wrong codes; the request was refused")
        raise ProtocolError(ErrorCode.INVALID, f"that is not the code on the new machine ({MAX_WRONG_CODES - wrong} tries left)")
    import secrets

    client_id = secrets.token_urlsafe(16)
    old_pc, new_pc = await db.accounts.move_super_user(ident.account_id, enr["hostname"], client_id)
    await db.enrollments.confirm(enr["id"], ident.account_id, ident.account_id, new_pc)
    _open.clear()
    await ctx.engine.audit.record(ctx, "handover.completed", target_type="accounts", target_id=ident.account_id,
                                  detail={"from_pc": old_pc, "to_pc": new_pc, "hostname": enr["hostname"]})
    # the old machine is no longer the Super User's: whatever is connected from it is dropped now
    for conn in list(ctx.engine.connections):
        if conn.ctx.identity is not None and conn.ctx.identity.pc_id == old_pc and conn is not ctx.connection:
            conn.writer.close()
    from engine.hierarchy.enrollment import _tell_machine

    await _tell_machine(ctx.engine, enr["id"], "confirmed")
    return {"status": "moved", "account_id": ident.account_id, "from_pc": old_pc, "to_pc": new_pc, "hostname": enr["hostname"]}
