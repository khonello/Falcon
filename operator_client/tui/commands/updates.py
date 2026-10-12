"""Updates: approve (Super User, hard gate), stage, rollout (Admin), the gate, retry, leave out, health, prompt."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


@command("updates", help_="Current approved version and rollout health")
async def updates(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("updates.rollout_health")
    v = res.get("version")
    out = f"current version: {v['version_string'] if v else '(none approved)'}\n"
    out += table(res["departments"], ["department_name", "pcs", "current", "pending", "escalated"])
    if res.get("pcs_behind"):
        out += "\n\nPCs behind:\n" + table(res["pcs_behind"],
                                             ["pc_id", "hostname", "current_version_id", "failures", "escalated"])
    return out


@command("update", "approve", "<version> [leave_out=<pc>,<pc>] [reason=...]",
         "Approve version N+1 (refused until every PC is confirmed on N, but the ones you leave out, with a reason)")
async def update_approve(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"version": args.get(0, "version")}
    if args.opt("leave_out"):
        payload["leave_out"] = [int(x) for x in args.opt("leave_out").split(",") if x]
        payload["reason"] = args.opt("reason") or ""
    res = await ctx.call("updates.approve", payload)
    return f"version {res['version']} approved (id {res['version_id']})" + (f", leaving out pcs {res['left_out']}" if res.get("left_out") else "")


@command("update", "stage", "<version> [note...]", "Say a version is ready and waits for approval (Super User)")
async def update_stage(ctx: ShellContext, args: Args) -> str:
    payload = {"version": args.get(0, "version")}
    if len(args.positional) > 1:
        payload["note"] = args.rest(1, "note")
    res = await ctx.call("updates.stage", payload)
    return f"{res['version']} is ready for approval" + (" (it already was)" if res["was_staged"] else "")


def _when(iso: str | None) -> str:
    return (iso or "")[:16].replace("T", " ") or "-"


@command("gate", help_="The rollout gate: the current version, who holds the next one back, adoption")
async def gate(ctx: ShellContext, args: Args) -> str:
    g = await ctx.call("rollout.gate")
    cur, nxt, s = g["current"], g["next"], g["strip"]
    out = [f"current {cur['version'] if cur else '(none)'}" + (f", approved {_when(cur['approved_at'])} by {cur['approved_by']}" if cur else "")
           + f" | next {nxt['version'] if nxt else 'none waiting'} | running it {s['running']}/{s['total']} | holding {s['holding']} | left out {s['left_out']} | failed installs this week {s['failed_installs']}"]
    if g["holding"]:
        out.append(table([{"machine": h["hostname"], "state": h["state"], "running": h["running"] or "?", "attempts": h["attempts"], "last error": h["last_error"] or "-",
                           "next try": h["next_try"], "escalated": h["escalated_to"] or "-"} for h in g["holding"]],
                         ["machine", "state", "running", "attempts", "last error", "next try", "escalated"]))
    if g["adoption"]:
        out += ["\nrunning the current version, by day:", table([{"day": d["day"], "machines": d["n"], "joined": ", ".join(d["joined"]) or "-", "": d["note"] or ""} for d in g["adoption"]], ["day", "machines", "joined", ""])]
    out.append("can be approved now" if g["can_approve"] else "")
    return "\n".join(x for x in out if x)


@command("update", "retry", "<pc_id> [now]", "Tell a machine behind to try its update when idle (or now)")
async def update_retry(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("updates.retry", {"pc_id": args.get_int(0, "pc_id"), "when": "now" if "now" in args.positional[1:] else "idle"})
    return f"asked pc {res['pc_id']} to try {res['version']} {res['when']}"


@command("update", "leave-out", "<pc_id> <reason...>", "The coming approval does not wait for this machine (Super User)")
async def update_leave_out(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("updates.leave_out", {"pc_id": args.get_int(0, "pc_id"), "reason": args.rest(1, "reason")})
    return f"pc {res['pc_id']} is left out of the gate"


@command("update", "take-back", "<pc_id>", "Put a machine back in the gate (Super User)")
async def update_take_back(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("updates.take_back", {"pc_id": args.get_int(0, "pc_id")})
    return f"pc {res['pc_id']} is back in the gate" if res["was_left_out"] else f"pc {res['pc_id']} was not left out"


@command("update", "rollout", "[dept=<id>]", "Roll the approved version out to your department's PCs")
async def update_rollout(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("updates.rollout_department", {"department_id": args.opt_int("dept")})
    if not res["targeted"]:
        return f"everything is already on {res['version']}"
    return f"rolling out {res['version']} to:\n" + table(res["targeted"], ["pc_id", "hostname"])


@command("update", "prompt", "<department_id> [message...]", "Nudge a department's Admins about a stalled rollout")
async def update_prompt(ctx: ShellContext, args: Args) -> str:
    message = " ".join(args.positional[1:]) or None
    res = await ctx.call("updates.prompt_admin", {"department_id": args.get_int(0, "department_id"), "message": message})
    return f"department {res['department_id']} prompted"
