"""Task lifecycle (Task -> Task Lifecycle).

    propose (LLM structure) -> assigner reviews / corrects / resolves collisions / confirms
    explicit None -> create (active) -> start (assignee; in_progress) -> [expectation signals,
    stack status] -> verify (assigner, manual, whole task) -> completed | stays open

Scope: Super User assigns to an Admin (department-level); Admin assigns to a Worker in their
own department (Client-PC-level). The assignee (Client) can view, start, and watch -- never
verify.

Deadlines: one soft + one final per task, both scheduled Events on the Scheduler that fire
through `control.events.on_signal` ('task.deadline_soft' / 'task.deadline_final') and push a
pulsing-indicator notice to both parties. Rescheduled from the database on Engine start.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_account, require_role, str_field
from engine.serialize import row, rows
from engine.task import llm_graph, verification
from engine.task.verification import VerificationItem
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

STATUSES = ("active", "in_progress", "completed")


# --- helpers ------------------------------------------------------------------------------------

async def _assignee_for(ctx: Context, assignee_account_id: int) -> dict[str, Any]:
    """Enforce assignment scope and return the assignee row."""
    ident = ctx.identity
    assignee = await ctx.engine.db.accounts.by_id(assignee_account_id)
    if assignee is None or assignee["status"] != "active":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active account")
    if ident.role == "super_user" and assignee["role"] != "admin":
        raise ProtocolError(ErrorCode.FORBIDDEN, "Super User assigns department-level tasks to Admins")
    if ident.role == "admin" and not (assignee["role"] == "worker"
                                      and assignee["department_id"] == ident.department_id):
        raise ProtocolError(ErrorCode.FORBIDDEN, "Admin assigns tasks to Workers in their own department")
    return assignee


def _parse_when(payload: dict[str, Any], name: str) -> datetime | None:
    raw = payload.get(name)
    if not raw:
        return None
    try:
        when = datetime.fromisoformat(str(raw))
    except ValueError as exc:
        raise ProtocolError(ErrorCode.INVALID, f"{name} must be ISO 8601") from exc
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


async def _can_view(ctx: Context, task: dict[str, Any]) -> bool:
    ident = ctx.identity
    if ident.account_id in (task["assigner_account_id"], task["assignee_account_id"]):
        return True
    if ident.role == "super_user":
        return True
    return ident.role == "admin" and task["assignee_department_id"] == ident.department_id


async def _task_view(engine: Engine, ctx: Context, task: dict[str, Any]) -> dict[str, Any]:
    names = await engine.db.accounts.display_names_for(
        ctx.identity.account_id, [task["assigner_account_id"], task["assignee_account_id"]])
    view = row(task) or {}
    view["assigner_name"] = names.get(task["assigner_account_id"])
    view["assignee_name"] = names.get(task["assignee_account_id"])
    return view


# --- deadlines as scheduled Events --------------------------------------------------------------

def _job_name(task_id: int, kind: str) -> str:
    return f"task.{task_id}.deadline_{kind}"


def schedule_deadlines(engine: Engine, task: dict[str, Any]) -> None:
    for kind, col in (("soft", "soft_deadline_at"), ("final", "final_deadline_at")):
        when = task.get(col)
        if when is None:
            engine.scheduler.cancel(_job_name(task["id"], kind))
            continue
        engine.scheduler.at(_job_name(task["id"], kind), when, _deadline_job(engine, task["id"], kind))


def cancel_deadlines(engine: Engine, task_id: int) -> None:
    for kind in ("soft", "final"):
        engine.scheduler.cancel(_job_name(task_id, kind))


def _deadline_job(engine: Engine, task_id: int, kind: str) -> Any:
    async def fire() -> None:
        task = await engine.db.tasks.get(task_id)
        if task is None or task["status"] == "completed":
            return
        from engine.control import events

        await engine.audit.record(None, f"task.deadline_{kind}", target_type="tasks", target_id=task_id)
        payload = {"task_id": task_id, "kind": kind, "indicator": "deadline_reached"}
        await engine.push_to_account(task["assigner_account_id"], "task.deadline", payload)
        await engine.push_to_account(task["assignee_account_id"], "task.deadline", payload)
        await events.on_signal(engine, task["assignee_pc_id"] or 0, f"task.deadline_{kind}", {"task_id": task_id})
    return fire


async def reschedule_all(engine: Engine) -> int:
    """Engine start: re-arm every open task's deadlines from the database."""
    if not engine.db.connected:
        return 0
    n = 0
    for task in await engine.db.tasks.active():
        schedule_deadlines(engine, task)
        n += 1
    return n


