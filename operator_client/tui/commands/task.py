"""Task: propose -> review/edit the working stack -> create; list/get/start/verify/stack.

The working stack lives in `ctx.scratch["task"]` between commands:
    task propose <assignee> <description...>   fills it from the Engine's proposal (+ flags)
    task items                                 shows it
    task item add file|program <intent> <name> [path=..] [link=<n>] [file=<file_index_id>]
    task item rm <n>
    task create [none] [soft=iso] [final=iso]  commits it (or an explicit None)
"""

from __future__ import annotations

from typing import Any

from operator_client.core.deadlines import resolve_phrase
from operator_client.tui.render import bullet, kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command

FILE_INTENTS = ("create", "update", "exists")
PROGRAM_INTENTS = ("used", "used_with_file", "installed_available", "closed_not_running")


def _work(ctx: ShellContext) -> dict[str, Any]:
    return ctx.scratch.setdefault("task", {"assignee": None, "description": "", "items": [], "soft": None, "final": None})


def _items_text(items: list[dict[str, Any]]) -> str:
    rows = [{"#": i + 1, "target": it["target_type"], "intent": it["intent"], "name": it["name"],
             "path": it.get("path"), "link": it.get("linked_item_index"), "file_index_id": it.get("file_index_id"),
             "by": it.get("populated_by")} for i, it in enumerate(items)]
    return table(rows, ["#", "target", "intent", "name", "path", "link", "file_index_id", "by"])


@command("task", "propose", "<assignee_account_id> <description...>",
         "Ask the Engine's local LLM to propose verification items + deadline; nothing is committed")
async def task_propose(ctx: ShellContext, args: Args) -> str:
    assignee = args.get_int(0, "assignee_account_id")
    description = args.rest(1, "description")
    res = await ctx.call("task.propose", {"description": description, "assignee_account_id": assignee})
    work = _work(ctx)
    phrase = res.get("final_deadline")
    resolved = resolve_phrase(phrase)
    work.update(assignee=assignee, description=description, soft=None,
                final=resolved.isoformat() if resolved else None,
                items=[{"target_type": i["target_type"], "intent": i["intent"], "name": i["name"], "path": i.get("path"),
                        "linked_item_index": i.get("linked_item_index"), "file_index_id": i.get("file_index_id"),
                        "populated_by": "llm"} for i in res["items"]])
    out = [f"proposal for account {assignee}" + ("" if res["llm_available"] else "  (local LLM unavailable -- manual editor)")]
    out.append(_items_text(work["items"]))
    if phrase and resolved:
        out.append(f"deadline (final): '{phrase}' -> {resolved.strftime('%Y-%m-%d %H:%M')}  (change with final=<iso>)")
    elif phrase:
        out.append(f"deadline (final): '{phrase}' -- could not resolve to a time; set final=<iso> on create")
    else:
        out.append("deadline (final): -")
    if res["flags"]:
        out.append("needs your decision:")
        out.append(bullet(_flag_text(f) for f in res["flags"]))
    if res["collisions"]:
        out.append("name collisions (give a path or a new name):")
        out.append(bullet(f"item {c['item_index'] + 1} {c['name']}: exists at " +
                          ", ".join(e["path"] for e in c["existing"]) for c in res["collisions"]))
    if res["proposed_split"]:
        out.append("this looks like more than one task -- proposed split (accept by creating each separately):")
        out.append(bullet(f"{p['description']}  targets={p.get('targets')}" for p in res["proposed_split"]))
    out.append("edit with `task item ...`, then `task create [soft=..] [final=..]` (or `task create none`)")
    return "\n".join(out)


def _flag_text(f: dict[str, Any]) -> str:
    kind = f.get("kind")
    if kind == "unclear":
        return f"unclear: {f.get('question')}"
    if kind == "ambiguous_deadline":
        return f"ambiguous deadline: {f.get('candidates')} -- set one with final=..."
    if kind == "contradiction":
        return f"contradiction: {f.get('detail')}"
    if kind == "no_target":
        return f"{f.get('ask')} -- confirm with `task create none`"
    if kind == "file_not_indexed":
        cands = ", ".join(f"{c['file_index_id']}={c['path']}" for c in f.get("candidates", [])) or "use `search <name>`"
        return f"item {f['item_index'] + 1}: {f.get('ask')}: {cands} -- then `task item file {f['item_index'] + 1} <file_index_id>`"
    return str(f)


@command("task", "items", "", "Show the working verification stack")
async def task_items(ctx: ShellContext, args: Args) -> str:
    w = _work(ctx)
    return (f"assignee {w['assignee']}: {w['description'] or '(no description)'}\n" + _items_text(w["items"]) +
            f"\ndeadlines: soft={w['soft'] or '-'} final={w['final'] or '-'}")


@command("task", "item", "add file|program <intent> <name> [path=..] [link=<n>] [file=<id>]  |  rm <n>  |  file <n> <file_index_id>",
         "Edit the working stack (the manual [+ item] editor)")
