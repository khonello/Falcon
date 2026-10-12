"""The Overviews, the reports board and the Super User's decisions.

    overview                                  Super User: the four figures, the day's deviations and Worth a look. Admin: Waiting on you and the rest
    departments-board                         one row per department: Admins, machines, issues, version, time to address
    board [days=7] [dept=<id>]                reports with whose they are and how fast they are taken
    decisions                                 Super User: what only you can decide
    decide <decision> <option> [reason=.. message=.. hostname=.. reports=1,2]
    promote <account_id>                      Super User: a Worker becomes an Admin of their department (the new key is shown once)
    admin limit <account_id> on|off           Super User: limit an Admin to working hours
"""

from __future__ import annotations

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


def _mins(m: int | None) -> str:
    if m is None:
        return "-"
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"


@command("overview", help_="The Overview: your figures at a glance")
async def overview(ctx: ShellContext, args: Args) -> str:
    if ctx.state.role == "super_user":
        r = await ctx.call("overview.su")
        k = r["kpis"]
        out = [kv({"waiting on you": f"{k['waiting']} ({k['urgent']} urgent)",
                   "deviations this week": f"{k['deviations']} ({k['deviations_open']} open, {k['deviations_high']} critical or high)",
                   "machines online": f"{k['online']} / {k['machines']}" + (f" -- offline: {', '.join(k['offline'])}" if k["offline"] else ""),
                   "on the current version": f"{k['on_current_pct']}%" if k["on_current_pct"] is not None else "-"}),
               "\ndeviations, 7 days:", table(r["days"], ["day", "critical", "high", "medium", "low"])]
        if r["worth_a_look"]:
            rows = [{"code": d["code"], "sev": d["severity"], "who": d["who"], "what": d["short"], "state": d["outcome_label"]} for d in r["worth_a_look"]]
            out += ["\nworth a look:", table(rows, ["code", "sev", "who", "what", "state"], width=50)]
        return "\n".join(out)
    r = await ctx.call("overview.admin")
    w = r["waiting"]
    return kv({"waiting on you": f"{w['total']} ({w['to_verify']} to verify, {w['issues']} issues, {w['pings']} pings)",
               "department tasks not yet seen": w["department_tasks_unseen"],
               "machines online": f"{r['machines']['online']} / {r['machines']['total']}",
               "open issues": f"{r['issues']['open']} ({r['issues']['unassigned']} unassigned)", "sessions held now": r["sessions_held"]})


@command("departments-board", help_="One row per department: Admins, machines, issues, version, time to address")
async def departments_board(ctx: ShellContext, args: Args) -> str:
    rows = (await ctx.call("overview.departments"))["departments"]
    return table([{"department": d["name"], "admins": ", ".join(a or "?" for a in d["admins"]) or "NONE", "machines": f"{d['online']}/{d['machines']}",
                   "issues": d["open_issues"], "worst": d["worst"] or "-", "on current": f"{d['on_current_version']}/{d['machines']}",
                   "to address": _mins(d["median_minutes"]), "to you": d["reports"]["to_you"]} for d in rows],
                 ["department", "admins", "machines", "issues", "worst", "on current", "to address", "to you"])


@command("board", usage="[days=7] [dept=<id>]", help_="Reports with whose they are and how fast they are taken")
async def board(ctx: ShellContext, args: Args) -> str:
    payload: dict = {}
    if args.opt("days"):
        payload["days"] = args.opt_int("days")
    if args.opt("dept"):
        payload["department_id"] = args.opt_int("dept")
    r = await ctx.call("reports.board", payload)
    s = r["strip"]
    head = f"waiting {s['waiting']}" + (f", with the department {s['with_department']}" if s["with_department"] is not None else "")
    out = [head + f", addressed {s['addressed']}, typical {_mins(s['typical_minutes'])}"]
    if r["reports"]:
        out.append(table([{"id": x["id"], "report": x["label"], "where": x["host"] or x["department_name"] or "-", "whose": x["owner"],
                           "state": f"addressed by {x['addressed']['by']} in {_mins(x['addressed']['took_minutes'])}" if x["addressed"] else "waiting"}
                          for x in r["reports"]], ["id", "report", "where", "whose", "state"], width=44))
    else:
        out.append("(no reports)")
    if r["handling"]:
        out += ["\nhandling:", table([{"department": h["name"], "admin": "yes" if h["has_admin"] else "NO", "reports": h["all"], "done": h["done"],
                                       "waiting": h["waiting"], "to you": h["to_you"], "median": _mins(h["median_minutes"])} for h in r["handling"]],
                                     ["department", "admin", "reports", "done", "waiting", "to you", "median"])]
    return "\n".join(out)


@command("decisions", help_="What only you can decide")
async def decisions(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("overview.queue")
    if not r["decisions"]:
        return "Nothing is waiting on you."
    out = []
    for d in r["decisions"]:
        out.append(f"[{d['severity']}] {d['id']}  {d['title']}\n    {d['why']}")
        for o in d["options"]:
            out.append(f"      {o['key']:<22} {o['title']}" + (f"  (needs {o['need']})" if o["need"] else "") + (f"  -- {o['disabled']}" if o["disabled"] else ""))
    return "\n".join(out)


@command("decide", None, "<decision> <option> [reason=..] [message=..] [hostname=..] [reports=1,2]", "Carry out one option of one decision")
async def decide(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"decision": args.get(0, "decision"), "option": args.get(1, "option")}
    for k in ("reason", "message", "hostname"):
        if args.opt(k):
            payload[k] = args.opt(k)
    if args.opt("reports"):
        payload["report_ids"] = [int(x) for x in args.opt("reports").split(",") if x]
    r = await ctx.call("overview.decide", payload)
    out = r["done"] or "done"
    if r.get("result") and r["result"].get("client_key"):
        out += f"\nclient id {r['result']['client_id']}  key {r['result']['client_key']}  (shown once)"
    return out + f"\n{len(r['decisions'])} still waiting"


@command("promote", None, "<account_id>", "Make a Worker an Admin of their department (new key shown once)")
async def promote(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("hierarchy.admin_promote", {"account_id": args.get_int(0, "account_id")})
    return f"account {r['account_id']} is now an Admin\nclient id {r['client_id']}  key {r['client_key']}  (shown once)"


@command("admin", "limit", "<account_id> on|off", "Limit an Admin to working hours, or lift it")
async def admin_limit(ctx: ShellContext, args: Args) -> str:
    state = args.get(1, "on|off")
    if state not in ("on", "off"):
        raise UsageError("on or off")
    r = await ctx.call("hierarchy.admin_limit", {"account_id": args.get_int(0, "account_id"), "on": state == "on"})
    return f"account {r['account_id']} is {'limited to working hours' if r['hours_limited'] else 'no longer limited'}"
