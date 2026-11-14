"""The Registry and a department's page.

    accounts [dept=<id>] [workers]             every Admin: workstation, key number, signed in or not
    refused [days=7]                           connections turned away at the handshake: who tried, why, how many times, what to do
    block <address> [reason...]                refuse an address at the door
    unblock <address>
    blocked                                    the addresses refused at the door
    department <id>                            a department's page: Admins, vacancy, machines, issues, reports handling, work
    admin demote <account_id>                  an Admin stops being one (the machine gets a new key, shown once)
"""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


@command("accounts", usage="[dept=<id>] [workers]", help_="Accounts: every Admin (add `workers` for them too)")
async def accounts(ctx: ShellContext, args: Args) -> str:
    payload: dict = {}
    if args.opt("dept"):
        payload["department_id"] = args.opt_int("dept")
    if "workers" in args.positional:
        payload["roles"] = ["admin", "worker"]
    r = await ctx.call("registry.accounts", payload)
    rows = [{"id": a["account_id"], "name": a["name"] or "?", "role": a["role"], "department": a["department_name"] or "-", "workstation": a["workstation"] or "-",
             "key": f"no. {a['key_generation']}" if a["key_generation"] else "-", "now": a["now"] + (", limited to working hours" if a["hours_limited"] else "")}
            for a in r["accounts"]]
    return f"{r['summary']['accounts']} accounts, {r['summary']['online']} signed in\n" + table(rows, ["id", "name", "role", "department", "workstation", "key", "now"])


