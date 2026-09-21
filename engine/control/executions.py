"""Action executions (spec 7.3 Script Execution Model, Control -> Dashboard).

One row per run, keyed by execution id (never process name), so a specific run can be
terminated unambiguously. The Engine records and coordinates; the worker client on the target PC
actually runs the action (detached subprocess, output to a per-execution log, tailed by
size-growth polling) and reports back.

Status: pending -> success | failed | terminated | timeout   (`timeout` is distinct from
`failed` and from manual `terminated`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)


async def start(engine: Engine, action: dict[str, Any], event_id: int | None, pc_id: int) -> int:
    """Create the execution row and push `action.execute` to the worker client on `pc_id`."""
    execution_id = await engine.db.control.start_execution(action["id"], event_id, pc_id) or 0
    await engine.broadcast(
        "action.execute",
        {"execution_id": execution_id, "action": action, "timeout_s": action.get("timeout_s")},
        predicate=lambda conn: conn.ctx.identity.pc_id == pc_id,
    )
    await engine.audit.record(None, "action.started", target_type="execution", target_id=execution_id,
                              detail={"action_id": action["id"], "event_id": event_id, "pc_id": pc_id})
    return execution_id


@handler("control.execution_result")
async def execution_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker Client reports {"execution_id", "status", "exit_code"?, "output"?, "error"?}."""
    return stub("control.execution_result", payload)


@handler("control.execution_output")
async def execution_output(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker Client streams incremental output chunks for the Dashboard's live view."""
    return stub("control.execution_output", payload)


@handler("control.terminate")
async def terminate(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Manual termination by execution id, independent of the timeout."""
    return stub("control.terminate", payload)


@handler("control.dashboard")
async def dashboard(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Operational view: everything running/recent with status and output. Refresh mechanism
    (poll vs push) is an open UI-phase item (spec 10.1)."""
    return stub("control.dashboard", payload)
