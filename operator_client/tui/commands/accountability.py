"""Rules and Accountability.

    rules                                     the standard: built-in (locked) rules and the Super User's, with this week's deviations
    rule <id>                                 one rule
    rule library                              the patterns to start from
    rule add never <trigger> name=..          Super User: a rule that must never be broken
    rule add follow <trigger> <expect> within=<minutes> name=..
    rule add limit <reading> n=<n> per=hour|day|week name=..
        (all: [who=admins|workers|machines|everyone|depts] [report=no] [admin=yes] [severity=..])
    rule on|off <id>                          switch an organisation rule on or off (a built-in cannot be)
    rule try <id> [within=<m>|n=<n>]          what a changed line would have done to the last month
    deviations [kind=..] [open] [group=rule|department|subject]
    deviation <id>                            the record, its timeline and its evidence
    deviation outcome <id> explained|accepted|escalated|dismissed|open [note...]
"""

from __future__ import annotations

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


def _spec(args: Args, shape: str) -> dict:
    spec: dict = {"who": args.opt("who") or ("admins" if shape != "never" else "everyone"), "resp": {
        "report": (args.opt("report") or "yes") != "no", "admin": (args.opt("admin") or "no") == "yes"}}
    if args.opt("severity"):
        spec["severity"] = args.opt("severity")
    return spec


@command("rules", help_="The standard: built-in (locked) rules and the Super User's, with this week's deviations")
async def rules(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("rules.list")
    s = res["summary"]
    rows = [{"id": r["id"], "code": r["code"], "rule": r["name"], "shape": r["shape"], "on": "locked" if r["locked"] else ("on" if r["on"] else "off"),
             "applies to": r["scope"], "this week": r["deviations_this_week"]} for r in res["rules"]]
    return (f"{s['rules']} rules, {s['on']} on: {s['broken_this_week']} broken this week, {s['kept']} kept\n\n"
            + table(rows, ["id", "code", "rule", "shape", "on", "applies to", "this week"], width=44))


@command("rule", None, "<id>", "One rule, in a sentence")
async def rule_get(ctx: ShellContext, args: Args) -> str:
    r = (await ctx.call("rules.get", {"rule_id": args.get_int(0, "id")}))["rule"]
    return kv({"rule": f"{r['code']} {r['name']}", "says": r["sentence"], "applies to": r["scope"], "set by": r["set_by"],
               "on": "always (built in)" if r["locked"] else r["on"], "this week": f"{r['deviations_this_week']} deviations, {r['open_this_week']} open",
               "when broken": ", ".join(k for k, v in r["spec"]["resp"].items() if v and k != "action_id") or "record it"})


@command("rule", "library", help_="The patterns to start from")
async def rule_library(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("rules.library")
    return table([{"key": p["key"], "pattern": p["name"], "says": p["sentence"]} for p in res["patterns"]], ["key", "pattern", "says"], width=70)


@command("rule", "add", "never <trigger> | follow <trigger> <expect> within=<m> | limit <reading> n=<n> per=<period>  name=.. [who=..] [report=no] [admin=yes]",
         "Create an organisation-wide rule (Super User)")
async def rule_add(ctx: ShellContext, args: Args) -> str:
    shape = args.get(0, "never|follow|limit")
    payload: dict = {"shape": shape, "name": args.opt("name") or f"{shape} rule", **_spec(args, shape)}
    if shape == "never":
        payload["trigger"] = args.get(1, "trigger")
    elif shape == "follow":
        payload.update(trigger=args.get(1, "trigger"), expect=args.get(2, "expect"), within=args.opt_int("within"))
    elif shape == "limit":
        payload.update(reading=args.get(1, "reading"), limit={"n": args.opt_int("n") or 0, "per": args.opt("per") or "week"})
    else:
        raise UsageError("shape is never, follow or limit")
    r = (await ctx.call("rules.create", payload))["rule"]
    return f"{r['code']} '{r['name']}': {r['sentence']}"


@command("rule", "on", "<id>", "Switch an organisation rule on")
async def rule_on(ctx: ShellContext, args: Args) -> str:
    r = (await ctx.call("rules.switch", {"rule_id": args.get_int(0, "id"), "on": True}))["rule"]
    return f"{r['code']} is on"


@command("rule", "off", "<id>", "Switch an organisation rule off (new deviations stop; old ones stay)")
async def rule_off(ctx: ShellContext, args: Args) -> str:
    r = (await ctx.call("rules.switch", {"rule_id": args.get_int(0, "id"), "on": False}))["rule"]
    return f"{r['code']} is off"


@command("rule", "try", "<id> within=<minutes> | n=<count>", "What a changed line would have done to the last month's deviations")
async def rule_try(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"rule_id": args.get_int(0, "id")}
    if args.opt("within"):
        payload["within"] = args.opt_int("within")
    if args.opt("n"):
        payload["limit"] = {"n": args.opt_int("n")}
    r = await ctx.call("rules.try", payload)
    return f"{r['deviations']} deviations in the last 30 days: {r['would_clear']} would not have been, {r['would_remain']} still would"


@command("deviations", usage="[kind=pc|worker|admin|dept] [open] [group=rule|department|subject]", help_="Accountability: departures from the rules")
async def deviations(ctx: ShellContext, args: Args) -> str:
    payload: dict = {}
    for k in ("kind", "group"):
        if args.opt(k):
            payload[k] = args.opt(k)
    if "open" in args.positional:
        payload["outcome"] = "open"
    res = await ctx.call("deviations.list", payload)
    s = res["summary"]
    rows = [{"id": d["id"], "code": d["code"], "sev": d["severity"], "who": d["who"], "rule": d["rule"]["code"], "what": d["short"], "state": d["outcome_label"]}
            for d in res["deviations"]]
    out = [f"{s['total']} deviations this week, {s['open']} open; open by kind: " + ", ".join(f"{k} {n}" for k, n in s["by_kind"].items())]
    out.append(table(rows, ["id", "code", "sev", "who", "rule", "what", "state"], width=52) if rows else "(none)")
    if res.get("groups"):
        out.append("\n" + table(res["groups"], ["label", "n", "open"]))
    return "\n".join(out)


@command("deviation", None, "<id>", "The record, its timeline and its evidence")
async def deviation_get(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("deviations.get", {"deviation_id": args.get_int(0, "id")})
    d = res["deviation"]
    out = [f"{d['code']}  {d['severity']}  {d['short']}  [{d['outcome_label']}]",
           kv({"rule": f"{d['rule']['code']} {d['rule']['name']}", "expected": d["expected"], "happened": d["happened"], "who": f"{d['who']} ({d['who_sub']})"})]
    if d["note"]:
        out.append(f"note ({d['by']}): {d['note']}")
    out.append("\naround it:")
    out.extend(f"  {e['at'][:16].replace('T', ' ')}  {e['who']}: {e['what']}" for e in res["context"])
    out.append("\nthe record shows:")
    out.extend(f"  - {e}" for e in res["evidence"])
    return "\n".join(out)


@command("deviation", "outcome", "<id> explained|accepted|escalated|dismissed|open [note...]", "Give a deviation an outcome (a note is required for explained and accepted)")
async def deviation_outcome(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"deviation_id": args.get_int(0, "id"), "outcome": args.get(1, "outcome")}
    if len(args.positional) > 2:
        payload["note"] = args.rest(2, "note")
    d = (await ctx.call("deviations.outcome", payload))["deviation"]
    return f"{d['code']}: {d['outcome_label']}"