@command("refused", usage="[days=7]", help_="Connections turned away at the handshake, and what to do about each")
async def refused(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("registry.refused", {"days": args.opt_int("days") or 7})
    if not r["refused"]:
        return "Nothing was refused."
    rows = [{"who": g["host"], "address": g["address"] + (" (blocked)" if g["blocked"] else ""), "because": g["why"], "tries": g["tries"],
             "last": (g["last"] or "")[:16].replace("T", " "), "do": g["advice"]} for g in r["refused"]]
    s = r["summary"]
    return f"{s['groups']} refused, {s['tries']} tries, {s['bad']} worth a look\n" + table(rows, ["who", "address", "because", "tries", "last", "do"], width=42)


@command("knocked", usage="[days=7]", help_="PCs that tried to connect without being registered, by the name they gave (register one with pc register)")
async def knocked(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("registry.knocked", {"days": args.opt_int("days") or 7})
    if not r["knocked"]:
        return "No unregistered PC tried to connect."
    rows = [{"name": k["name"], "address": k["address"], "tries": k["tries"], "last": (k["last"] or "")[:16].replace("T", " ")} for k in r["knocked"]]
    return table(rows, ["name", "address", "tries", "last"])


@command("block", None, "<address> [reason...]", "Refuse an address at the door")
async def block(ctx: ShellContext, args: Args) -> str:
    payload = {"address": args.get(0, "address")}
    if len(args.positional) > 1:
        payload["reason"] = args.rest(1, "reason")
    r = await ctx.call("registry.block", payload)
    return f"{r['address']} is blocked" + (" (it was already)" if r["was_blocked"] else "")


@command("unblock", None, "<address>", "Let an address connect again")
async def unblock(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("registry.unblock", {"address": args.get(0, "address")})
    return f"{r['address']} is no longer blocked" if r["was_blocked"] else f"{r['address']} was not blocked"


@command("blocked", help_="The addresses refused at the door")
async def blocked(ctx: ShellContext, args: Args) -> str:
    rows = (await ctx.call("registry.blocked"))["blocked"]
    return table(rows, ["address", "reason", "at"]) if rows else "No address is blocked."


@command("department", None, "<id>", "A department's page")
async def department(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("departments.get", {"department_id": args.get_int(0, "id")})
    s = r["summary"]
    out = [f"{r['department']['name']}: " + ("NO ADMIN" if r["vacant"] else ", ".join(a["name"] or "?" for a in r["admins"])) + f" -- {s['machines']} machines, {s['online']} online, {r['open_issues']} open issues"]
    if r["machines"]:
        out.append(table([{"machine": m["hostname"], "health": m["health"], "user": m["user"] or "-", "version": m["version"] or "-"} for m in r["machines"]], ["machine", "health", "user", "version"]))
    if r["issues"]:
        out += ["\nworst issues:", table([{"code": i["code"], "sev": i["severity"], "issue": i["title"], "subject": i["subject"]} for i in r["issues"]], ["code", "sev", "issue", "subject"], width=40)]
    if r["tasks"]:
        out += ["\nopen work:", table([{"id": t["id"], "task": t["title"], "standing": t["standing"]} for t in r["tasks"]], ["id", "task", "standing"], width=50)]
    if r["vacant"] and r["workers"]:
        out.append("\ncould be promoted: " + ", ".join(f"{w['name'] or w['workstation']} (account {w['account_id']})" for w in r["workers"]))
    return "\n".join(out)


@command("admin", "demote", "<account_id>", "An Admin stops being one (never yourself)")
async def admin_demote(ctx: ShellContext, args: Args) -> str:
    r = await ctx.call("hierarchy.admin_demote", {"account_id": args.get_int(0, "account_id")})
    return f"account {r['account_id']} is a Worker again\nclient id {r['client_id']}  key {r['client_key']}  (shown once)"


@command("licence", "import", "<file.json>", "Take in a licence's codes (the file the licence store hands over: {name, reference?, codes: [{code, role, seats?, department?, expires_at?}]})")
async def licence_import(ctx: ShellContext, args: Args) -> str:
    import json
    from pathlib import Path

    path = Path(args.get(0, "file"))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"cannot read {path}: {exc}") from exc
    res = await ctx.call("licence.import", data)
    return f"licence {res['licence_id']}: {res['added']} code(s) added" + (f", {res['already_known']} already known" if res["already_known"] else "")


@command("licences", help_="Licence codes: role, seats used, where machines that joined went (a code shows only its last four characters)")
async def licences(ctx: ShellContext, args: Args) -> str:
    codes = (await ctx.call("licence.list"))["codes"]
    rows_ = [{"id": c["id"], "licence": c["licence"], "code": "..." + c["last4"], "role": c["role"], "used": f"{c['used']}/{c['seats']}",
              "department": c["department"] or "", "expires": (c["expires_at"] or "")[:10], "state": "withdrawn" if c["revoked_at"] else ""}
             for c in codes]
    return table(rows_, ["id", "licence", "code", "role", "used", "department", "expires", "state"]) if rows_ else "(no licence codes yet: licence import <file>)"


@command("licence", "revoke", "<code_id>", "Withdraw a licence code: no further machine joins with it (the ones that joined stay)")
async def licence_revoke(ctx: ShellContext, args: Args) -> str:
    await ctx.call("licence.revoke", {"code_id": args.get_int(0, "code_id")})
    return "withdrawn"


# --- seats: machines knock, Admins give seats (docs/SEATS-AND-SETUP.md) -------------------------------------------------

@command("seats", help_="Seats bought and in use, for Admins and for Workers, and until when")
async def seats(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("seats.summary")
    if not res["registered"]:
        head = "This Engine is not registered with the store: seats are not counted."
    else:
        head = "Seats (bought in the store):"
    rows_ = []
    for role, label in (("admin", "Admin"), ("worker", "Worker")):
        r = res[role]
        until = (r["valid_until"] or "")[:10]
        grace = f"in grace until {r['grace_ends'][:10]}" if r["in_grace"] and r["grace_ends"] else ""
        rows_.append({"kind": label, "bought": "-" if r["bought"] is None else r["bought"], "in use": r["in_use"],
                      "free": "-" if r["free"] is None else r["free"], "until": until, "note": grace})
    return head + "\n" + table(rows_, ["kind", "bought", "in use", "free", "until", "note"])


@command("knocks", help_="Machines knocking for a seat, with what they say about themselves (look-alikes flagged)")
async def knocks(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("knocks.list")
    rows_ = [{"id": k["id"], "machine": k["hostname"], "signed in": k["signed_in_user"] or "", "address": k["peer"] or "",
              "hardware": (k["hardware_id"] or "")[:18], "first knocked": (k["first_seen"] or "")[:16], "look-alike": "; ".join(k["look_alike"])}
             for k in res["knocks"]]
    return table(rows_, ["id", "machine", "signed in", "address", "hardware", "first knocked", "look-alike"]) if rows_ else "(nobody is knocking)"


@command("seat", "give", "<knock_id> [department_id]", "Give a knocking machine a Worker seat, in that department (needed when departments exist)")
async def seat_give(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"knock_id": args.get_int(0, "knock_id")}
    if len(args.positional) > 1:
        payload["department_id"] = args.get_int(1, "department_id")
    res = await ctx.call("seat.give", payload)
    return f"{res['hostname']} has a Worker seat (pc {res['pc_id']}, department {res['department_id']}); it collects its own key"


@command("seat", "take", "<pc_id>", "Take a machine's seat back: it is cut off from the Engine and knocks again (never the last Admin seat)")
async def seat_take(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("seat.take", {"pc_id": args.get_int(0, "pc_id")})
    return f"pc {res['pc_id']}'s {res['role']} seat is taken back; it knocks again"


@command("seats", "refresh", help_="Ask the store now for seats bought since it last asked")
async def seats_refresh(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("seats.refresh")
    return f"{res['added']} new grant(s) from the store" if res["added"] else "nothing new from the store"
