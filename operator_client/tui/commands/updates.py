"""Updates: approve (Super User, hard gate), rollout (Admin), health, prompt."""

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
        out += "\n\nPCs behind:\n" + table(res["pcs_behind"], ["pc_id", "hostname", "current_version_id"])
    return out


@command("update", "approve", "<version>", "Approve version N+1 (refused until every PC is confirmed on N)")
async def update_approve(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("updates.approve", {"version": args.get(0, "version")})
    return f"version {res['version']} approved (id {res['version_id']})"


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
