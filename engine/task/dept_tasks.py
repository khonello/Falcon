"""Department tasks: what the Super User gives a department (task-natural-combo.md; ENGINE-GAPS #16).

A different thing from an Admin's task to a Worker (engine/task/tasks.py), which keeps its verification stack:

  * no checks and no expectations -- such work is rarely a file or a program
  * given to a DEPARTMENT: every Admin in it is told by default, or only the ones the Super User picks
  * one deadline
  * each Admin marks it seen, ongoing or done (their own row only); the task STANDS at the furthest any of them has got
  * only the Super User who gave it calls it complete, or sends it back as ongoing with a note every Admin on it sees

    task.dept_create {department_id, title, deadline_at, admin_ids?}      Super User
    task.dept_mark   {task_id, state: seen|ongoing|done}                  an Admin who was told
    task.dept_complete {task_id}                                          the Super User who gave it
    task.dept_reopen {task_id, note}                                      the Super User who gave it
    task.dept_list   {department_id?, include_completed?}                 Super User: all; Admin: the ones they were told
    task.dept_get    {task_id}

Pushes (`task.dept_assigned`, `task.dept_updated`, `task.dept_completed`, `task.dept_reopened`, `task.dept_deadline`)
go to the Admins told and to the Super User, so a console can show the strip across every page until the task is seen.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from engine.serialize import row
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

STATES = ("seen", "ongoing", "done")
RANK = {"told": 0, "seen": 1, "ongoing": 2, "done": 3}
TITLE_MAX = 200
NOTE_MAX = 1000


def standing(states: list[str]) -> str:
    """Where the task stands: the furthest any Admin told has got ('told' while none has marked it)."""
    return max(states, key=RANK.__getitem__) if states else "told"


def _job_name(task_id: int) -> str:
    return f"dept_task.{task_id}.deadline"


def schedule_deadline(engine: Engine, task: dict[str, Any]) -> None:
    engine.scheduler.at(_job_name(task["id"]), task["deadline_at"], _deadline_job(engine, task["id"]))


def _deadline_job(engine: Engine, task_id: int) -> Any:
    async def fire() -> None:
        task = await engine.db.department_tasks.get(task_id)
        if task is None or task["completed_at"] is not None:
            return
        from engine.control import events

        admins = await engine.db.department_tasks.admins([task_id])
        await engine.audit.record(None, "task.dept_deadline", target_type="department_tasks", target_id=task_id)
        payload = {"task_id": task_id, "kind": "final", "indicator": "deadline_reached"}
        await engine.push_to_account(task["assigner_account_id"], "task.dept_deadline", payload)
        for a in admins:
            await engine.push_to_account(a["account_id"], "task.dept_deadline", payload)
            acct = await engine.db.accounts.by_id(a["account_id"])
            await events.on_signal(engine, (acct or {}).get("bound_pc_id") or 0, "task.deadline_final",
                                   {"dept_task_id": task_id})
    return fire


async def reschedule_all(engine: Engine) -> int:
    """Engine start: re-arm every open department task's deadline from the database."""
    if not engine.db.connected:
        return 0
    open_tasks = await engine.db.department_tasks.open_tasks()
    for task in open_tasks:
        schedule_deadline(engine, task)
    return len(open_tasks)


def _parse_deadline(payload: dict[str, Any]) -> datetime:
    raw = payload.get("deadline_at")
    if not raw:
        raise ProtocolError(ErrorCode.INVALID, "a department task needs a deadline")
    try:
        when = datetime.fromisoformat(str(raw))
    except ValueError as exc:
        raise ProtocolError(ErrorCode.INVALID, "deadline_at must be ISO 8601") from exc
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


