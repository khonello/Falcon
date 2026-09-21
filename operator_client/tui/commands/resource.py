"""Resource: violations, resolve, tag."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


@command("violations", usage="[all]", help_="Resource violations you can see (`all` includes resolved)")
async def violations(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.violations", {"include_resolved": args.flag("all")})
    return table(res["violations"], ["id", "hostname", "path", "expected_tag", "detected_via", "detected_at",
                                     "resolved_at", "report_id"], width=50)


@command("violation", "resolve", "<violation_id>", "Mark a violation rectified; the file stops being ignored")
async def violation_resolve(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.resolve", {"violation_id": args.get_int(0, "violation_id")})
    ctx.state.clear_indicator(f"violation:{res['violation_id']}")
    return f"violation {res['violation_id']} resolved"


@command("tag", usage="<file_index_id> admin|restricted|worker_dept|common [dept=<id>]",
         help_="Classify an indexed file explicitly (admin tier: Super User only)")
async def tag(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.tag", {"file_index_id": args.get_int(0, "file_index_id"), "tag": args.get(1, "tag"),
                                          "scope_department_id": args.opt_int("dept")})
    return f"file {res['file_index_id']} tagged {res['tag']}"
