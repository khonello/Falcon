"""Update & deployment model (spec 9).

  * Super User approves version N+1 -- hard gate: every PC must be confirmed on N first.
  * Rollout cascades: Admins execute it within their own departments (worker clients are told
    to update; they retry on idle by themselves).
  * One-step-back compatibility: N supports N-1 only; a PC on N-1 mid-rollout is fully normal.
  * Failed attempts are retried by the client when idle; past a threshold (open item 10.4,
    count-based here and tunable via FALCON_UPDATE_ESCALATION_FAILURES) the failure escalates
    to that PC's Admin as an actionable notice and an 'update_status' report.
  * Super User sees an aggregate rollout-health view grouped by department, never per-PC
    noise -- and can prompt an Admin whose department looks stalled.
"""

from __future__ import annotations

import logging
from typing import Any

from engine.dispatch import Context, handler
from engine.hierarchy import reports
from engine.permissions import (
    int_field,
    require_account,
    require_department_scope,
    require_role,
    str_field,
)
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

log = logging.getLogger(__name__)


def _behind_view(rows_: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"pc_id": r["id"], "hostname": r["hostname"], "department_id": r["department_id"],
             "current_version_id": r["current_version_id"]} for r in rows_]


@handler("updates.current")
async def current(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_account(ctx)
    return {"version": row(await ctx.engine.db.updates.current_version())}


@handler("updates.approve")
async def approve(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only. {"version": "1.2.0"}. Refused while any PC is not confirmed on the
    current version -- the system never has more than N and N+1 in flight."""
    ident = require_role(ctx, "super_user")
    version = str_field(payload, "version")
    db = ctx.engine.db
    if await db.updates.version_by_string(version):
        raise ProtocolError(ErrorCode.CONFLICT, f"version {version} already approved")
    cur = await db.updates.current_version()
    if cur is not None:
        behind = await db.updates.pcs_behind(cur["id"])
        if behind:
            raise ProtocolError(ErrorCode.CONFLICT,
                                f"{len(behind)} PC(s) are not yet confirmed on {cur['version_string']}: "
                                + ", ".join(b["hostname"] for b in behind[:5]))
    version_id = await db.updates.approve_version(version, ident.account_id)
    await ctx.engine.audit.record(ctx, "update.approved", target_type="versions", target_id=version_id,
                                  detail={"version": version})
    await ctx.engine.push_to_role("admin", "update.approved", {"version_id": version_id, "version": version})
    return {"version_id": version_id, "version": version}


@handler("updates.rollout_department")
async def rollout_department(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Admin executes the approved rollout for their own department (Super User may too).
    {"department_id"?} -- targets every PC in the department not yet on the current version."""
    ident = require_role(ctx, "super_user", "admin")
    department_id = int_field(payload, "department_id", required=ident.role == "super_user") or ident.department_id
    require_department_scope(ident, department_id)
    db = ctx.engine.db
    cur = await db.updates.current_version()
    if cur is None:
        raise ProtocolError(ErrorCode.CONFLICT, "no approved version")
    targets = [b for b in await db.updates.pcs_behind(cur["id"]) if b["department_id"] == department_id]
    if not targets:
        return {"version": cur["version_string"], "targeted": []}
    await db.updates.set_target([t["id"] for t in targets], cur["id"])
    for t in targets:
        await ctx.engine.push_to_pc(t["id"], "update.available", {"version_id": cur["id"],
                                                                  "version": cur["version_string"]})
    await ctx.engine.audit.record(ctx, "update.rollout", target_type="departments", target_id=department_id,
                                  detail={"version": cur["version_string"], "pcs": [t["id"] for t in targets]})
    return {"version": cur["version_string"], "targeted": _behind_view(targets)}


@handler("updates.report_status")
async def report_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker client reports an attempt: {"version": str, "succeeded": bool, "running": str?}
    -- `running` (the version the PC is actually on) is required for a failed first report.
    Past the escalation threshold, failures become an actionable notice to the PC's Admin."""
    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no pc bound to this connection")
    version = str_field(payload, "version")
    succeeded = bool(payload.get("succeeded", False))
    db = ctx.engine.db
    v = await db.updates.version_by_string(version)
    if v is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, f"unknown version {version}")
    # `running` (what the PC is actually on) is recorded when it is an approved version; an
    # unknown build (a fresh install) leaves current_version_id NULL = never confirmed, behind.
    running = str_field(payload, "running", required=False)
    rv = await db.updates.version_by_string(running) if running else None
    st = await db.updates.record_attempt(ident.pc_id, v["id"], succeeded, rv["id"] if rv else None)
    await ctx.engine.audit.record(ctx, "update.attempt", target_type="pc_version_status", target_id=ident.pc_id,
                                  detail={"version": version, "succeeded": succeeded,
                                          "failures": st["attempt_failure_count"]})
    escalated = False
    threshold = ctx.engine.settings.update_escalation_failures
    if not succeeded and st["attempt_failure_count"] >= threshold and st["escalated_at"] is None:
        await db.updates.mark_escalated(ident.pc_id)
        escalated = True
        await reports.emit(ctx.engine, "update_status", source_table="pc_version_status", source_id=st["id"],
                           summary=f"update to {version} failed {st['attempt_failure_count']}x on pc {ident.pc_id}")
        await ctx.engine.push_to_role("admin", "update.escalated",
                                      {"pc_id": ident.pc_id, "version": version,
                                       "failures": st["attempt_failure_count"]},
                                      department_id=ident.department_id)
    return {"failures": st["attempt_failure_count"], "escalated": escalated,
            "current_version_id": st["current_version_id"], "target_version_id": st["target_version_id"]}


@handler("updates.rollout_health")
async def rollout_health(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User: aggregate by department. Admin: their own department plus its PCs behind."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    cur = await db.updates.current_version()
    health = await db.updates.rollout_health_by_department()
    if ident.role == "admin":
        health = [h for h in health if h["department_id"] == ident.department_id]
        behind = [b for b in (await db.updates.pcs_behind(cur["id"]) if cur else [])
                  if b["department_id"] == ident.department_id]
        return {"version": row(cur), "departments": rows(health), "pcs_behind": _behind_view(behind)}
    return {"version": row(cur), "departments": rows(health)}


@handler("updates.prompt_admin")
async def prompt_admin(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User's second lever: nudge a department's Admins whose rollout looks stalled.
    {"department_id", "message"?}"""
    require_role(ctx, "super_user")
    department_id = int_field(payload, "department_id")
    message = payload.get("message") or "Super User is asking about your department's update rollout."
    await ctx.engine.push_to_role("admin", "update.prompt", {"message": message}, department_id=department_id)
    await ctx.engine.audit.record(ctx, "update.prompt", target_type="departments", target_id=department_id)
    return {"department_id": department_id, "prompted": True}
