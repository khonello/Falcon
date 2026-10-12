"""The Automation and Actions pages: rules with how they fired and how their runs ended, the library with its runs, a test on one machine.

    automation [days=7]                       the rules: what they watch for and do, fired, last run, problems; runs per day by outcome
    action board [days=7]                     the action library: used by, runs, problems, last run
    runs [action=<id>] [event=<id>] [hand]    recent runs, how each ended
    event test <event_id> <pc_id>             run a rule's actions once on one machine
"""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


def _days(rows: list[dict]) -> str:
    return table([{"day": d["day"], "success": d["Success"], "failed": d["Failed"], "timed out": d["Timed out"], "stopped": d["Stopped by you"]} for d in rows],
                 ["day", "success", "failed", "timed out", "stopped"])


@command("automation", usage="[days=7]", help_="Rules: what they watch for and do, how often they fired, how their runs ended")
async def automation(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("automation.board", {"days": args.opt_int("days") or 7})
    s = r["strip"]
    rows = [{"id": x["event_id"], "rule": x["name"], "on": "on" if x["on"] else "off", "by": x["owner"] or "?" + (" (read only)" if x["read_only"] else ""), "fired": x["fired"],
             "last run": x["last_run"] or "-", "problems": x["problems"]} for x in r["rules"]]
    head = f"{s['rules']} rules, {s['on']} on, fired {s['fired']}, {s['problems']} problems"
    return head + "\n" + (table(rows, ["id", "rule", "on", "by", "fired", "last run", "problems"], width=40) if rows else "(no rules)") + "\n\nruns per day:\n" + _days(r["days"])


@command("action", "board", "[days=7]", "The action library: used by, runs, problems, last run")
async def action_board(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("actions.board", {"days": args.opt_int("days") or 7})
    s = r["strip"]
    rows = [{"id": a["action_id"], "action": a["name"], "kind": a["kind"], "used by": f"{len(a['used_by'])} rule(s)" if a["used_by"] else "no rules", "runs": a["runs"],
             "problems": a["problems"], "limit": f"{a['timeout_s']}s", "last": a["last_run"]["outcome"] if a["last_run"] else "not run yet"} for a in r["actions"]]
    head = f"{s['actions']} actions ({s['control']} control, {s['monitoring']} monitoring, {s['custom']} custom), {s['runs']} runs ({s['by_hand']} by hand), {s['problems']} problems"
    return head + "\n" + (table(rows, ["id", "action", "kind", "used by", "runs", "problems", "limit", "last"], width=36) if rows else "(no actions)")


@command("runs", usage="[action=<id>] [event=<id>] [hand]", help_="Recent runs: when, where, how each ended, what set it off")
async def runs(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"hand": "hand" in args.positional}
    for k, key in (("action", "action_id"), ("event", "event_id")):
        if args.opt(k):
            payload[key] = args.opt_int(k)
    r = await ctx.call("actions.runs", payload)
    rows = [{"run": x["run_id"], "action": x["action"], "where": x["host"] or "?", "at": (x["at"] or "")[:16].replace("T", " "), "took": f"{x['took_s']}s" if x["took_s"] is not None else "-",
             "outcome": x["outcome"], "said": x["summary"] or "-", "by": x["by"]} for x in r["runs"]]
    return f"{r['total']} runs\n" + (table(rows, ["run", "action", "where", "at", "took", "outcome", "said", "by"], width=34) if rows else "")


@command("event", "test", "<event_id> <pc_id>", "Run a rule's actions once on one machine")
async def event_test(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("control.event_test", {"event_id": args.get_int(0, "event_id"), "pc_id": args.get_int(1, "pc_id")})
    return f"ran {len(r['runs'])} action(s) once on pc {r['pc_id']}: executions {', '.join(str(x['execution_id']) for x in r['runs'])}"
