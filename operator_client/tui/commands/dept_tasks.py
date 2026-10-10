"""Department tasks: what the Super User gives a department (ENGINE-GAPS #16). Not an Admin's task to a Worker
(commands/task.py, which keeps its checks).

    dtask give <department_id> due=<when> [admins=1,2] <title...>   Super User: tell every Admin (or the ones picked)
    dtask mark <task_id> seen|ongoing|done                          Admin: your own row
    dtask complete <task_id>                                        Super User who gave it
    dtask reopen <task_id> <note...>                                Super User who gave it: back to ongoing, every Admin sees the note
    dtasks [all]                                                    your department tasks (all: with the completed ones)
    dtask <task_id>                                                 one, with who has got where
"""

from __future__ import annotations

from operator_client.core.deadlines import resolve_phrase
from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


def _line(t: dict) -> str:
    return f"task {t['id']} '{t['title']}' for {t['department_name']}: {t['standing']}, due {t['deadline_at']}"


@command("dtask", "give", "<department_id> due=<when> [admins=1,2] <title...>",
         "Give a department a task: no checks, one deadline; every Admin in it is told unless you pick some")
async def dtask_give(ctx: ShellContext, args: Args) -> str:
    department = args.get_int(0, "department_id")
    title = args.rest(1, "title")
    when = resolve_phrase(args.opt("due"))
    if when is None:
        raise UsageError("due=<when> is required (an ISO date/time, or a phrase like 'friday 17:00')")
    payload: dict = {"department_id": department, "title": title, "deadline_at": when.isoformat()}
    if args.opt("admins"):
        payload["admin_ids"] = [int(x) for x in args.opt("admins").split(",") if x]  # type: ignore[union-attr]
    res = await ctx.call("task.dept_create", payload)
    return _line(res["task"]) + f"\ntold {res['task']['told']} Admin(s)"


@command("dtask", "mark", "<task_id> seen|ongoing|done", "Mark a department task (your own state; the Super User completes it)")
async def dtask_mark(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("task.dept_mark", {"task_id": args.get_int(0, "task_id"), "state": args.get(1, "seen|ongoing|done")})
    return _line(res["task"]) + f"\nyou: {res['task']['my_state']}"


@command("dtask", "complete", "<task_id>", "Complete a department task you gave (only you can)")
async def dtask_complete(ctx: ShellContext, args: Args) -> str:
    return _line((await ctx.call("task.dept_complete", {"task_id": args.get_int(0, "task_id")}))["task"])


@command("dtask", "reopen", "<task_id> <note...>", "Send a department task back as ongoing, with a note every Admin on it sees")
async def dtask_reopen(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("task.dept_reopen", {"task_id": args.get_int(0, "task_id"), "note": args.rest(1, "note")})
    return _line(res["task"])


@command("dtasks", help_="Department tasks: the Super User's (all of them) or the ones you were told")
async def dtasks(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("task.dept_list", {"include_completed": bool(args.positional and args.positional[0] == "all")})
    rows_ = [{"id": t["id"], "department": t["department_name"], "title": t["title"], "standing": t["standing"],
              "you": t.get("my_state", ""), "due": t["deadline_at"]} for t in res["tasks"]]
    out = table(rows_, ["id", "department", "title", "standing", "you", "due"], width=40) if rows_ else "(none)"
    return out + (f"\n{res['unseen']} not yet seen by you" if res.get("unseen") else "")


@command("dtask", None, "<task_id>", "A department task: who has got where, and the notes sent with it")
async def dtask_get(ctx: ShellContext, args: Args) -> str:
    t = (await ctx.call("task.dept_get", {"task_id": args.get_int(0, "task_id")}))["task"]
    out = [_line(t)]
    out.append(table([{"admin": a["name"] or a["account_id"], "state": a["state"], "since": a["state_at"]} for a in t["admins"]],
                     ["admin", "state", "since"]))
    out.extend(f"note ({n['by']}, {n['at']}): {n['text']}" for n in t["notes"])
    return "\n".join(out) + "\n" + kv({"told": t["told"], "given by": t["assigner_name"]})