async def _view(ctx: Context, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tasks as the caller sees them. The Super User sees every Admin's state; an Admin sees the task, where it
    stands, and only their own row (what a colleague marked is not theirs to read). Names are the caller's."""
    ident = ctx.identity
    db = ctx.engine.db
    ids = [t["id"] for t in tasks]
    admins = await db.department_tasks.admins(ids) if ids else []
    notes = await db.department_tasks.notes(ids) if ids else []
    people = {t["assigner_account_id"] for t in tasks} | {a["account_id"] for a in admins} | {n["by_account_id"] for n in notes}
    names = await db.accounts.display_names_for(ident.account_id, sorted(people)) if people else {}
    out = []
    for t in tasks:
        mine = [a for a in admins if a["task_id"] == t["id"]]
        view = row(t) or {}
        view["assigner_name"] = names.get(t["assigner_account_id"])
        view["standing"] = "complete" if t["completed_at"] is not None else standing([a["state"] for a in mine])
        view["told"] = len(mine)
        view["notes"] = [{"text": n["text"], "at": row(n)["at"], "by": names.get(n["by_account_id"])}
                         for n in notes if n["task_id"] == t["id"]]
        rows_ = mine if ident.role == "super_user" else [a for a in mine if a["account_id"] == ident.account_id]
        view["admins"] = [{"account_id": a["account_id"], "name": names.get(a["account_id"]), "state": a["state"],
                           "state_at": row(a)["state_at"], "seen_at": row(a)["seen_at"]} for a in rows_]
        if ident.role == "admin":
            view["my_state"] = view["admins"][0]["state"] if view["admins"] else None
        out.append(view)
    return out


@handler("task.dept_create")
async def dept_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"department_id", "title", "deadline_at", "admin_ids"?}. Every Admin in the department is told unless the
    Super User picks some. A department with no Admin cannot be given a task: there is no one to tell."""
    ident = require_role(ctx, "super_user")
    db = ctx.engine.db
    department_id = int_field(payload, "department_id")
    if department_id not in {d["id"] for d in await db.accounts.list_departments()}:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such department")
    title = " ".join(str_field(payload, "title").split())[:TITLE_MAX]
    if not title:
        raise ProtocolError(ErrorCode.INVALID, "a department task needs a title")
    deadline = _parse_deadline(payload)
    in_dept = [a for a in await db.accounts.active_admins() if a["department_id"] == department_id]
    picked = payload.get("admin_ids")
    if picked is None:
        told = [a["id"] for a in in_dept]
    else:
        if not isinstance(picked, list) or not picked:
            raise ProtocolError(ErrorCode.INVALID, "admin_ids must be a non-empty list, or leave it out for every Admin")
        told = sorted({int(i) for i in picked})
        if stray := set(told) - {a["id"] for a in in_dept}:
            raise ProtocolError(ErrorCode.INVALID, f"{sorted(stray)} are not Admins of that department")
    if not told:
        raise ProtocolError(ErrorCode.CONFLICT, "that department has no Admin to tell yet")
    task_id = await db.department_tasks.create(department_id, ident.account_id, title, deadline, told)
    task = await db.department_tasks.get(task_id)
    assert task is not None
    schedule_deadline(ctx.engine, task)
    await ctx.engine.audit.record(ctx, "task.dept_created", target_type="department_tasks", target_id=task_id,
                                  detail={"department_id": department_id, "told": told, "deadline_at": deadline.isoformat()})
    for admin_id in told:
        await ctx.engine.push_to_account(admin_id, "task.dept_assigned",
                                         {"task_id": task_id, "title": title, "deadline_at": deadline.isoformat()})
    return {"task": (await _view(ctx, [task]))[0]}


@handler("task.dept_mark")
async def dept_mark(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"task_id", "state": "seen"|"ongoing"|"done"}. An Admin who was told, on their own row. A completed task
    takes no more marks; the Super User may send it back."""
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    task_id = int_field(payload, "task_id")
    state = str_field(payload, "state", choices=STATES)
    task = await db.department_tasks.get(task_id)
    if task is None or not any(a["account_id"] == ident.account_id for a in await db.department_tasks.admins([task_id])):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such task for you")
    if task["completed_at"] is not None:
        raise ProtocolError(ErrorCode.CONFLICT, "the Super User has already completed this task")
    await db.department_tasks.mark(task_id, ident.account_id, state)
    await ctx.engine.audit.record(ctx, "task.dept_marked", target_type="department_tasks", target_id=task_id,
                                  detail={"state": state})
    view = (await _view(ctx, [await db.department_tasks.get(task_id) or task]))[0]
    names = await db.accounts.display_names_for(task["assigner_account_id"], [ident.account_id])
    await ctx.engine.push_to_account(task["assigner_account_id"], "task.dept_updated",
                                     {"task_id": task_id, "state": state, "by_account_id": ident.account_id,
                                      "by_name": names.get(ident.account_id), "standing": view["standing"]})
    return {"task": view}


