"""Action executions (spec 7.3 Script Execution Model, Control -> Dashboard).

One row per run, keyed by execution id (never process name), so a specific run can be
terminated unambiguously. The Engine records and coordinates; the worker client on the target
PC actually runs the action (detached subprocess, output to a per-execution log tailed by
size-growth polling) and reports back.

    Engine -> pc     push    action.execute   {execution_id, action, timeout_s}
    pc     -> Engine request control.execution_output {execution_id, chunk}      (streamed)
    pc     -> Engine request control.execution_result {execution_id, status, ...}
    Engine -> pc     push    action.terminate {execution_id}                     (manual stop)

Status: pending -> success | failed | terminated (terminated_reason: timeout | manual).
`timeout` is reported distinctly from `failed`. An Engine-side guard also terminates a run
the worker never reports on (timeout + grace).
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import (
    int_field,
    require_account,
    require_department_scope,
    require_role,
    str_field,
)
from engine.serialize import row
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

GRACE_SECONDS = 15
OUTPUT_CHUNKS_KEPT = 200

# execution_id -> streamed output chunks (the worker keeps the full log file; this is the live
# tail the Dashboard shows). Bounded; not persisted -- output_log_path is the durable record.
_outputs: dict[int, deque[str]] = {}


def reset_state() -> None:
    _outputs.clear()


def _wire_action(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": action["id"], "kind": action["action_kind"], "name": action.get("name"),
        "builtin_type": action.get("builtin_type"), "params": action.get("params") or {},
        "script": action.get("custom_script"), "language": action.get("custom_script_language"),
    }


async def start(engine: Engine, action: dict[str, Any], event_id: int | None, pc_id: int, *,
                actor: Context | None = None) -> int | None:
    """Create the execution row and dispatch to the worker client on `pc_id`, honouring the
    action's timing. Returns the execution id, or None when the run is delayed (the row is
    created when the delay elapses)."""
    timing = action.get("timing") or {"mode": "immediate"}
    delay = int(timing.get("delay_s", 0)) if timing.get("mode") == "delayed" else 0

    async def dispatch() -> int:
        execution_id = await engine.db.control.start_execution(action["id"], event_id, pc_id)
        _outputs[execution_id] = deque(maxlen=OUTPUT_CHUNKS_KEPT)
        await engine.push_to_pc(pc_id, "action.execute", {
            "execution_id": execution_id, "action": _wire_action(action), "timeout_s": action["timeout_seconds"]})
        await engine.audit.record(actor, "action.started", target_type="execution", target_id=execution_id,
                                  detail={"action_id": action["id"], "event_id": event_id, "pc_id": pc_id,
                                          "delayed_s": delay})
        await _notify_dashboard(engine, action, {"execution_id": execution_id, "status": "pending"})
        engine.scheduler.at(f"execution.{execution_id}.guard",
                            datetime.now(timezone.utc) + timedelta(seconds=action["timeout_seconds"] + GRACE_SECONDS),
                            lambda: _guard(engine, execution_id))
        return execution_id

    if delay:
        async def later() -> None:
            await dispatch()

        engine.scheduler.at(f"action.{action['id']}.delayed.{pc_id}.{datetime.now(timezone.utc).timestamp()}",
                            datetime.now(timezone.utc) + timedelta(seconds=delay), later)
        return None
    return await dispatch()


async def _guard(engine: Engine, execution_id: int) -> None:
    ex = await engine.db.control.execution(execution_id)
    if ex is None or ex["status"] != "pending":
        return
    await engine.db.control.finish_execution(execution_id, "terminated", terminated_reason="timeout")
    await engine.audit.record(None, "action.timeout_unreported", target_type="execution", target_id=execution_id)
    action = await engine.db.control.action(ex["action_id"])
    if action:
        await _notify_dashboard(engine, action, {"execution_id": execution_id, "status": "terminated",
                                                 "terminated_reason": "timeout", "unreported": True})


async def _notify_dashboard(engine: Engine, action: dict[str, Any], payload: dict[str, Any]) -> None:
    creator = await engine.db.accounts.by_id(action["created_by_account_id"])
    dept = creator["department_id"] if creator else None
    await engine.push_to_role("admin", "action.status", {"action_id": action["id"], **payload}, department_id=dept)
    await engine.push_to_role("super_user", "action.status", {"action_id": action["id"], **payload})


async def resume_guards(engine: Engine) -> int:
    """Engine start: re-arm timeout guards for executions still pending in the database."""
    if not engine.db.connected:
        return 0
    n = 0
    for ex in await engine.db.control.pending_executions():
        due = ex["started_at"] + timedelta(seconds=ex["timeout_seconds"] + GRACE_SECONDS)
        engine.scheduler.at(f"execution.{ex['id']}.guard", due, lambda eid=ex["id"]: _guard(engine, eid))
        n += 1
    return n


# --- handlers -----------------------------------------------------------------------------------

async def _own_execution(ctx: Context, execution_id: int) -> dict[str, Any]:
    ex = await ctx.engine.db.control.execution(execution_id)
    if ex is None or ex["target_pc_id"] != ctx.identity.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such execution on this pc")
    return ex


@handler("control.execution_output")
async def execution_output(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker streams an output chunk: {"execution_id", "chunk"}."""
    require_account(ctx)
    execution_id = int_field(payload, "execution_id")
    ex = await _own_execution(ctx, execution_id)
    chunk = str(payload.get("chunk", ""))
    _outputs.setdefault(execution_id, deque(maxlen=OUTPUT_CHUNKS_KEPT)).append(chunk)
    action = await ctx.engine.db.control.action(ex["action_id"])
    if action:
        await _notify_dashboard(ctx.engine, action, {"execution_id": execution_id, "status": "pending", "chunk": chunk})
    return {"accepted": True}


