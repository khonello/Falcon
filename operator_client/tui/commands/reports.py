"""Reports and system alerts."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


@command("reports", help_="Reports you can see")
async def reports(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.list")
    return table(res["reports"], ["id", "category", "summary", "generated_at", "seen_at", "addressed_at"])


@command("report", "seen", "<report_id>[,<report_id>...]", "Mark reports seen by you (new -> seen, yours only)")
async def report_seen(ctx: ShellContext, args: Args) -> str:
    ids = [int(x) for x in args.get(0, "report_id").split(",") if x]
    res = await ctx.call("reports.seen", {"report_ids": ids})
    return f"seen now: {res['seen'] or 'none (already seen)'}"


@command("report", "mark", "<report_id>", "Mark a report addressed")
async def report_mark(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.mark", {"report_id": args.get_int(0, "report_id")})
    return f"addressed (view row {res['view_id']})"


@command("alerts", help_="Alerts delivered to you")
async def alerts(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("alerts.list"))["alerts"], ["id", "alert_type", "title", "from_name", "body", "deliver_at"], width=50)


@command("alerts", "sent", "", "What you have sent, scheduled or withdrawn ")
async def alerts_sent(ctx: ShellContext, args: Args) -> str:
    rows_ = (await ctx.call("alerts.sent"))["alerts"]
    return table(rows_, ["id", "alert_type", "status", "audience_label", "title", "body", "deliver_at"], width=40) if rows_ else "(nothing sent)"


@command("alerts", "cancel", "<id>", "Withdraw a scheduled announcement before it goes out")
async def alerts_cancel(ctx: ShellContext, args: Args) -> str:
    await ctx.call("alerts.cancel", {"alert_id": args.get_int(0, "id")})
    return "withdrawn"


@command("alert", None, "<emergency|warning|announcement|routine> <admin_only|department|all_users|specific_users> <body...> [title=<words>] [dept=<id>] [to=1,2] [at=<iso>] [link=<url>]",
         "Send an announcement now (or schedule it with at=)")
async def alert(ctx: ShellContext, args: Args) -> str:
    if len(args.positional) < 3:
        raise UsageError("type, audience and body are required")
    res = await ctx.call("alerts.create", {"type": args.positional[0], "audience": args.positional[1],
                                           "body": args.rest(2, "body"), "title": args.opt("title"), "department_id": args.opt_int("dept"),
                                           "account_ids": args.opt_ints("to"), "deliver_at": args.opt("at"),
                                           "action_link": args.opt("link")})
    return f"alert {res['alert_id']} " + (f"scheduled for {res['deliver_at']}" if res["deliver_at"] else "delivered")


@command("audit", usage="[n] [actor=<account_id>] [prefix=<action.>]", help_="Recent audit entries you may see")
async def audit(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("audit.recent", {"limit": int(args.positional[0]) if args.positional else 50,
                                          "actor_account_id": args.opt_int("actor"), "prefix": args.opt("prefix")})
    return table(res["entries"], ["occurred_at", "actor_name", "action_type", "target_type", "target_id", "detail"], width=60)


@command("expectations", help_="The raw log of system expectations that were not met (unresolved)")
async def expectations(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("audit.deviations"))["deviations"],
                 ["id", "expectation", "observed_account_id", "observed_pc_id", "detail", "detected_at"], width=50)