async def task_item(ctx: ShellContext, args: Args) -> str:
    w = _work(ctx)
    op = args.get(0, "add|rm")
    if op == "rm":
        n = args.get_int(1, "n")
        if not 1 <= n <= len(w["items"]):
            raise UsageError("no such item")
        w["items"].pop(n - 1)
        return _items_text(w["items"])
    if op == "file":
        n, fid = args.get_int(1, "n"), args.get_int(2, "file_index_id")
        if not 1 <= n <= len(w["items"]):
            raise UsageError("no such item")
        w["items"][n - 1]["file_index_id"] = fid
        return _items_text(w["items"])
    if op != "add":
        raise UsageError("expected add, rm or file")
    target = args.get(1, "file|program")
    intent = args.get(2, "intent")
    name = args.get(3, "name")
    allowed = FILE_INTENTS if target == "file" else PROGRAM_INTENTS if target == "program" else ()
    if intent not in allowed:
        raise UsageError(f"{target} intents: {', '.join(allowed) or 'file or program'}")
    link = args.opt_int("link")
    w["items"].append({"target_type": target, "intent": intent, "name": name, "path": args.opt("path"),
                       "linked_item_index": link - 1 if link else None, "file_index_id": args.opt_int("file"),
                       "populated_by": "manual"})
    return _items_text(w["items"])


def _deadline_arg(value: str | None, name: str) -> str | None:
    """Accept ISO 8601 or a resolvable phrase ("friday 3pm", "tomorrow"); refuse the rest."""
    if not value:
        return None
    resolved = resolve_phrase(value)
    if resolved is None:
        raise UsageError(f"{name}= must be ISO 8601 or a plain phrase like 'friday 5pm' (got {value!r})")
    return resolved.isoformat()


@command("task", "create", "[none] [assignee=<id>] [desc=<text>] [soft=<iso>] [final=<iso>]",
         "Commit the working stack as a task, or `none` for an explicit no-verification task")
async def task_create(ctx: ShellContext, args: Args) -> str:
    w = _work(ctx)
    assignee = args.opt_int("assignee") or w["assignee"]
    description = args.opt("desc") or w["description"]
    if assignee is None or not description:
        raise UsageError("propose first, or give assignee=<id> desc=<text>")
    none = args.flag("none")
    soft = _deadline_arg(args.opt("soft") or w["soft"], "soft")
    final = _deadline_arg(args.opt("final") or w["final"], "final")
    payload: dict[str, Any] = {"assignee_account_id": assignee, "description": description,
                               "verification_mode": "none" if none else "stack", "confirm_none": none,
                               "items": [] if none else w["items"],
                               "soft_deadline_at": soft, "final_deadline_at": final}
    if not none and not w["items"]:
        raise UsageError("the stack is empty -- add items, or create with `none` to confirm no verification")
    res = await ctx.call("task.create", payload)
    ctx.scratch.pop("task", None)
    t = res["task"]
    return f"task {t['id']} created for {t['assignee_name']} ({t['status']}, verification {t['verification_mode']})"


@command("tasks", usage="[all]", help_="Tasks you assigned / are assigned (`all` includes completed)")
async def tasks(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("task.list", {"include_completed": args.flag("all")})
    return table(res["tasks"], ["id", "status", "assigner_name", "assignee_name", "description_raw",
                                "verification_mode", "final_deadline_at"], width=48)


@command("task", None, "<task_id>", "Show a task with its verification stack and expectation signals")
async def task_get(ctx: ShellContext, args: Args) -> str:
    res = (await ctx.call("task.get", {"task_id": args.get_int(0, "task_id")}))["task"]
    out = kv(res, skip=("items", "expectations", "manual_verification"))
    out += "\n\nverification stack:\n" + table(res["items"], ["sequence", "target_type", "intent", "proposed_filename",
                                                              "program_name", "file_path", "status"])
    if res.get("manual_verification"):
        out += "\n\nmanual verification:\n" + kv(res["manual_verification"])
    if res.get("expectations"):
        out += "\n\nrecent signals:\n" + table(res["expectations"][:10], ["observed_at", "signal_type", "value"], width=60)
    return out


@command("task", "stack", "<task_id>", "Re-evaluate and show the stack status")
async def task_stack(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("task.stack", {"task_id": args.get_int(0, "task_id")})
    return table(res["items"], ["sequence", "target_type", "intent", "proposed_filename", "program_name", "status"])


@command("task", "start", "<task_id>", "Acknowledge start (assignee)")
async def task_start(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("task.start", {"task_id": args.get_int(0, "task_id")})
    return f"task {res['task_id']} {res['status']}"


@command("task", "verify", "<task_id> complete|incomplete", "Manual verification of the whole task (assigner only)")
async def task_verify(ctx: ShellContext, args: Args) -> str:
    outcome = args.get(1, "complete|incomplete")
    res = await ctx.call("task.verify", {"task_id": args.get_int(0, "task_id"), "outcome": outcome})
    ctx.state.clear_indicator(f"task:{res['task_id']}")
    return f"task {res['task_id']} verified {res['outcome']} -> {res['status']}"