@handler("control.execution_result")
async def execution_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker reports {"execution_id", "status": "success"|"failed"|"timeout"|"terminated",
    "exit_code"?, "output_log_path"?, "output"?}."""
    require_account(ctx)
    execution_id = int_field(payload, "execution_id")
    ex = await _own_execution(ctx, execution_id)
    if ex["status"] != "pending":
        return {"recorded": False, "status": ex["status"]}
    reported = str_field(payload, "status", choices=("success", "failed", "timeout", "terminated"))
    status = "terminated" if reported in ("timeout", "terminated") else reported
    reason = {"timeout": "timeout", "terminated": "manual"}.get(reported)
    exit_code = payload.get("exit_code")
    await ctx.engine.db.control.finish_execution(execution_id, status, terminated_reason=reason,
                                                 output_log_path=payload.get("output_log_path"),
                                                 exit_code=int(exit_code) if exit_code is not None else None)
    ctx.engine.scheduler.cancel(f"execution.{execution_id}.guard")
    if payload.get("output"):
        _outputs.setdefault(execution_id, deque(maxlen=OUTPUT_CHUNKS_KEPT)).append(str(payload["output"]))
    await ctx.engine.audit.record(ctx, "action.finished", target_type="execution", target_id=execution_id,
                                  detail={"status": status, "reason": reason, "exit_code": payload.get("exit_code")})
    action = await ctx.engine.db.control.action(ex["action_id"])
    if action:
        await _notify_dashboard(ctx.engine, action, {"execution_id": execution_id, "status": status,
                                                     "terminated_reason": reason, "exit_code": payload.get("exit_code")})
    return {"recorded": True, "status": status}


@handler("control.terminate")
async def terminate(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Manual termination by execution id, independent of the timeout. {"execution_id"}"""
    ident = require_role(ctx, "super_user", "admin")
    execution_id = int_field(payload, "execution_id")
    ex = await ctx.engine.db.control.execution(execution_id)
    if ex is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such execution")
    pc = await ctx.engine.db.accounts.pc(ex["target_pc_id"])
    require_department_scope(ident, pc["department_id"] if pc else None)
    if ex["status"] != "pending":
        raise ProtocolError(ErrorCode.CONFLICT, f"execution already {ex['status']}")
    await ctx.engine.push_to_pc(ex["target_pc_id"], "action.terminate", {"execution_id": execution_id})
    await ctx.engine.audit.record(ctx, "action.terminate_requested", target_type="execution", target_id=execution_id)
    return {"execution_id": execution_id, "requested": True}


@handler("control.execution")
async def execution(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """One execution with its live output tail."""
    ident = require_role(ctx, "super_user", "admin")
    execution_id = int_field(payload, "execution_id")
    ex = await ctx.engine.db.control.execution(execution_id)
    if ex is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such execution")
    pc = await ctx.engine.db.accounts.pc(ex["target_pc_id"])
    require_department_scope(ident, pc["department_id"] if pc else None)
    return {"execution": row(ex), "output": list(_outputs.get(execution_id, []))}


@handler("control.dashboard")
async def dashboard(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Operational view: enabled events with their actions, last fired, recent executions and
    outputs, plus everything currently running. Refresh is push-driven (`action.status`,
    `event.fired`) with this as the full snapshot -- see open item 10.1."""
    from engine.control import events as ev

    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    if ident.role == "super_user":
        defs = await db.control.event_definitions(enabled_only=True)
    else:
        defs = await db.control.events_in_department(ident.department_id, enabled_only=True)
    out = []
    for d in defs:
        actions = []
        for a in await db.control.actions_for_event(d["id"]):
            recent = await db.control.last_executions_for_action(a["id"])
            actions.append({"action": row(a), "recent": [
                {**(row(r) or {}), "output": list(_outputs.get(r["id"], []))[-5:]} for r in recent]})
        out.append({"event": row(d), "last_fired_at": ev.last_fired(d["id"]), "actions": actions})
    live = [row(x) for x in await db.control.live_executions()]
    return {"automations": out, "live": live}
