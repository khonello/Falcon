"""Departments, accounts, PCs (Hierarchy -> Identity Model, Department Creation & Assignment,
Offboarding & Deprovisioning).

Identity Model: one account <-> exactly one PC. Offboarding deactivates, never deletes.
Department creation and Admin assignment are Super User only; an Admin may provision Workers
(and their PCs) inside their own department.

Provisioning issues the PC's `client_id` (spec 8.2). Until Phase 5 the derived key is not
generated -- the client_id alone is what `auth.respond` resolves.
"""

from __future__ import annotations

import secrets
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import (
    int_field,
    outranks,
    require_department_scope,
    require_role,
    str_field,
)
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

PC_TYPE_FOR_ROLE = {"super_user": "super_user_workstation", "admin": "admin_workstation", "worker": "client_pc"}


@handler("hierarchy.department_create")
async def department_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"name": str} -- Super User only. Zero-Admin departments are allowed."""
    ident = require_role(ctx, "super_user")
    name = str_field(payload, "name")
    import asyncpg

    try:
        dept_id = await ctx.engine.db.accounts.create_department(name, ident.account_id)
    except asyncpg.UniqueViolationError as exc:
        raise ProtocolError(ErrorCode.CONFLICT, f"department {name!r} already exists") from exc
    await ctx.engine.audit.record(ctx, "department.created", target_type="departments", target_id=dept_id,
                                  detail={"name": name})
    await seat_watch(ctx.engine, dept_id, name)
    return {"department_id": dept_id, "name": name}


@handler("hierarchy.departments")
async def departments(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    return {"departments": rows(await ctx.engine.db.accounts.list_departments())}


async def seat_watch(engine: Any, department_id: int, name: str) -> None:
    """A department with no Admin must get one within the time the rule allows (a new department starts without; so does one that
    loses its last)."""
    from datetime import datetime, timezone

    from engine.console import accountability

    if any(a["department_id"] == department_id for a in await engine.db.accounts.active_admins()):
        return
    await accountability.watch(engine, "seat", target_table=f"seat:{department_id}", target_id=int(datetime.now(timezone.utc).timestamp()),
                               kind="dept", department_id=department_id, label=name)


async def provision(engine: Any, role: str, department_id: int | None, hostname: str) -> dict[str, Any]:
    """An account and its PC together (one account <-> one PC), with a new client id and its key. Shared by
    `hierarchy.account_create` and by confirming an enrollment, so a machine provisioned either way is the same."""
    client_id = secrets.token_urlsafe(16)
    db = engine.db
    async with db.pool.acquire() as conn, conn.transaction():
        pc_id = await db.accounts.create_pc(hostname, department_id, PC_TYPE_FOR_ROLE[role], client_id)
        account_id = await db.accounts.create(role, department_id, pc_id)
    return {"account_id": account_id, "pc_id": pc_id, "client_id": client_id,
            "client_key": engine.client_key(client_id), "role": role}


@handler("hierarchy.account_create")
async def account_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"role": str, "department_id": int?, "hostname": str} -- provisions the account AND its
    PC together (one account <-> one PC), returning the PC's new client_id.

    Super User may create any role; an Admin may create Workers in their own department.
    """
    ident = require_role(ctx, "super_user", "admin")
    role = str_field(payload, "role", choices=("super_user", "admin", "worker"))
    hostname = str_field(payload, "hostname")
    department_id = int_field(payload, "department_id", required=role != "super_user")
    if not outranks(ident.role, role):
        raise ProtocolError(ErrorCode.FORBIDDEN, f"{ident.role} cannot create a {role}")
    if department_id is not None:
        require_department_scope(ident, department_id)
    made = await provision(ctx.engine, role, department_id, hostname)
    await ctx.engine.audit.record(ctx, "account.created", target_type="accounts", target_id=made["account_id"],
                                  detail={"role": role, "department_id": department_id, "pc_id": made["pc_id"]})
    # client_id + client_key go into the install package; the Engine keeps neither key nor copy.
    return made


