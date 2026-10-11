"""Issues: the tickets an Admin works.

    issues [type=..] [mine|unassigned]       open and waiting issues, worst first, and what is waiting on you
    issue <id>                               what it means, its facts, what you can do, its timeline
    issue act <id> <key> [reason=..] [message=..] [pick=<n>]    do one of the things offered
    issue take <id> | give <id> <account> | free <id>           take it, give it to an Admin, hand it back
    issue escalate <id> [note..]             an Admin sends it up to the Super User
    issue note <id> <text...>                a line in its timeline
"""

from __future__ import annotations

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, command


@command("issues", usage="[type=file|update|deviation|flow|offline] [mine|unassigned]",
         help_="Open and waiting issues, worst first")
async def issues_list(ctx: ShellContext, args: Args) -> str:
    payload: dict = {}
    if args.opt("type"):
        payload["type"] = args.opt("type")
    if args.positional and args.positional[0] in ("mine", "unassigned"):
        payload["owner"] = "me" if args.positional[0] == "mine" else "unassigned"
    res = await ctx.call("issues.list", payload)
    s = res["summary"]
    rows = [{"id": i["id"], "code": i["code"], "severity": i["severity"], "what": f"{i['title']}: {i['subject']}".strip(": "),
             "machine": i["host"] or "", "owner": (i["owner"] or {}).get("name") or "unassigned", "state": i["label"],
             "age": f"{i['age_hours']:.1f}h" + (" PAST TARGET" if i["past_target"] else "")} for i in res["issues"]]
    head = (f"{s['open']} open, {s['waiting']} waiting, {s['past_target']} past target, {s['done_today']} done today; "
            f"{s['mine']} waiting on you")
    return head + "\n\n" + (table(rows, ["id", "code", "severity", "what", "machine", "owner", "state", "age"], width=48) if rows else "(nothing)")


@command("issue", None, "<id>", "One issue: what it means, its facts, what you can do, its timeline")
async def issue_get(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("issues.get", {"issue_id": args.get_int(0, "id")})
    i = res["issue"]
    out = [f"{i['code']}  {i['severity']}  {i['title']}  [{i['label']}]", res["lead"], kv({k: v for k, v in res["facts"]})]
    if res["options"]:
        out.append("\ncan do:")
        out.extend(f"  {o['key']:<8} {o['title']}" + (f"  (needs a {o['need']})" if o.get("need") else "") for o in res["options"])
    out.extend(f"  not now: {w}" for w in res["why"])
    out.append("\ntimeline:")
    out.extend(f"  {e['at'][:16].replace('T', ' ')}  {e['who']}: {e['what']}" for e in res["timeline"])
    return "\n".join(out)


@command("issue", "act", "<id> <key> [reason=..] [message=..] [pick=<n>]", "Do one of the things an issue offers")
async def issue_act(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"issue_id": args.get_int(0, "id"), "key": args.get(1, "key")}
    for k in ("reason", "message"):
        if args.opt(k):
            payload[k] = args.opt(k)
    if args.opt("pick"):
        payload["pick"] = args.opt_int("pick")
    res = await ctx.call("issues.act", payload)
    return f"{res['issue']['code']}: {res['issue']['label']}"


@command("issue", "take", "<id>", "Take an issue yourself")
async def issue_take(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("issues.assign", {"issue_id": args.get_int(0, "id")})
    return f"{res['issue']['code']} is yours"


@command("issue", "give", "<id> <account_id>", "Give an issue to an Admin")
async def issue_give(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("issues.assign", {"issue_id": args.get_int(0, "id"), "account_id": args.get_int(1, "account_id")})
    return f"{res['issue']['code']} is now {res['issue']['owner']['name']}'s"


@command("issue", "free", "<id>", "Hand an issue back (unassigned)")
async def issue_free(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("issues.assign", {"issue_id": args.get_int(0, "id"), "account_id": None})
    return f"{res['issue']['code']} is unassigned"


@command("issue", "escalate", "<id> [note...]", "Send an issue up to the Super User")
async def issue_escalate(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("issues.escalate", {"issue_id": args.get_int(0, "id"), "note": args.rest(1, "note") if len(args.positional) > 1 else ""})
    return f"{res['issue']['code']} sent up"


@command("issue", "note", "<id> <text...>", "Add a line to an issue's timeline")
async def issue_note(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("issues.note", {"issue_id": args.get_int(0, "id"), "text": args.rest(1, "text")})
    return f"{len(res['timeline'])} lines in its timeline"
