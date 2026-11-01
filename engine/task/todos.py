"""An Admin's own to-dos (the user, 29 Oct 2026; ENGINE-GAPS #17).

Version 1 has nobody above the Admins, so what came from them on the Admin's pages became the Admin's own: a line of text, when it is due,
when it was done. Not a kind of Task -- no checks, no assignee, no seen or ongoing, no verification. Only its owner sees it, adds it,
ticks it and takes the tick back.

    todo.list {done_days?}            the caller's: what is not done (soonest due first, no date last), then what was done in the last
                                      `done_days` (default 7, 0 for none); `strip` is what the strip across the console shows: not done,
                                      due within a day or past its date
    todo.add  {text, due_at?}         a new one
    todo.done {todo_id, done?}        tick it (done true, the default) or take the tick back (done false)

"Not now" on the strip is the console's own and needs nothing from here. Pushes `todo.changed` to the owner's other consoles.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.isotime import parse_iso
from engine.permissions import int_field, require_role, str_field
from engine.serialize import row
from protocol import ErrorCode, ProtocolError

TEXT_MAX = 300
OPEN_MAX = 500                        # a hard cap on to-dos not done, per owner: past it, adding says so
DONE_DAYS_DEFAULT = 7
DONE_DAYS_MAX = 90
STRIP_WITHIN = timedelta(days=1)


def _due(payload: dict[str, Any]) -> datetime | None:
    raw = payload.get("due_at")
    if raw in (None, ""):
        return None
    try:
        when = parse_iso(str(raw))
    except ValueError as exc:
        raise ProtocolError(ErrorCode.INVALID, "due_at must be ISO 8601") from exc
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _view(t: dict[str, Any], now: datetime) -> dict[str, Any]:
    view = row(t) or {}
    due = t["due_at"]
    view["done"] = t["done_at"] is not None
    view["overdue"] = t["done_at"] is None and due is not None and due < now
    view["on_strip"] = t["done_at"] is None and due is not None and due < now + STRIP_WITHIN
    return view


@handler("todo.list")
async def todo_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    days = int_field(payload, "done_days", required=False)
    days = DONE_DAYS_DEFAULT if days is None else max(0, min(days, DONE_DAYS_MAX))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days) if days else None
    todos = [_view(t, now) for t in await ctx.engine.db.todos.list(ident.account_id, done_since=since)]
    return {"todos": todos, "open": sum(1 for t in todos if not t["done"]),
            "strip": [t for t in todos if t["on_strip"]]}


@handler("todo.add")
async def todo_add(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    text = " ".join(str_field(payload, "text").split())
    if not text:
        raise ProtocolError(ErrorCode.INVALID, "a to-do needs a line of text")
    if len(text) > TEXT_MAX:
        raise ProtocolError(ErrorCode.INVALID, f"a to-do is one line, at most {TEXT_MAX} characters")
    due = _due(payload)
    db = ctx.engine.db
    if await db.todos.open_count(ident.account_id) >= OPEN_MAX:
        raise ProtocolError(ErrorCode.CONFLICT, f"you have {OPEN_MAX} to-dos not done; tick some off before adding more")
    made = await db.todos.add(ident.account_id, text, due)
    await ctx.engine.audit.record(ctx, "todo.added", target_type="todos", target_id=made["id"],
                                  detail={"due_at": due.isoformat() if due else None})
    view = _view(made, datetime.now(timezone.utc))
    await ctx.engine.push_to_account(ident.account_id, "todo.changed", {"todo_id": made["id"], "done": False})
    return {"todo": view}


@handler("todo.done")
async def todo_done(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    todo_id = int_field(payload, "todo_id")
    done = payload.get("done", True)
    if not isinstance(done, bool):
        raise ProtocolError(ErrorCode.INVALID, "done must be true or false")
    db = ctx.engine.db
    # Someone else's to-do is not there at all, to its non-owner.
    if await db.todos.get(todo_id, ident.account_id) is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such to-do")
    updated = await db.todos.set_done(todo_id, ident.account_id, done)
    assert updated is not None
    await ctx.engine.audit.record(ctx, "todo.done" if done else "todo.undone", target_type="todos", target_id=todo_id)
    await ctx.engine.push_to_account(ident.account_id, "todo.changed", {"todo_id": todo_id, "done": done})
    return {"todo": _view(updated, datetime.now(timezone.utc))}
