"""The console's own views from a terminal: the fleet, one machine's page, the audit trail as events.

    machines [dept=<id>]                  every machine with its health
    machine <pc_id> [1h|6h|24h|7d]        one machine: facts, levels, processes, sessions, files, events
    feed [kind=..] [pc=<id>] [n=<n>]      the audit trail as events (kind, who, what, machine)
    feed summary [hours=<n>]              counts per kind over time
    feed export <file> [kind=..]          the same rows as CSV
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, command


def _kinds(args: Args) -> list[str] | None:
    return [k for k in (args.opt("kind") or "").split(",") if k] or None


@command("machines", usage="[dept=<id>]", help_="Every machine with its health, who is in it and what it runs")
async def machines(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("machines.list", {"department_id": args.opt_int("dept")} if args.opt("dept") else {})
    s = res["summary"]
    rows = [{"pc": m["pc_id"], "machine": m["hostname"], "department": m["department_name"], "health": m["health"],
             "user": m["user"] or "", "version": m["version"] or "?", "held by": m["held_by"] or "", "note": m["note"]}
            for m in res["machines"]]
    head = (f"{s['machines']} machines, {s['online']} online, {s['behind']} behind {res['current_version'] or 'no version yet'}; "
            + ", ".join(f"{n} {h}" for h, n in sorted(s["by_health"].items())))
    return head + "\n\n" + table(rows, ["pc", "machine", "department", "health", "user", "version", "held by", "note"], width=44)


@command("machine", usage="<pc_id> [1h|6h|24h|7d]", help_="One machine's page")
async def machine(ctx: ShellContext, args: Args) -> str:
    payload = {"pc_id": args.get_int(0, "pc_id")}
    if len(args.positional) > 1:
        payload["range"] = args.positional[1]
    res = await ctx.call("machines.get", payload)
    m = res["machine"]
    out = [kv({"machine": m["hostname"], "health": f"{m['health']} {m['note']}".strip(), "department": m["department_name"],
               "user": m["user"] or "(no one)", "version": m["version"], "os": m["os"], "ip": m["ip"],
               "online": m["online"], "last seen": m["last_seen_at"], "agent since": m["agent_started_at"],
               "held by": f"{m['held_by']} ({m['held_via']})" if m["held_by"] else ""})]
    for key in ("cpu", "memory", "disk", "net_kbps"):
        pts = res["series"][key]
        out.append(f"{key:<9} " + (f"{len(pts)} points, last {pts[-1]['v']}, high {max(p['v'] for p in pts)}" if pts else "no samples"))
    if res["processes"]:
        out.append("\nprocesses (as of " + res["processes"]["at"] + "):\n" + table(res["processes"]["items"][:12], ["pid", "name", "cpu", "memory_mb", "user"]))
    out.append("\nsessions:\n" + (table(res["sessions"], ["who", "type", "started_at", "ended_at", "seconds"]) if res["sessions"] else "(none)"))
    f = res["files"]
    out.append(f"\nfiles: {f['indexed']} indexed " + ", ".join(f"{n} {t}" for t, n in sorted(f["by_tag"].items())))
    out.append("\nevents:\n" + "\n".join(f"{e['at'][:16].replace('T', ' ')}  {e['kind']:<10} {e['actor']}: {e['what']}" for e in res["events"]))
    return "\n".join(out)


@command("feed", usage="[kind=..] [pc=<id>] [n=<n>] | summary [hours=<n>] | export <file> [kind=..]",
         help_="The audit trail as events: kind, who, what, machine")
async def feed(ctx: ShellContext, args: Args) -> str:
    sub = args.positional[0] if args.positional else ""
    since = (datetime.now(timezone.utc) - timedelta(hours=args.opt_int("hours") or 24 * 7)).isoformat()
    base = {"kinds": _kinds(args), "since": since} if _kinds(args) else {"since": since}
    if sub == "summary":
        res = await ctx.call("audit.summary", {**base, "bucket_minutes": 60})
        return kv({"events": res["total"], "people": res["actors"], "violations": res["violations"], "kept (days)": res["kept_days"],
                   **{f"  {k}": n for k, n in sorted(res["by_kind"].items())}})
    if sub == "export":
        res = await ctx.call("audit.export", base)
        Path(args.get(1, "file")).write_text(res["csv"], encoding="utf-8")
        return f"{res['rows']} rows written to {args.get(1, 'file')}"
    if args.opt("pc"):
        base["pc_id"] = args.opt_int("pc")
    res = await ctx.call("audit.events", {**base, "limit": args.opt_int("n") or 30})
    rows = [{"at": e["at"][:16].replace("T", " "), "kind": e["kind"], "who": e["actor"], "what": e["what"], "machine": e["host"] or ""}
            for e in res["events"]]
    return table(rows, ["at", "kind", "who", "what", "machine"], width=60) + ("\n(more)" if res["more"] else "")