# --- handlers -----------------------------------------------------------------------------------

@handler("task.propose")
async def propose(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"description": str, "assignee_account_id": int} -> LLM-populated structure for review.

    Nothing is committed here. `needs_assigner` is true when any question in the decision
    graph came back unclear/contradictory, a deadline was ambiguous, several tasks were
    detected, or a Create-intent name collides. When the local LLM is unreachable the
    structure is empty and `llm_available` is false: the assigner uses the manual editor."""
    require_role(ctx, "super_user", "admin")
    description = str_field(payload, "description")
    assignee = await _assignee_for(ctx, int_field(payload, "assignee_account_id"))
    structure = await llm_graph.populate(ctx.engine.llm, description)
    collisions = await verification.check_create_collisions(ctx.engine, structure.items, assignee["bound_pc_id"])
    return {
        "llm_available": ctx.engine.llm.available,
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
    """Assigner commits a reviewed structure.

    {"assignee_account_id", "description", "verification_mode": "stack"|"none",
     "confirm_none": bool, "items": [...], "soft_deadline_at": iso?, "final_deadline_at": iso?}

    Refuses: 'none' without an explicit confirm_none; an empty stack; invalid items; any
    unresolved Create-intent collision (the response lists them so the assigner can supply a
    path or a new name)."""
    ident = require_role(ctx, "super_user", "admin")
    description = str_field(payload, "description")
    assignee = await _assignee_for(ctx, int_field(payload, "assignee_account_id"))
    mode = str_field(payload, "verification_mode", choices=("stack", "none"))
    soft = _parse_when(payload, "soft_deadline_at")
    final = _parse_when(payload, "final_deadline_at")
    if soft and final and soft >= final:
        raise ProtocolError(ErrorCode.INVALID, "soft deadline must be before the final deadline")

    items: list[VerificationItem] = []
    if mode == "none":
        if not payload.get("confirm_none"):
            raise ProtocolError(ErrorCode.INVALID,
                                "no verification must be an explicit choice: pass confirm_none=true")
    else:
        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise ProtocolError(ErrorCode.INVALID, "a verification stack needs at least one item")
        items = [VerificationItem.from_payload(d) for d in raw_items]
        problems = verification.validate_stack(items)
        if problems:
            raise ProtocolError(ErrorCode.INVALID, "; ".join(problems))
        for idx, item in enumerate(items):
            if item.target_type == "file" and item.intent in ("exists", "update"):
                if item.file_index_id is None:
                    raise ProtocolError(ErrorCode.INVALID, f"item {idx + 1}: exists/update needs file_index_id")
                indexed = await ctx.engine.db.file_index.get(item.file_index_id)
                if indexed is None or indexed["pc_id"] != assignee["bound_pc_id"]:
                    raise ProtocolError(ErrorCode.INVALID,
                                        f"item {idx + 1}: file must be indexed on the assignee's PC")
        collisions = await verification.check_create_collisions(ctx.engine, items, assignee["bound_pc_id"])
        if collisions:
            raise ProtocolError(ErrorCode.CONFLICT, "unresolved name collision: "
                                + "; ".join(f"item {c['item_index'] + 1} ({c['name']})" for c in collisions))

    task_id = await ctx.engine.db.tasks.create(
        {"assigner_account_id": ident.account_id, "assignee_account_id": assignee["id"],
         "description_raw": description, "verification_mode": mode,
         "soft_deadline_at": soft, "final_deadline_at": final},
        [item.to_row(i + 1) for i, item in enumerate(items)])
    task = await ctx.engine.db.tasks.get(task_id)
    assert task is not None
    schedule_deadlines(ctx.engine, task)
    await ctx.engine.audit.record(ctx, "task.created", target_type="tasks", target_id=task_id,
                                  detail={"assignee_account_id": assignee["id"], "verification_mode": mode,
                                          "items": len(items)})
    await ctx.engine.push_to_account(assignee["id"], "task.assigned", {"task_id": task_id})
    return {"task": await _task_view(ctx.engine, ctx, task)}


@handler("task.list")
async def list_tasks(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Tasks the caller assigned or is assigned; an Admin also sees their department's;
    Super User sees all. {"include_completed": bool}"""
    ident = require_account(ctx)
    include = bool(payload.get("include_completed", False))
    db = ctx.engine.db
    if ident.role == "super_user":
        found = await db.tasks.list_all(include_completed=include)
    elif ident.role == "admin":
        mine = await db.tasks.list_for(ident.account_id, include_completed=include)
        dept = await db.tasks.list_department(ident.department_id, include_completed=include)
        seen: set[int] = set()
        found = [t for t in mine + dept if not (t["id"] in seen or seen.add(t["id"]))]
    else:
        found = await db.tasks.list_for(ident.account_id, include_completed=include)
    names = await db.accounts.display_names_for(
        ident.account_id, sorted({t["assigner_account_id"] for t in found} | {t["assignee_account_id"] for t in found}))
    out = []
    for t in rows(found):
        t["assigner_name"] = names.get(t["assigner_account_id"])
        t["assignee_name"] = names.get(t["assignee_account_id"])
        out.append(t)
    return {"tasks": out}


