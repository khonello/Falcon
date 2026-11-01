"""The Calendar page: what is coming, read from what the Engine already holds (the Task deadlines, the rules that run on a clock, the announcements
waiting to go out). Nothing here is written by the page and nothing is stored for it.

    calendar.board {days?}     what is coming in the next `days` (default 62, at most 124), soonest first:
                               {"now", "until", "items": [{"kind": "task" | "todo" | "rule" | "announcement", "at", "title", "line", "to": [page, sub]}]}

An Admin sees the tasks they were given or gave, the department's, the department tasks the Super User gave them, their own to-dos that have a date, the rules that run on a clock in their
department (a repeating one is drawn through the end of next month, so one daily rule does not fill the calendar to the horizon), and the announcements they
have scheduled. The Super User sees the department tasks they gave and every scheduled announcement. A task overdue is still listed, on the day it was due.
Flows are not here: they run on events, not a clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role

DEFAULT_DAYS = 62
MAX_DAYS = 124
MAX_ITEMS = 1500                      # a hard cap: a very busy calendar is cut, soonest kept


def _iso(t: datetime | None) -> str | None:
    return t.astimezone(timezone.utc).isoformat() if t is not None else None


def _end_of_next_month(now: datetime) -> datetime:
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return (nxt + timedelta(days=32)).replace(day=1)          # the first day after next month


def occurrences(spec: dict[str, Any], now: datetime, until: datetime) -> list[datetime]:
    """When a rule that runs on a clock will fire, as the Engine's scheduler reads it (UTC): `time.scheduled` once at `at`; `time.recurring` at `HH:MM`
    on the given weekdays (Monday is 0), or every day. A rule that repeats by an interval has no wall-clock times, so it has none here."""
    etype, m = spec.get("type"), spec.get("match") or {}
    out: list[datetime] = []
    if etype == "time.scheduled":
        try:
            at = datetime.fromisoformat(str(m.get("at")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return out
        at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        if now <= at < until:
            out.append(at)
    elif etype == "time.recurring" and ":" in str(m.get("at", "")):
        try:
            hh, mm = (int(x) for x in str(m["at"]).split(":", 1))
        except ValueError:
            return out
        days = m.get("days")
        day = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        while day < until:
            if day >= now and (not days or day.weekday() in days):
                out.append(day)
            day += timedelta(days=1)
    return out


def _task_title(t: dict[str, Any]) -> str:
    """A task has no title of its own: the first line of what was asked, kept short."""
    first = str(t.get("description_raw") or "").strip().splitlines()
    return (first[0][:80] if first else f"Task {t['id']}")


@handler("calendar.board")
async def board(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    days = max(1, min(int_field(payload, "days", required=False) or DEFAULT_DAYS, MAX_DAYS))
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days)
    db = ctx.engine.db
    items: list[dict[str, Any]] = []

    # --- tasks: the final deadline of what is not finished (the soft one when there is no final one), overdue ones on the day they were due
    if ident.role == "admin":
        mine = await db.tasks.list_for(ident.account_id, include_completed=False)
        dept = await db.tasks.list_department(ident.department_id, include_completed=False)
        seen: set[int] = set()
        people = await db.accounts.display_names_for(ident.account_id, sorted({t["assignee_account_id"] for t in mine + dept}))
        for t in mine + dept:
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            when = t.get("final_deadline_at") or t.get("soft_deadline_at")
            if when is None or when >= until:
                continue
            items.append({"kind": "task", "at": _iso(when), "title": _task_title(t), "line": people.get(t["assignee_account_id"]) or "Task", "to": ["tasks", str(t["id"])], "overdue": when < now})
    dept_tasks = await db.department_tasks.list(account_id=ident.account_id, include_completed=False) if ident.role == "admin" \
        else await db.department_tasks.list(department_id=None, include_completed=False)
    names = {d["id"]: d["name"] for d in await db.accounts.list_departments()}
    for t in dept_tasks:
        when = t["deadline_at"]
        if when is None or when >= until:
            continue
        line = "From the Super User" if ident.role == "admin" else names.get(t["department_id"], "A department")
        items.append({"kind": "task", "at": _iso(when), "title": t["title"], "line": line, "to": ["tasks", str(t["id"])], "overdue": when < now})

    # --- an Admin's own to-dos with a date (not done; overdue ones on the day they were due)
    if ident.role == "admin":
        for t in await db.todos.list(ident.account_id):
            when = t["due_at"]
            if when is None or when >= until:
                continue
            items.append({"kind": "todo", "at": _iso(when), "title": t["text"][:80], "line": "Your to-do", "to": ["tasks", "todos"], "overdue": when < now})

    # --- rules that run on a clock (an Admin's department only)
    if ident.role == "admin":
        horizon = min(until, _end_of_next_month(now))
        for d in await db.control.events_in_department(ident.department_id, enabled_only=True):
            spec = d["condition_spec"] or {}
            if not str(spec.get("type", "")).startswith("time."):
                continue
            actions = await db.control.actions_for_event(d["id"])
            for at in occurrences(spec, now, horizon):
                items.append({"kind": "rule", "at": _iso(at), "title": d.get("name") or "A rule that runs on a clock",
                              "line": f"{len(actions)} action{'' if len(actions) == 1 else 's'}", "to": ["automation", str(d["id"])], "overdue": False})

    # --- announcements waiting to go out
    for a in await db.alerts.sent(None if ident.role == "super_user" else ident.account_id):
        when = a.get("deliver_at")
        if when is None or a.get("delivered_at") or a.get("cancelled_at") or when < now or when >= until:
            continue
        items.append({"kind": "announcement", "at": _iso(when), "title": a.get("title") or str(a.get("body") or "")[:80], "line": "Goes out", "to": ["messages", "announcements"], "overdue": False})

    items.sort(key=lambda x: x["at"])
    return {"now": _iso(now), "until": _iso(until), "items": items[:MAX_ITEMS], "cut": len(items) > MAX_ITEMS}
