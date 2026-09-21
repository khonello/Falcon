"""Update & deployment model (spec 9).

  * Super User approves version N+1 -- hard gate: every PC must be confirmed on N first.
  * Rollout cascades: Admins execute it within their own departments.
  * One-step-back compatibility: N supports N-1 only; a PC on N-1 mid-rollout is fully normal.
  * Failed attempts retry automatically when the PC is idle (client-side, same idle mechanism as
    the file sweep); past a threshold (open item 10.4) it escalates to that PC's Admin.
  * Super User sees an aggregate rollout-health view grouped by department, never per-PC noise.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub


@handler("updates.approve")
async def approve(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only. Refuses unless `db.updates.all_pcs_on(current)` is True."""
    return stub("updates.approve", payload)


@handler("updates.rollout_department")
async def rollout_department(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Admin executes the approved rollout for their own department's Client PCs."""
    return stub("updates.rollout_department", payload)


@handler("updates.report_status")
async def report_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker Client reports {version, status: ok|failed|retrying, attempts}. Past-threshold failures
    become an actionable notice to that PC's Admin via Report Routing."""
    return stub("updates.report_status", payload)


@handler("updates.rollout_health")
async def rollout_health(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User aggregate view, grouped by department."""
    return stub("updates.rollout_health", payload)


@handler("updates.prompt_admin")
async def prompt_admin(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User's second lever: nudge an Admin whose department looks stalled."""
    return stub("updates.prompt_admin", payload)
