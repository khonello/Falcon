"""Reports & routing, the Super-User-only addressed View, and system alerts."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


@command("reports", help_="Reports you can see: everything (Super User) or your routed pane (Admin)")
async def reports(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.list")
    return table(res["reports"], ["id", "category", "source_table", "source_id", "generated_at", "addressed_at"])


@command("report", "mark", "<report_id>", "Mark a routed report addressed (Admin); Super User's copy is untouched")
async def report_mark(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.mark", {"report_id": args.get_int(0, "report_id")})
    return f"addressed (view row {res['view_id']})"


@command("routing", help_="Report routing configuration (Super User)")
async def routing(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.routing_get")
    return "categories: " + ", ".join(res["categories"]) + "\n\n" + table(res["routing"], ["category", "department_name",
                                                                                          "routed_department_id", "configured_at"])


@command("routing", "set", "<category> [dept_ids,...]", "Route a report category to departments (empty = none)")
async def routing_set(ctx: ShellContext, args: Args) -> str:
    ids = [int(x) for x in args.positional[1].split(",") if x] if len(args.positional) > 1 else []
    res = await ctx.call("reports.routing_set", {"category": args.get(0, "category"), "department_ids": ids})
    return f"{res['category']} -> departments {res['department_ids'] or 'none (Super User only)'}"


@command("addressed", help_="The Super-User-only View: who addressed which report, when")
async def addressed(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.addressed_view")
    return table(res["addressed"], ["report_id", "category", "addressed_by_account_id", "addressed_by_department_id", "addressed_at"])


@command("alerts", help_="Alerts delivered to you")
async def alerts(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("alerts.list"))["alerts"], ["id", "alert_type", "audience", "body", "action_link", "deliver_at"], width=50)


@command("alert", None, "<emergency|warning|announcement|routine> <admin_only|department|all_users|specific_users> <body...> [dept=<id>] [to=1,2] [at=<iso>] [link=<url>]",
         "Send a system alert now (or schedule it with at=)")
async def alert(ctx: ShellContext, args: Args) -> str:
    if len(args.positional) < 3:
        raise UsageError("type, audience and body are required")
    res = await ctx.call("alerts.create", {"type": args.positional[0], "audience": args.positional[1],
                                           "body": args.rest(2, "body"), "department_id": args.opt_int("dept"),
                                           "account_ids": args.opt_ints("to"), "deliver_at": args.opt("at"),
                                           "action_link": args.opt("link")})
    return f"alert {res['alert_id']} " + (f"scheduled for {res['deliver_at']}" if res["deliver_at"] else "delivered")




@command("audit", usage="[n] [actor=<account_id>] [prefix=<action.>]", help_="Recent audit entries you may see")
async def audit(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("audit.recent", {"limit": int(args.positional[0]) if args.positional else 50,
                                          "actor_account_id": args.opt_int("actor"), "prefix": args.opt("prefix")})
    return table(res["entries"], ["occurred_at", "actor_name", "action_type", "target_type", "target_id", "detail"], width=60)


@command("deviations", help_="System expectation deviations (unresolved)")
async def deviations(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("audit.deviations"))["deviations"],
                 ["id", "expectation", "observed_account_id", "observed_pc_id", "detail", "detected_at"], width=50)
