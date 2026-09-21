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
    return {"department_id": dept_id, "name": name}


@handler("hierarchy.departments")
async def departments(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    return {"departments": rows(await ctx.engine.db.accounts.list_departments())}


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
    client_id = secrets.token_urlsafe(16)
    db = ctx.engine.db
    async with db.pool.acquire() as conn, conn.transaction():
        pc_id = await db.accounts.create_pc(hostname, department_id, PC_TYPE_FOR_ROLE[role], client_id)
        account_id = await db.accounts.create(role, department_id, pc_id)
    await ctx.engine.audit.record(ctx, "account.created", target_type="accounts", target_id=account_id,
                                  detail={"role": role, "department_id": department_id, "pc_id": pc_id})
    return {"account_id": account_id, "pc_id": pc_id, "client_id": client_id, "role": role}


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
    return {"account_id": account_id, "status": "offboarded"}


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
    pc_id = await ctx.engine.db.accounts.create_pc(hostname, department_id, pc_type, secrets.token_urlsafe(16))
    await ctx.engine.audit.record(ctx, "pc.registered", target_type="pcs", target_id=pc_id)
    return {"pc_id": pc_id}
