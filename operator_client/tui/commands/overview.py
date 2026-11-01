"""The Overview and the reports board.

    overview                                  Waiting on you and the rest
    departments-board                         one row per department: Admins, machines, issues, version, time to address
    board [days=7] [dept=<id>]                reports with whose they are and how fast they are taken
    promote <account_id>                      a Worker becomes an Admin (the new key is shown once)
"""

from __future__ import annotations

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, command


def _mins(m: int | None) -> str:
    if m is None:
        return "-"
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"


@command("overview", help_="The Overview: your figures at a glance")
async def overview(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("overview.admin")
    w = r["waiting"]
    return kv({"waiting on you": f"{w['total']} ({w['to_verify']} to verify, {w['issues']} issues, {w['pings']} pings)",
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


@command("promote", None, "<account_id>", "Make a Worker an Admin of their department (new key shown once)")
async def promote(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("hierarchy.admin_promote", {"account_id": args.get_int(0, "account_id")})
    return f"account {r['account_id']} is now an Admin\nclient id {r['client_id']}  key {r['client_key']}  (shown once)"