@handler("task.get")
async def get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The task with its live verification stack and recent expectation signals."""
    require_account(ctx)
    task_id = int_field(payload, "task_id")
    task = await ctx.engine.db.tasks.get(task_id)
    if task is None or not await _can_view(ctx, task):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such task")
    if task["status"] != "completed" and task["verification_mode"] == "stack":
        task["items"] = await verification.evaluate_stack(ctx.engine, task_id)
    view = await _task_view(ctx.engine, ctx, task)
    view["expectations"] = rows(await ctx.engine.db.tasks.expectations(task_id))
    return {"task": view}


@handler("task.start")
async def start(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Assignee acknowledges start (the Client exception). Fires the 'task.started' Event."""
    ident = require_account(ctx)
    task_id = int_field(payload, "task_id")
    task = await ctx.engine.db.tasks.get(task_id)
    if task is None or task["assignee_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such task assigned to you")
    if task["status"] != "active":
        raise ProtocolError(ErrorCode.CONFLICT, f"task is {task['status']}")
    await ctx.engine.db.tasks.mark_started(task_id)
    await ctx.engine.audit.record(ctx, "task.started", target_type="tasks", target_id=task_id)
    await ctx.engine.push_to_account(task["assigner_account_id"], "task.started", {"task_id": task_id})
    from engine.control import events

    await events.on_signal(ctx.engine, ident.pc_id or 0, "task.started", {"task_id": task_id})
    return {"task_id": task_id, "status": "in_progress"}


@handler("task.verify")
async def verify(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Assigner only. {"task_id", "outcome": "complete"|"incomplete"} -- the whole task, never
    per item. The only path to 'completed'."""
    ident = require_account(ctx)
    task_id = int_field(payload, "task_id")
    outcome = str_field(payload, "outcome", choices=("complete", "incomplete"))
    task = await ctx.engine.db.tasks.get(task_id)
    if task is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such task")
    if task["assigner_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the assigner verifies")
    if task["status"] == "completed":
        raise ProtocolError(ErrorCode.CONFLICT, "task is already completed")
    await ctx.engine.db.tasks.record_manual_verification(task_id, ident.account_id, outcome)
    await ctx.engine.audit.record(ctx, "task.verified", target_type="tasks", target_id=task_id,
                                  detail={"outcome": outcome})
    if outcome == "complete":
        cancel_deadlines(ctx.engine, task_id)
        await ctx.engine.push_to_account(task["assignee_account_id"], "task.completed",
                                         {"task_id": task_id, "indicator": "task_completed"})
    else:
        await ctx.engine.push_to_account(task["assignee_account_id"], "task.incomplete", {"task_id": task_id})
    return {"task_id": task_id, "outcome": outcome,
            "status": "completed" if outcome == "complete" else task["status"]}


@handler("task.stack")
async def stack(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Re-evaluate and return the verification stack status (assigner's transparency view)."""
    require_account(ctx)
    task_id = int_field(payload, "task_id")
    task = await ctx.engine.db.tasks.get(task_id)
    if task is None or not await _can_view(ctx, task):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such task")
    return {"task_id": task_id, "items": rows(await verification.evaluate_stack(ctx.engine, task_id))}
