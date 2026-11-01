"""Parked with the Super User (docs/design/v1-it-admin.md), 1 Nov 2026: commands and code cut from the shipped Operator Client.
Each block says the file it came from; it goes back there, with that file's imports."""

# from operator_client/tui/commands/hierarchy.py
@command("handover", help_="Move the Super User to another machine: open it, then confirm with the code the new machine shows")
async def handover_status(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("handover.status")
    head = f"handover is open until {res['until']}" if res["open"] else "handover is closed (handover open lets ONE new machine ask, for ten minutes)"
    rows_ = [{"id": r["id"], "machine": r["hostname"], "os": r["os"], "since": r["created_at"]} for r in res["waiting"]]
    return head + ("\n" + table(rows_, ["id", "machine", "os", "since"]) if rows_ else "")


# from operator_client/tui/commands/hierarchy.py
@command("handover", "open", "", "Let one new machine ask to become the Super User's (ten minutes)")
async def handover_open(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("handover.open")
    return f"open until {res['until']}: install the Super User console on the new machine and let it ask; it shows a code"


# from operator_client/tui/commands/hierarchy.py
@command("handover", "confirm", "<id> <code>", "Type the code the new machine shows: the Super User moves there and this machine stops being the Super User's")
async def handover_confirm(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("handover.confirm", {"enrollment_id": args.get_int(0, "id"), "code": args.get(1, "code")})
    return f"the Super User now lives on {res['hostname']} (pc {res['to_pc']}); this machine ({res['from_pc']}) is no longer the Super User's and is no longer part of Falcon"


# from operator_client/tui/commands/hierarchy.py
@command("handover", "cancel", "", "Close the handover and refuse any machine waiting")
async def handover_cancel(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("handover.cancel")
    return f"closed; {res['refused']} waiting machine(s) refused"


# from operator_client/tui/commands/overview.py
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


# from operator_client/tui/commands/overview.py
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


# from operator_client/tui/commands/overview.py
@command("admin", "limit", "<account_id> on|off", "Limit an Admin to working hours, or lift it")
async def admin_limit(ctx: ShellContext, args: Args) -> str:
    state = args.get(1, "on|off")
    if state not in ("on", "off"):
        raise UsageError("on or off")
    r = await ctx.call("hierarchy.admin_limit", {"account_id": args.get_int(0, "account_id"), "on": state == "on"})
    return f"account {r['account_id']} is {'limited to working hours' if r['hours_limited'] else 'no longer limited'}"


# from operator_client/tui/commands/reports.py
@command("routing", help_="Report routing configuration (Super User)")
async def routing(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.routing_get")
    return "categories: " + ", ".join(res["categories"]) + "\n\n" + table(res["routing"], ["category", "department_name",
                                                                                          "routed_department_id", "configured_at", "includes_earlier"])


# from operator_client/tui/commands/reports.py
@command("routing", "set", "<category> [dept_ids,...] [earlier=no]",
         "Route a report category to departments (empty = none); earlier=no: added ones get only new reports")
async def routing_set(ctx: ShellContext, args: Args) -> str:
    ids = [int(x) for x in args.positional[1].split(",") if x] if len(args.positional) > 1 else []
    earlier = (args.opt("earlier") or "yes").lower() not in ("no", "false", "0", "off")
    res = await ctx.call("reports.routing_set", {"category": args.get(0, "category"), "department_ids": ids,
                                                 "include_earlier": earlier})
    line = f"{res['category']} -> departments {res['department_ids'] or 'none (Super User only)'}"
    if res["added"]:
        line += f"\nadded {res['added']}: " + (f"with the {res['earlier_unaddressed']} earlier unaddressed"
                                                if res["include_earlier"] else "new reports only")
    if res["removed"]:
        line += f"\nremoved {res['removed']}"
    return line


# from operator_client/tui/commands/reports.py
@command("addressed", help_="The Super-User-only View: who addressed which report, when")
async def addressed(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("reports.addressed_view")
    return table(res["addressed"], ["report_id", "category", "addressed_by_account_id", "addressed_by_department_id", "addressed_at"])


# from operator_client/tui/commands/overview.py (overview)
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


# from operator_client/__main__.py
    if args.handover_join:
        import asyncio

        from operator_client.core.handover_join import HandoverEnded, join

        if args.engine:
            host, _, port = args.engine.rpartition(":")
            cfg.engine_host, cfg.engine_port = (host or args.engine), int(port) if port.isdigit() else cfg.engine_port
        if args.ca:
            cfg.ca_cert = args.ca
        if args.plaintext:
            cfg.tls = False
        try:
            asyncio.run(join(cfg))
        except HandoverEnded as exc:
            print(f"Not finished: {exc}")
            raise SystemExit(1) from exc
        raise SystemExit(0)
