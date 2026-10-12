"""Search (Ctrl K) from the shell: `find <text>` looks for a machine, person, task, flow, issue, rule or department."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


@command("find", None, "<text...> [kind=machine|person|task|flow|issue|rule|department]", "Find a machine, person, task, flow, issue, rule or department")
async def find(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"q": " ".join(args.positional)}
    if args.opt("kind"):
        payload["kinds"] = [args.opt("kind")]
    rows = (await ctx.call("search.find", payload))["results"]
    return table([{"kind": r["kind"], "id": r["id"], "found": r["title"], "about": r["sub"], "opens": r["page"]} for r in rows], ["kind", "id", "found", "about", "opens"]) if rows else "nothing found"
