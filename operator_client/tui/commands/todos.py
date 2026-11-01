"""An Admin's own to-dos (ENGINE-GAPS #17): a line, when it is due, when it was done. Yours alone.

    todo add [due=<when>] <text...>     a new one
    todo done <todo_id>                 tick it
    todo undo <todo_id>                 take the tick back
    todos [all]                         what is not done (all: with the last week's done ones)
"""

from __future__ import annotations

from operator_client.core.deadlines import resolve_phrase
from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


def _line(t: dict) -> str:
    state = "done" if t["done"] else "overdue" if t["overdue"] else "open"
    return f"to-do {t['id']} '{t['text']}': {state}" + (f", due {t['due_at']}" if t["due_at"] else "")


@command("todo", "add", "[due=<when>] <text...>", "Add a to-do of your own (no checks, no one else sees it)")
async def todo_add(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"text": args.rest(0, "text")}
    if args.opt("due"):
        when = resolve_phrase(args.opt("due"))
        if when is None:
            raise UsageError("due=<when> is an ISO date/time, or a phrase like 'friday 17:00'")
        payload["due_at"] = when.isoformat()
    return _line((await ctx.call("todo.add", payload))["todo"])


@command("todo", "done", "<todo_id>", "Tick one of your to-dos")
async def todo_done(ctx: ShellContext, args: Args) -> str:
    return _line((await ctx.call("todo.done", {"todo_id": args.get_int(0, "todo_id"), "done": True}))["todo"])


@command("todo", "undo", "<todo_id>", "Take the tick back")
async def todo_undo(ctx: ShellContext, args: Args) -> str:
    return _line((await ctx.call("todo.done", {"todo_id": args.get_int(0, "todo_id"), "done": False}))["todo"])


@command("todos", help_="Your to-dos (all: with the ones done in the last week)")
async def todos(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("todo.list", {"done_days": 7 if args.positional and args.positional[0] == "all" else 0})
    rows_ = [{"id": t["id"], "text": t["text"], "due": t["due_at"] or "", "state": "done" if t["done"] else "overdue" if t["overdue"] else ""}
             for t in res["todos"]]
    out = table(rows_, ["id", "text", "due", "state"], width=50) if rows_ else "(none)"
    return out + (f"\n{len(res['strip'])} due within a day or past its date" if res["strip"] else "")
