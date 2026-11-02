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
