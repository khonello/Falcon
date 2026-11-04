"""What the console's pages do, from the shell: requests to talk, reminders, flows, a rule's runs, a machine's programs (ENGINE-GAPS #23)."""

from __future__ import annotations

from operator_client.tui.shell import Args, ShellContext, command


@command("task", "remind", "<task_id>", "Remind the person a late task was given to")
async def task_remind(ctx: ShellContext, args: Args) -> str:
    await ctx.call("task.remind", {"task_id": args.get_int(0, "task_id")})
    return "reminded"


@command("task", "help", "", "How to write a task")
async def task_help(ctx: ShellContext, args: Args) -> str:
    h = await ctx.call("task.help")
    parts = [f"  {x['name']}: {x['says']}" for x in h["parts"]]
    return "\n".join([h["title"], h["says"], *parts, "For example:", *[f"  {e}" for e in h["examples"]], h["cannot"]])


@command("chat", "requests", "", "Who at a machine is asking to talk")
async def chat_requests(ctx: ShellContext, args: Args) -> str:
    got = (await ctx.call("chat.requests"))["requests"]
    return "\n".join(f"{r['id']}  {r['from']} on {r['host']}: {r['line']}" for r in got) or "nobody is asking"


@command("chat", "accept", "<request_id>", "Accept a request to talk: the conversation opens with their line in it")
async def chat_accept(ctx: ShellContext, args: Args) -> str:
    got = await ctx.call("chat.request_accept", {"request_id": args.get_int(0, "request_id")})
    return f"conversation {got['conversation']['conversation_id']}"


@command("chat", "close", "<request_id> <why...>", "Close a request to talk, with a reason the person reads")
async def chat_close(ctx: ShellContext, args: Args) -> str:
    await ctx.call("chat.request_close", {"request_id": args.get_int(0, "request_id"), "why": args.rest(1, "why")})
    return "closed"


@command("flow", "remind", "<flow_id>", "Remind whoever must pick a folder for a waiting flow")
async def flow_remind(ctx: ShellContext, args: Args) -> str:
    return f"reminded {(await ctx.call('flow.remind', {'flow_id': args.get_int(0, 'flow_id')}))['reminded']}"


@command("flow", "keep", "<flow_id> new|both <path>", "Settle a file kept beside: keep only the new one, or both")
async def flow_keep(ctx: ShellContext, args: Args) -> str:
    await ctx.call("flow.keep", {"flow_id": args.get_int(0, "flow_id"), "keep": args.get(1, "new|both"), "path": args.rest(2, "path")})
    return "settled"


@command("flow", "start", "<flow_id>", "Start a stopped flow again")
async def flow_start(ctx: ShellContext, args: Args) -> str:
    return (await ctx.call("flow.start", {"flow_id": args.get_int(0, "flow_id")}))["flow"]["status"]


@command("update", "now", "<pc_id>", "Update a machine that is behind, now")
async def update_now(ctx: ShellContext, args: Args) -> str:
    return f"asked: version {(await ctx.call('update.now', {'pc_id': args.get_int(0, 'pc_id')}))['version']}"


@command("machine", "end", "<pc_id> <program>", "End a running program; the person is told")
async def machine_end(ctx: ShellContext, args: Args) -> str:
    return f"execution {(await ctx.call('machines.end_program', {'pc_id': args.get_int(0, 'pc_id'), 'name': args.rest(1, 'program')}))['execution_id']}"


@command("event", "again", "<event_id> <at>", "Run a firing again, only where it failed or timed out")
async def event_again(ctx: ShellContext, args: Args) -> str:
    got = await ctx.call("automation.run_again", {"event_id": args.get_int(0, "event_id"), "at": args.get(1, "at")})
    return f"{len(got['runs'])} run(s) started, {len(got['offline'])} machine(s) offline"


@command("event", "skip", "<event_id> <at> [undo]", "Skip one scheduled run, or take the skip back")
async def event_skip(ctx: ShellContext, args: Args) -> str:
    got = await ctx.call("automation.skip", {"event_id": args.get_int(0, "event_id"), "at": args.get(1, "at"), "undo": args.flag("undo")})
    return "skipped" if got["skipped"] else "not skipped"


@command("mark", "take-back", "<mark_id> <allowance_id>", "Take back an allowed copy: it is caught like any other again")
async def mark_take_back(ctx: ShellContext, args: Args) -> str:
    await ctx.call("marks.allow_revoke", {"mark_id": args.get_int(0, "mark_id"), "allowance_id": args.get_int(1, "allowance_id")})
    return "taken back"
