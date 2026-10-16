"""Detective from the shell: what a person seems to be trying to do, as cases with their evidence."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


@command("detective", usage="[noted] [status=open|explained|accepted|dismissed|escalated]", help_="The cases Detective has raised for you to see, strongest first")
async def detective(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"include_noted": "noted" in args.positional}
    if args.opt("status"):
        payload["status"] = args.opt("status")
    found = (await ctx.call("detective.cases", payload))["cases"]
    if not found:
        return "(no cases)"
    return table([{"id": c["id"], "machine": c["host"], "intent": c["intent"], "level": c["level"], "weight": f"{c['weight']:.2f}",
                   "stage": f"{c['stage_count']}/5 {c['stage_name'] or ''}".strip(), "status": c["status"], "last": c["last_at"]} for c in found],
                 ["id", "machine", "intent", "level", "weight", "stage", "status", "last"])


@command("detective", "case", "<id>", "One case: what it looks like, the story in order, each finding and what would make it innocent")
async def detective_case(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("detective.case", {"case_id": args.get_int(0, "id")})
    c = res["case"]
    out = [f"Case {c['id']} · {c['host']} · {c['intent']} · {c['level']} ({c['weight']:.2f}) · stage {c['stage_count']} of 5: {c['stage_name']}"
           + (f" · next: {c['next_stage']}" if c.get("next_stage") else ""), c["headline"]]
    if c.get("not_yet"):
        out.append(c["not_yet"])
    out.append("")
    out += [f"  {line}" for line in c["story"]]
    out.append("")
    for f in res["findings"]:
        out.append(f"- {f['behaviour']} ({f['weight']:.2f}): {f['summary']}")
        if f.get("why"):
            out.append(f"    because: {'; '.join(f['why'])}")
        out.append(f"    innocent if: {f['innocent']}")
    if c["status"] != "open":
        out.append(f"\nReviewed: {c['status']}" + (f" by {c['reviewed_by']}" if c.get("reviewed_by") else "") + (f" ({c['note']})" if c.get("note") else ""))
    return "\n".join(out)


@command("detective", "review", "<id> <explained|accepted|dismissed|escalated> [note...]", "Record what you made of a case; escalating tells the Super User")
async def detective_review(ctx: ShellContext, args: Args) -> str:
    await ctx.call("detective.review", {"case_id": args.get_int(0, "id"), "outcome": args.get(1, "outcome"), "note": args.rest(2, "note") if len(args.positional) > 2 else ""})
    return "recorded"


@command("detective", "overview", "", "What is open, by intent and level")
async def detective_overview(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("detective.overview")
    lv = res["by_level"]
    lines = [f"urgent {lv['urgent']} · cases {lv['case']} · noted {lv['noted']} · reviewed {res['reviewed']}"]
    lines += [f"  {n}  {intent}" for intent, n in sorted(res["by_intent"].items(), key=lambda kv: -kv[1])]
    return "\n".join(lines)