async def _own_as_assigner(ctx: Context, task_id: int) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    task = await ctx.engine.db.department_tasks.get(task_id)
    if task is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such department task")
    if task["assigner_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the Super User who gave this task closes or reopens it")
    return task


@handler("task.dept_complete")
async def dept_complete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"task_id"}. Only the Super User who gave it. It does not need every Admin to have said done: the call is theirs."""
    task = await _own_as_assigner(ctx, int_field(payload, "task_id"))
    if task["completed_at"] is not None:
        raise ProtocolError(ErrorCode.CONFLICT, "already completed")
    db = ctx.engine.db
    await db.department_tasks.complete(task["id"])
    ctx.engine.scheduler.cancel(_job_name(task["id"]))
    await ctx.engine.audit.record(ctx, "task.dept_completed", target_type="department_tasks", target_id=task["id"])
    for a in await db.department_tasks.admins([task["id"]]):
        await ctx.engine.push_to_account(a["account_id"], "task.dept_completed", {"task_id": task["id"], "title": task["title"]})
    return {"task": (await _view(ctx, [await db.department_tasks.get(task["id"]) or task]))[0]}


@handler("task.dept_reopen")
async def dept_reopen(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"task_id", "note"}. Only the Super User who gave it: the task goes back to ongoing for every Admin who had
    finished, with a note every Admin on it sees. Works on a completed task and on one an Admin marked done."""
    task = await _own_as_assigner(ctx, int_field(payload, "task_id"))
    note = str_field(payload, "note").strip()[:NOTE_MAX]
    if not note:
        raise ProtocolError(ErrorCode.INVALID, "say what is still to do: a note is required")
    db = ctx.engine.db
    await db.department_tasks.send_back(task["id"], ctx.identity.account_id, note)
    fresh = await db.department_tasks.get(task["id"]) or task
    schedule_deadline(ctx.engine, fresh)
    await ctx.engine.audit.record(ctx, "task.dept_reopened", target_type="department_tasks", target_id=task["id"],
                                  detail={"note": note})
    for a in await db.department_tasks.admins([task["id"]]):
        await ctx.engine.push_to_account(a["account_id"], "task.dept_reopened",
                                         {"task_id": task["id"], "title": task["title"], "note": note})
    return {"task": (await _view(ctx, [fresh]))[0]}


@handler("task.dept_list")
async def dept_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The Super User: every department task (optionally one department's). An Admin: the ones they were told, with
    their own state. `unseen` is how many an Admin has not yet marked seen -- what the strip across their pages counts."""
    ident = require_role(ctx, "super_user", "admin")
    include = bool(payload.get("include_completed"))
    db = ctx.engine.db
    if ident.role == "super_user":
        dept = int_field(payload, "department_id", required=False)
        tasks = await db.department_tasks.list(department_id=dept, include_completed=include)
    else:
        tasks = await db.department_tasks.list(account_id=ident.account_id, include_completed=include)
    views = await _view(ctx, tasks)
    out = {"tasks": views}
    if ident.role == "admin":
        out["unseen"] = sum(1 for v in views if v["my_state"] == "told" and v["standing"] != "complete")
    return out


@handler("task.dept_get")
async def dept_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    task_id = int_field(payload, "task_id")
    task = await db.department_tasks.get(task_id)
    if task is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such department task")
    if ident.role == "admin" and not any(a["account_id"] == ident.account_id for a in await db.department_tasks.admins([task_id])):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such department task")
    return {"task": (await _view(ctx, [task]))[0]}
