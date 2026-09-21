"""Control / Events / Monitoring / Actions: the action library (incl. Custom Actions validated
here before sending), events, manual runs, executions, terminate, and the dashboard."""

from __future__ import annotations

from pathlib import Path

from common.custom_actions import validate
from operator_client.tui.render import bullet, kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


@command("actions", help_="The action library: built-in types and your department's stored actions")
async def actions(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.action_list")
    out = ["built-in:"]
    out.append(bullet(f"{k} ({v['category']}) params: {', '.join(v['params']) or '-'}" for k, v in res["builtin"].items()))
    for kind in ("control", "monitoring", "custom"):
        out.append(f"\n{kind}:")
        out.append(table(res["actions"][kind], ["id", "name", "builtin_type", "params", "timeout_seconds", "timing",
                                                "custom_script_language"], width=40))
    return "\n".join(out)


@command("action", "add", "<control|monitoring> <builtin_type> [timeout=<s>] [name=..] [delay=<s>] [<param>=<value> ...]",
         "Create a built-in action")
async def action_add(ctx: ShellContext, args: Args) -> str:
    kind = args.get(0, "control|monitoring")
    builtin = args.get(1, "builtin_type")
    reserved = {"timeout", "name", "delay", "desc"}
    params = {k: v for k, v in args.options.items() if k not in reserved}
    timing = {"mode": "delayed", "delay_s": int(args.opt("delay"))} if args.opt("delay") else None  # type: ignore[arg-type]
    res = await ctx.call("control.action_create", {"kind": kind, "builtin_type": builtin, "params": params,
                                                  "timeout_s": int(args.opt("timeout", "60") or 60),
                                                  "name": args.opt("name"), "description": args.opt("desc"),
                                                  "timing": timing})
    return f"action {res['action']['id']} '{res['action']['name']}' created"


@command("action", "custom", "<name> python|powershell <script-file> [timeout=<s>] [delay=<s>] [desc=..]",
         "Create a Custom Action from a script file -- validated locally first (stdlib + Windows-native only)")
async def action_custom(ctx: ShellContext, args: Args) -> str:
    name = args.get(0, "name")
    language = args.get(1, "python|powershell")
    path = Path(args.get(2, "script-file"))
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UsageError(f"cannot read {path}: {exc}") from exc
    result = validate(language, source)
    if not result.ok:
        return "script rejected before sending:\n" + bullet(result.problems)
    timing = {"mode": "delayed", "delay_s": int(args.opt("delay"))} if args.opt("delay") else None  # type: ignore[arg-type]
    res = await ctx.call("control.action_create", {"kind": "custom", "name": name, "language": language, "script": source,
                                                  "timeout_s": int(args.opt("timeout", "60") or 60),
                                                  "description": args.opt("desc"), "timing": timing})
    return f"custom action {res['action']['id']} '{name}' created ({len(source.splitlines())} lines)"


@command("action", "rm", "<action_id>", "Archive an action")
async def action_rm(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.action_delete", {"action_id": args.get_int(0, "action_id")})
    return f"action {res['action_id']} archived"


@command("action", "run", "<action_id> <pc_id>", "Run an action now on a PC")
async def action_run(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.action_run", {"action_id": args.get_int(0, "action_id"), "pc_id": args.get_int(1, "pc_id")})
    return f"execution {res['execution_id']}" if res.get("execution_id") else "scheduled (delayed action)"


@command("events", help_="Event definitions with their attached actions")
async def events(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.event_list")
    rows = [{"id": e["id"], "type": e["condition_spec"].get("type"), "mechanism": e["condition_type"],
             "enabled": e["enabled"], "pcs": e["condition_spec"].get("pc_ids") or "dept",
             "match": e["condition_spec"].get("match"), "actions": [a["name"] or a["id"] for a in e["actions"]],
             "last_fired": e.get("last_fired_at")} for e in res["events"]]
    return table(rows, width=36) + "\n\ntypes: " + ", ".join(sorted(res["types"]))


@command("event", "add", "<type> [actions=1,2] [pcs=3,4] [match_<key>=<value> ...] [disabled]",
         "Define an event; e.g. event add file.modified actions=5 match_path_prefix=C:/resources/restricted")
async def event_add(ctx: ShellContext, args: Args) -> str:
    match = {k[6:]: _coerce(v) for k, v in args.options.items() if k.startswith("match_")}
    res = await ctx.call("control.event_create", {"type": args.get(0, "type"), "action_ids": args.opt_ints("actions") or [],
                                                 "pc_ids": args.opt_ints("pcs"), "match": match,
                                                 "enabled": not args.flag("disabled")})
    return f"event {res['event']['id']} ({res['event']['condition_type']}) created"


def _coerce(v: str):
    try:
        return int(v)
    except ValueError:
        return v


@command("event", "enable", "<event_id>", "Enable an event")
async def event_enable(ctx: ShellContext, args: Args) -> str:
    await ctx.call("control.event_update", {"event_id": args.get_int(0, "event_id"), "enabled": True})
    return "enabled"


@command("event", "disable", "<event_id>", "Disable an event (never deleted)")
async def event_disable(ctx: ShellContext, args: Args) -> str:
    await ctx.call("control.event_delete", {"event_id": args.get_int(0, "event_id")})
    return "disabled"


@command("event", "actions", "<event_id> <action_ids,...>", "Replace the actions attached to an event (order = display)")
async def event_actions(ctx: ShellContext, args: Args) -> str:
    ids = [int(x) for x in args.get(1, "action_ids").split(",") if x]
    res = await ctx.call("control.event_update", {"event_id": args.get_int(0, "event_id"), "action_ids": ids})
    return f"event {res['event']['id']} actions: " + ", ".join(str(a["id"]) for a in res["event"]["actions"])


@command("dashboard", help_="Operational view: enabled automations, last fired, recent executions, live runs")
async def dashboard(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.dashboard")
    lines = ["ENABLED AUTOMATIONS:"]
    for auto in res["automations"]:
        ev = auto["event"]
        lines.append(f"\nEvent {ev['id']}: {ev['condition_spec'].get('type')}  (last: {auto['last_fired_at'] or 'never'})")
        for a in auto["actions"]:
            act = a["action"]
            last = a["recent"][0] if a["recent"] else None
            status = f"{last['status'].upper()}" + (f" ({last['terminated_reason']})" if last and last.get("terminated_reason") else "") if last else "never run"
            lines.append(f"  ├─ {act.get('name') or act.get('builtin_type')} [{act['action_kind']}] -> {status}")
            for chunk in (last or {}).get("output", [])[-3:]:
                lines.append(f"  │     {chunk}")
    lines.append("\nLIVE:")
    lines.append(table(res["live"], ["id", "action_id", "builtin_type", "target_pc_id", "started_at"]))
    return "\n".join(lines)


@command("exec", usage="<execution_id>", help_="One execution with its output tail")
async def exec_(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.execution", {"execution_id": args.get_int(0, "execution_id")})
    return kv(res["execution"]) + "\n\noutput:\n" + ("\n".join(res["output"]) or "(none)")


@command("terminate", usage="<execution_id>", help_="Stop a running action by execution id")
async def terminate(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("control.terminate", {"execution_id": args.get_int(0, "execution_id")})
    return f"termination requested for execution {res['execution_id']}"


@command("validate", usage="python|powershell <script-file>", help_="Validate a script locally without sending it")
async def validate_cmd(ctx: ShellContext, args: Args) -> str:
    language = args.get(0, "python|powershell")
    path = Path(args.get(1, "script-file"))
    result = validate(language, path.read_text(encoding="utf-8"))
    return "ok" if result.ok else "problems:\n" + bullet(result.problems)


