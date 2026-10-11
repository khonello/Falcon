"""Running a built-in action on one machine for the system's own reasons (an issue's *Delete this copy*), outside any automation.

The run is a real execution like any other (its own timeout, output, termination, audit), so it needs an action row to belong to.
That row is made for the run and archived at once: it is a record of what was done, not an entry in the Actions library.
"""

from __future__ import annotations

from typing import Any

from engine.control import executions
from engine.control.actions import BUILTIN, SETTLE_SECONDS, check_params, run_length
from engine.dispatch import Context
from protocol import ErrorCode, ProtocolError


async def run_on_machine(ctx: Context, builtin_type: str, params: dict[str, Any], pc_id: int, *, name: str,
                         timeout_s: int = 60) -> int:
    """Start `builtin_type` on `pc_id` now; returns the execution id. The machine must be connected."""
    if pc_id not in ctx.engine.online_pc_ids():
        raise ProtocolError(ErrorCode.UNAVAILABLE, "that machine is not connected, so nothing can be run on it")
    spec = BUILTIN[builtin_type]
    cleaned = check_params(builtin_type, params)
    db = ctx.engine.db
    creator = (ctx.viewed_by or ctx.identity).account_id
    action_id = await db.control.create_action(creator, spec["category"], max(timeout_s, run_length(cleaned) + SETTLE_SECONDS),
                                               builtin_type=builtin_type, name=name, params=cleaned)
    await db.control.archive_action(action_id)
    action = await db.control.action(action_id)
    assert action is not None
    execution_id = await executions.start(ctx.engine, action, None, pc_id, actor=ctx)
    if execution_id is None:                       # a delayed run: not what the system asks for here
        raise ProtocolError(ErrorCode.INTERNAL, "the run was delayed")
    return execution_id