@handler("hierarchy.account_offboard")
async def account_offboard(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_id": int}. Deactivates; row and history are kept. Any active session the
    account occupies is ended."""
    ident = require_role(ctx, "super_user", "admin")
    account_id = int_field(payload, "account_id")
    db = ctx.engine.db
    subject = await db.accounts.by_id(account_id)
    if subject is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such account")
    if not outranks(ident.role, subject["role"]):
        raise ProtocolError(ErrorCode.FORBIDDEN, "offboarding is top-down only")
    require_department_scope(ident, subject["department_id"])
    from engine.hierarchy import traversal

    session = await db.sessions.active_for_account(account_id)
    if session is not None:
        await traversal.end_session(ctx.engine, session, "superior_ended", actor=ctx)
    await db.accounts.offboard(account_id)
    await ctx.engine.audit.record(ctx, "account.offboarded", target_type="accounts", target_id=account_id)
    if subject["role"] == "admin" and subject["department_id"] is not None:
        dept = next((d for d in await db.accounts.list_departments() if d["id"] == subject["department_id"]), None)
        await seat_watch(ctx.engine, subject["department_id"], dept["name"] if dept else "A department")
    return {"account_id": account_id, "status": "offboarded"}


@handler("hierarchy.admin_promote")
async def admin_promote(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_id"} -- Super User only. A Worker becomes an Admin of the department they already work in. Their machine becomes an
    Admin workstation and gets a new key (returned once: the install on it must be redone with it); what was installed as a Worker's
    stops working. A department with no Admin is how this is usually reached, but it is allowed to give a department another."""
    require_role(ctx, "super_user")
    account_id = int_field(payload, "account_id")
    db = ctx.engine.db
    subject = await db.accounts.by_id(account_id)
    if subject is None or subject["status"] != "active":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active account")
    if subject["role"] != "worker":
        raise ProtocolError(ErrorCode.CONFLICT, f"only a Worker can be promoted (this is a {subject['role']})")
    from engine.hierarchy import traversal

    session = await db.sessions.active_for_account(account_id)
    if session is not None and session["occupied_via"] != "native":
        await traversal.end_session(ctx.engine, session, "superior_ended", actor=ctx)
    generation = await db.accounts.promote(account_id)
    await ctx.engine.audit.record(ctx, "account.promoted", target_type="accounts", target_id=account_id,
                                  detail={"department_id": subject["department_id"], "pc_id": subject["bound_pc_id"], "key_generation": generation})
    for conn in list(ctx.engine.connections):
        if conn.ctx.identity is not None and conn.ctx.identity.pc_id == subject["bound_pc_id"]:
            conn.writer.close()                  # the machine reconnects with the key it is given now
    return {"account_id": account_id, "role": "admin", "department_id": subject["department_id"], "pc_id": subject["bound_pc_id"],
            "client_id": subject["client_id"], "key_generation": generation,
            "client_key": ctx.engine.client_key(subject["client_id"], generation)}


@handler("hierarchy.admin_limit")
async def admin_limit(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_id", "on": bool} -- Super User only. Limit an Admin to working hours (they cannot enter a machine outside them), or lift it."""
    require_role(ctx, "super_user")
    account_id = int_field(payload, "account_id")
    on = payload.get("on", True)
    if not isinstance(on, bool):
        raise ProtocolError(ErrorCode.INVALID, "on must be true or false")
    subject = await ctx.engine.db.accounts.by_id(account_id)
    if subject is None or subject["role"] != "admin" or subject["status"] != "active":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active Admin")
    await ctx.engine.db.accounts.set_hours_limited(account_id, on)
    await ctx.engine.audit.record(ctx, "admin.limited" if on else "admin.limit_lifted", target_type="accounts", target_id=account_id)
    await ctx.engine.push_to_account(account_id, "account.limited", {"on": on, "working_hours": ctx.engine.settings.working_hours})
    return {"account_id": account_id, "hours_limited": on}


@handler("hierarchy.account_get")
async def account_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    account_id = int_field(payload, "account_id")
    subject = await ctx.engine.db.accounts.by_id(account_id)
    if subject is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such account")
    require_department_scope(ident, subject["department_id"])
    subject.pop("client_id", None)  # credentials are shown once, at provisioning
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [account_id])
    return {"account": row(subject), "name": names.get(account_id)}


@handler("hierarchy.pc_register")
async def pc_register(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"hostname": str, "department_id": int?, "pc_type": str} -- a PC without an account yet
    (e.g. pre-staging hardware). Binding happens via account_create's hostname later."""
    ident = require_role(ctx, "super_user", "admin")
    hostname = str_field(payload, "hostname")
    pc_type = str_field(payload, "pc_type", choices=("super_user_workstation", "admin_workstation", "client_pc"))
    department_id = int_field(payload, "department_id", required=pc_type != "super_user_workstation")
    if department_id is not None:
        require_department_scope(ident, department_id)
    client_id = secrets.token_urlsafe(16)
    pc_id = await ctx.engine.db.accounts.create_pc(hostname, department_id, pc_type, client_id)
    await ctx.engine.audit.record(ctx, "pc.registered", target_type="pcs", target_id=pc_id)
    return {"pc_id": pc_id, "client_id": client_id, "client_key": ctx.engine.client_key(client_id)}


@handler("hierarchy.pc_rekey")
async def pc_rekey(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"pc_id": int} -- rotate a PC's client key (lost/compromised install package). The old key
    stops verifying immediately and any live connection from that PC is dropped; the new key is
    returned once for a fresh install package. Super User anywhere; Admin within their department."""
    ident = require_role(ctx, "super_user", "admin")
    pc_id = int_field(payload, "pc_id")
    pc = await ctx.engine.db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such pc")
    if pc["department_id"] is not None:
        require_department_scope(ident, pc["department_id"])
    elif ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the Super User can rekey an undeparted PC")
    generation = await ctx.engine.db.accounts.rekey_pc(pc_id)
    await ctx.engine.audit.record(ctx, "pc.rekeyed", target_type="pcs", target_id=pc_id,
                                  detail={"key_generation": generation})
    for conn in list(ctx.engine.connections):
        if conn.ctx.identity is not None and conn.ctx.identity.pc_id == pc_id and conn is not ctx.connection:
            conn.writer.close()
    return {"pc_id": pc_id, "client_id": pc["client_id"], "key_generation": generation,
            "client_key": ctx.engine.client_key(pc["client_id"], generation)}
