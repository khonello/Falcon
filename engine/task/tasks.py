"""Task lifecycle (Task -> Task Lifecycle).

    created -> proposed (LLM structure) -> reviewed (assigner confirms / corrects / resolves
    collision / explicit None) -> assigned -> started (assignee acknowledges) -> [expectation
    signals] -> verified (assigner, manual, whole task) -> complete | incomplete -> closed

Deadlines: one soft + one final per task, both scheduled Events on the Scheduler, surfaced with
the shared pulsing status indicator. The assignee (Client) can view, start, and watch --
never verify or close.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub
from engine.task import llm_graph, verification

STATUSES = ("proposed", "assigned", "started", "complete", "incomplete", "closed")


@handler("task.propose")
async def propose(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"description": str, "assignee_account_id": int} -> LLM-populated structure for review.
    Nothing is committed here; a flagged structure must go back to the assigner."""
    description = str(payload.get("description", ""))
    structure = await llm_graph.populate(ctx.engine.llm, description)
    collisions = await verification.check_create_collisions(
        ctx.engine, structure.items, int(payload.get("assignee_account_id", 0)))
    return {
        "items": [vars(i) for i in structure.items],
        "final_deadline": structure.final_deadline,
        "soft_deadline": structure.soft_deadline,
        "flags": structure.flags,
        "proposed_split": structure.proposed_split,
        "collisions": collisions,
        "needs_assigner": structure.needs_assigner() or bool(collisions),
    }


@handler("task.create")
async def create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Assigner commits a reviewed structure (or explicit verification None). Refuses if any
    Create-intent collision is unresolved. Schedules soft/final deadline Events."""
    return stub("task.create", payload)


@handler("task.list")
async def list_tasks(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("task.list", payload)


@handler("task.get")
async def get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Includes the live verification stack status and expectation signals."""
    return stub("task.get", payload)


@handler("task.start")
async def start(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Assignee acknowledges start. Client role is allowed here."""
    return stub("task.start", payload)


@handler("task.verify")
async def verify(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Assigner only. {"task_id", "outcome": "complete"|"incomplete"} -- whole task, never
    per item. The only path to 'complete'."""
    return stub("task.verify", payload)


@handler("task.close")
async def close(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("task.close", payload)
