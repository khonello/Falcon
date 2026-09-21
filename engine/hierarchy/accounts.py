"""Departments, accounts, PCs (Hierarchy -> Identity Model, Department Creation & Assignment,
Offboarding & Deprovisioning).

Identity Model: one account <-> exactly one PC. Offboarding deactivates, never deletes.
Department creation and Admin assignment are Super User only.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub


@handler("hierarchy.department_create")
async def department_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("hierarchy.department_create", payload)


@handler("hierarchy.account_create")
async def account_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"role", "department_id", "pc_id"} -- provisions the client_id/derived key too (spec 8.2)."""
    return stub("hierarchy.account_create", payload)


@handler("hierarchy.account_offboard")
async def account_offboard(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("hierarchy.account_offboard", payload)


@handler("hierarchy.pc_register")
async def pc_register(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("hierarchy.pc_register", payload)
