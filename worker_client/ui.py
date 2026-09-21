"""The narrow Client UI (Hierarchy -> Client): view/start/monitor assigned tasks, Assistance
search and ping, alerts, and the BLOCKED surface -- deliberately a small command set, not the
Operator Client's. Built on the same `common.cli` machinery.

`python -m worker_client --ui` runs it in the same process as the service; pushes print live.
"""

from __future__ import annotations

from typing import Any

from common.cli import Args, Registry, UsageError, make_command_decorator, parse
from common.connection import ConnectionError_, EngineError
from common.render import kv, table
from worker_client.service import WorkerService

registry = Registry()
command = make_command_decorator(registry)


class UIContext:
    def __init__(self, service: WorkerService) -> None:
        self.service = service
        self.scratch: dict[str, Any] = {}
        self.quit_requested = False

    async def call(self, type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.service.call(type_, payload)


@command("status", help_="Connection, your identity, block state, watcher and executions")
async def status(ctx: UIContext, args: Args) -> str:
    s = ctx.service
    ident = s.identity
    data = {"engine": s.config.engine_address, "connected": bool(s.conn and s.conn.connected),
            "account_id": ident.account_id if ident else None, "pc_id": ident.pc_id if ident else None,
            "native_session": s.native_session_id, "blocked": s.lockout.is_blocked,
            "watcher": f"{s.watcher.mode} ({s.watcher.events_reported} events, {s.watcher.sweeps_completed} sweeps)",
            "executions_running": list(s.executor.running), "pending_update": s.updater.pending}
    out = kv(data)
    if s.lockout.blocked_by:
        b = s.lockout.blocked_by
        out += f"\n\n*** THIS PC IS OCCUPIED BY {b.get('occupant_name')} ({b.get('occupant_role')}) -- TRAVERSAL IN PROGRESS ***"
    return out


@command("tasks", help_="Tasks assigned to you")
async def tasks(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("task.list")
    return table(res["tasks"], ["id", "status", "assigner_name", "description_raw", "final_deadline_at"], width=50)


@command("task", None, "<task_id>", "A task with its verification stack status (you cannot verify)")
async def task_get(ctx: UIContext, args: Args) -> str:
    t = (await ctx.call("task.get", {"task_id": args.get_int(0, "task_id")}))["task"]
    out = kv(t, skip=("items", "expectations", "manual_verification", "assignee_pc_id", "assignee_department_id"))
    out += "\n\nverification stack:\n" + table(t["items"], ["sequence", "target_type", "intent", "proposed_filename",
                                                            "program_name", "status"])
    return out


@command("task", "start", "<task_id>", "Acknowledge that you have started")
async def task_start(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("task.start", {"task_id": args.get_int(0, "task_id")})
    await ctx.service._refresh_tasks()
    return f"task {res['task_id']} {res['status']}"


@command("search", usage="<query...>", help_="Search files you are permitted to see")
async def search(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("assistance.search", {"query": args.rest(0, "query")})
    return table(res["results"], ["pc_id", "path", "resource_tag", "last_seen_at"], width=60)


@command("ping", usage="<admin_account_id>", help_="Ping your Admin for attention (repeatable)")
async def ping(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("assistance.ping", {"to_account_id": args.get_int(0, "admin_account_id")})
    return f"ping {res['ping_id']} sent -- your Admin sees a pulsing indicator until they respond"


@command("pings", help_="Pings waiting for YOUR response (an Admin may ping you for information)")
async def pings(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("assistance.ping_status")
    return f"{res['unaddressed']} unaddressed\n" + table(res["pings"], ["id", "from_name", "sent_at"])


@command("respond", usage="<ping_id>", help_="Respond to an Admin's ping")
async def respond(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("assistance.respond", {"ping_id": args.get_int(0, "ping_id")})
    ctx.scratch["channel"] = res["channel_id"]
    return f"channel {res['channel_id']}; turn: {res['turn']}"


@command("msg", usage="[channel_id] <text...>", help_="Post one message (one per turn)")
async def msg(ctx: UIContext, args: Args) -> str:
    if args.positional and args.positional[0].isdigit():
        channel_id, text = int(args.positional[0]), args.rest(1, "text")
    else:
        channel_id, text = ctx.scratch.get("channel"), args.rest(0, "text")
    if channel_id is None:
        raise UsageError("no channel yet -- give the channel id")
    res = await ctx.call("assistance.message", {"channel_id": channel_id, "body": text})
    ctx.scratch["channel"] = channel_id
    return f"sent; now the {res['turn']}'s turn"


@command("channel", usage="[channel_id]", help_="Show the conversation")
async def channel(ctx: UIContext, args: Args) -> str:
    channel_id = int(args.positional[0]) if args.positional else ctx.scratch.get("channel")
    if channel_id is None:
        raise UsageError("no channel yet")
    res = await ctx.call("assistance.channel", {"channel_id": channel_id})
    ctx.scratch["channel"] = channel_id
    names = res["channel"].get("names", {})
    state = "closed" if res["channel"].get("closed_at") else ("your turn" if res["channel"].get("my_turn") else "waiting")
    return f"channel {channel_id} -- {state}\n" + ("\n".join(
        f"{m['sent_at'][11:16]}  {names.get(str(m['sender_account_id']), m['sender_account_id'])}: {m['body']}"
        for m in res["messages"]) or "(no messages)")


@command("channels", help_="Your channels")
async def channels(ctx: UIContext, args: Args) -> str:
    return table((await ctx.call("assistance.channels"))["channels"], ["id", "superior_account_id", "turn", "closed_at"])


@command("alerts", help_="Alerts delivered to you")
async def alerts(ctx: UIContext, args: Args) -> str:
    return table((await ctx.call("alerts.list"))["alerts"], ["id", "alert_type", "body", "action_link", "deliver_at"], width=50)


@command("violations", help_="Resource violations surfaced to you (files being ignored until you fix them)")
async def violations(ctx: UIContext, args: Args) -> str:
    return table((await ctx.call("resource.violations"))["violations"],
                 ["id", "filename", "expected_tag", "detected_at", "path"], width=70)


@command("violation", "resolve", "<violation_id>", "I removed the file -- stop ignoring it")
async def violation_resolve(ctx: UIContext, args: Args) -> str:
    res = await ctx.call("resource.resolve", {"violation_id": args.get_int(0, "violation_id")})
    return f"violation {res['violation_id']} resolved"


@command("sweep", help_="Run the full index sweep now (normally waits for idle)")
async def sweep(ctx: UIContext, args: Args) -> str:
    n = await ctx.service.watcher.sweep()
    return f"reported {n} entries"


@command("help", usage="[command]", help_="Commands")
async def help_(ctx: UIContext, args: Args) -> str:
    rows = [{"command": c.full, "usage": c.usage, "what": c.help}
            for c in sorted(registry.commands.values(), key=lambda c: c.full)]
    return table(rows, ["command", "usage", "what"], width=60)


@command("quit", help_="Exit the UI (the service keeps running if started separately)")
async def quit_(ctx: UIContext, args: Args) -> str:
    ctx.quit_requested = True
    return "bye"


async def run_line(ctx: UIContext, line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    try:
        positional, args = parse(line)
    except ValueError as exc:
        return f"parse error: {exc}"
    found = registry.resolve(positional)
    if found is None:
        return f"unknown command {positional[0]!r} -- try: help"
    cmd, consumed = found
    args.positional = args.positional[consumed:]
    try:
        out = await cmd.handler(ctx, args)
        return out if out is not None else ""
    except UsageError as exc:
        return f"usage: {cmd.full} {cmd.usage}\n  {exc}"
    except EngineError as exc:
        return f"{exc.code}: {exc.message}"
    except ConnectionError_ as exc:
        return f"connection: {exc}"


def describe(type_: str, p: dict[str, Any]) -> str | None:
    """Pushes worth a line in the worker's UI."""
    if type_ == "session.blocked":
        return f"*** {p.get('occupant_name')} ({p.get('occupant_role')}) has entered this PC -- BLOCKED until {str(p.get('deadline_at',''))[11:16]} ***"
    if type_ == "session.released":
        return "*** this PC is yours again ***"
    if type_ == "task.assigned":
        return f"new task {p.get('task_id')} assigned to you -- `task {p.get('task_id')}`"
    if type_ == "task.deadline":
        return f"DEADLINE ({p.get('kind')}) reached for task {p.get('task_id')}"
    if type_ == "task.completed":
        return f"task {p.get('task_id')} was verified complete"
    if type_ == "task.incomplete":
        return f"task {p.get('task_id')} was verified incomplete -- keep going"
    if type_ == "assistance.ping":
        return f"PING from {p.get('from_name')} -- `respond {p.get('ping_id')}`"
    if type_ == "assistance.channel_opened":
        return f"your Admin responded: channel {p.get('channel_id')} open"
    if type_ == "assistance.message":
        return f"[channel {p.get('channel_id')}] {p.get('body')}"
    if type_ == "alert.delivered":
        return f"ALERT [{p.get('alert_type')}] {p.get('body')}"
    if type_ == "resource.violation":
        return f"RESOURCE VIOLATION: {p.get('message')}"
    if type_ == "action.execute":
        return f"running action {p.get('action', {}).get('name') or p.get('action', {}).get('builtin_type')} (execution {p.get('execution_id')})"
    if type_ == "update.available":
        return f"update {p.get('version')} available; it will install when you are idle"
    return None


async def run_ui(service: WorkerService) -> None:
    from prompt_toolkit import PromptSession, print_formatted_text
    from prompt_toolkit.completion import NestedCompleter
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.patch_stdout import patch_stdout

    ctx = UIContext(service)

    async def notify(type_: str, payload: dict[str, Any]) -> None:
        text = describe(type_, payload)
        if text:
            print_formatted_text(FormattedText([("#8ab4f8", f"  » {text}")]))

    service.on_notify(notify)

    def toolbar() -> str:
        s = service
        who = f" Worker · pc {s.identity.pc_id} " if s.identity else " not connected "
        if s.lockout.blocked_by:
            return who + f"  ‼ BLOCKED by {s.lockout.blocked_by.get('occupant_name')} -- traversal in progress"
        return who + f"  watcher: {s.watcher.mode}  running: {len(s.executor.running)}"

    session: PromptSession[str] = PromptSession(completer=NestedCompleter.from_nested_dict(registry.completions()),
                                                bottom_toolbar=toolbar, refresh_interval=1.0)
    print_formatted_text("Falcon Worker Client -- type `help`")
    with patch_stdout():
        while not ctx.quit_requested:
            try:
                line = await session.prompt_async("worker> ")
            except (EOFError, KeyboardInterrupt):
                break
            out = await run_line(ctx, line)
            if out:
                print_formatted_text(out)


