"""Hierarchy: tree, traversal & sessions, display names, departments/accounts, assisted access."""

from __future__ import annotations

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


def _session_line(s: dict | None) -> str:
    if not s:
        return "free"
    tag = "native" if s["occupied_via"] == "native" else s["occupied_via"].upper()
    return f"{tag} by {s.get('occupant_name')} ({s['occupant_role']})" + (
        f" until {s['deadline_at'][11:16]}" if s.get("deadline_at") else "")


@command("tree", help_="The hierarchy as the Engine lets you see it (names resolved for you)")
async def tree(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.tree")
    lines = []
    for d in res["departments"]:
        lines.append(f"{d['name']}  (department {d['department_id']})")
        for a in d["admins"]:
            lines.append(f"  ADMIN  {a['name']:<24} account {a['account_id']:<3} pc {a['pc_id']:<3} {a['hostname']:<12} "
                         f"{_session_line(a['session'])}")
        for w in d["workers"]:
            lines.append(f"    WORKER {w['name']:<22} account {w['account_id']:<3} pc {w['pc_id']:<3} {w['hostname']:<12} "
                         f"{_session_line(w['session'])}")
    return "\n".join(lines) or "(no departments)"


@command("traverse", usage="<pc_id> [force]",
         help_="Enter a PC's session. `force` = block-or-end an occupied session first (vertical only)")
async def traverse(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.traverse", {"pc_id": args.get_int(0, "pc_id"), "force": args.flag("force")})
    ctx.state.set_session(res["session"])
    s = res["session"]
    note = "already occupying" if res["already_occupying"] else "entered"
    banner = "\n[RED BANNER] you are inside another user's view" if s.get("super_user_banner") else ""
    restricted = "\nrestricted view: Conditional Rendering applies" if s.get("restricted_view") else ""
    return f"{note} pc {s['pc_id']} -- session {s['session_id']}, deadline {s['deadline_at']}{banner}{restricted}"


@command("end", usage="[session_id]", help_="End your current session (or someone else's, if you outrank them)")
async def end(ctx: ShellContext, args: Args) -> str:
    sid = int(args.positional[0]) if args.positional else (ctx.state.session or {}).get("session_id")
    if sid is None:
        raise UsageError("no session to end")
    res = await ctx.call("hierarchy.end_session", {"session_id": sid})
    if ctx.state.session and ctx.state.session.get("session_id") == sid:
        ctx.state.set_session(None)
    return f"session {sid} ended ({res['reason']})"


@command("extend", help_="Extend your traversal time limit by one step")
async def extend(ctx: ShellContext, args: Args) -> str:
    sid = (ctx.state.session or {}).get("session_id")
    if sid is None:
        raise UsageError("you are not occupying a session")
    res = await ctx.call("hierarchy.extend_session", {"session_id": sid})
    ctx.state.session["deadline_at"] = res["deadline_at"]
    ctx.state.set_session(ctx.state.session)
    return f"deadline now {res['deadline_at']} (extended {res['extended_count']}x)"


@command("session", usage="[pc_id]", help_="Session state of a PC (default: your own)")
async def session(ctx: ShellContext, args: Args) -> str:
    payload = {"pc_id": int(args.positional[0])} if args.positional else {}
    res = await ctx.call("hierarchy.session_state", payload)
    ctx.state.set_session(res.get("my_session"))
    return (f"pc {res['pc_id']}: {_session_line(res['pc_session'])}\n"
            f"you: {_session_line(res['my_session'])}" + ("\nBLOCKED" if res["blocked"] else ""))


@command("claim", help_="Re-claim your own PC after a block is released")
async def claim(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.claim_native")
    if res["blocked"]:
        return "still blocked"
    ctx.state.blocked_by = None
    ctx.state.clear_indicator("blocked")
    st = await ctx.call("hierarchy.session_state")
    ctx.state.set_session(st.get("my_session"))
    return f"claimed native session {res['session_id']}"


# --- names --------------------------------------------------------------------------------------

@command("name", "set", "<account_id> <label...>", "Privately label an account below you (never propagates)")
async def name_set(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.set_display_name", {"account_id": args.get_int(0, "account_id"),
                                                       "label": args.rest(1, "label")})
    return f"account {res['account_id']} is now '{res['label']}' in your view"


@command("name", "self", "<label...>", "Set the name those below you see")
async def name_self(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.set_self_name", {"label": args.rest(0, "label")})
    return f"your self name is now '{res['label']}'"


@command("names", usage="<account_id...>", help_="Resolve names as you see them")
async def names(ctx: ShellContext, args: Args) -> str:
    ids = [int(x) for x in args.positional] if args.positional else []
    if not ids:
        raise UsageError("give at least one account id")
    res = await ctx.call("hierarchy.resolve_names", {"account_ids": ids})
    return kv(res["names"])


# --- departments / accounts -----------------------------------------------------------------------

@command("depts", help_="List departments")
async def depts(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("hierarchy.departments"))["departments"], ["id", "name", "created_at"])


@command("dept", "add", "<name...>", "Create a department (Super User)")
async def dept_add(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.department_create", {"name": args.rest(0, "name")})
    return f"department {res['department_id']} '{res['name']}' created"


@command("account", "add", "<role> <hostname> [dept=<id>]",
         "Provision an account + its PC; prints the client_id ONCE")
async def account_add(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.account_create", {"role": args.get(0, "role"), "hostname": args.get(1, "hostname"),
                                                     "department_id": args.opt_int("dept")})
    return (f"account {res['account_id']} ({res['role']}) on pc {res['pc_id']}\n"
            f"client_id: {res['client_id']}   <- give this to the client install; it is not shown again")


@command("account", "offboard", "<account_id>", "Deactivate an account (never deleted)")
async def account_offboard(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.account_offboard", {"account_id": args.get_int(0, "account_id")})
    return f"account {res['account_id']} {res['status']}"


@command("account", None, "<account_id>", "Show an account")
async def account_get(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.account_get", {"account_id": args.get_int(0, "account_id")})
    return f"name (as you see it): {res['name']}\n" + kv(res["account"])


@command("pc", "add", "<hostname> <pc_type> [dept=<id>]", "Register a PC without an account yet")
async def pc_add(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.pc_register", {"hostname": args.get(0, "hostname"), "pc_type": args.get(1, "pc_type"),
                                                  "department_id": args.opt_int("dept")})
    return f"pc {res['pc_id']} registered"


# --- assisted access ------------------------------------------------------------------------------

@command("assist", "available", "on|off", "Broadcast / withdraw your availability to help peers")
async def assist_available(ctx: ShellContext, args: Args) -> str:
    on = args.get(0, "on|off").lower() in ("on", "yes", "true", "1")
    res = await ctx.call("assisted_access.set_available", {"available": on})
    return "available for assistance" if res["available"] else "not available"


@command("assist", "helpers", "[dept=<id>]", "Admins reachable right now")
async def assist_helpers(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assisted_access.available_helpers", {"department_id": args.opt_int("dept")})
    return table(res["helpers"], ["id", "name", "department_name"])


@command("assist", "request", "[dept=<id>] [helper=<account_id>] [deny=key,key]",
         "Ask for hands-on help; `deny` narrows the scope (never widens it)")
async def assist_request(ctx: ShellContext, args: Args) -> str:
    narrowing = {k: False for k in (args.opt("deny") or "").split(",") if k}
    res = await ctx.call("assisted_access.request", {"department_id": args.opt_int("dept"),
                                                    "helper_account_id": args.opt_int("helper"), "narrowing": narrowing})
    if not res["matched"]:
        return f"request {res['request_id']}: {res['message']}"
    return f"request {res['request_id']} offered to {res['helper_name']} (account {res['helper_account_id']}) -- waiting"


@command("assist", "accept", "<request_id>", "Accept an assistance offer (you enter their workstation)")
async def assist_accept(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assisted_access.accept", {"request_id": args.get_int(0, "request_id")})
    st = await ctx.call("hierarchy.session_state")
    ctx.state.set_session(st.get("my_session"))
    ctx.state.clear_indicator(f"offer:{res['request_id']}")
    return f"assisting: session {res['session_id']} until {res['deadline_at']}\nscope: " + ", ".join(
        k for k, v in res["scope"].items() if v)


@command("assist", "decline", "<request_id>", "Decline an assistance offer")
async def assist_decline(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assisted_access.decline", {"request_id": args.get_int(0, "request_id")})
    ctx.state.clear_indicator(f"offer:{res['request_id']}")
    return "declined"


@command("assist", "close", "<request_id>", "End an assistance session (either party)")
async def assist_close(ctx: ShellContext, args: Args) -> str:
    await ctx.call("assisted_access.close", {"request_id": args.get_int(0, "request_id")})
    st = await ctx.call("hierarchy.session_state")
    ctx.state.set_session(st.get("my_session"))
    return "assistance session closed"


@command("assist", "status", "<request_id>", "Status of an assistance request")
async def assist_status(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assisted_access.status", {"request_id": args.get_int(0, "request_id")})
    return kv(res["request"]) + "\n\nsession:\n" + (kv(res["session"]) if res["session"] else "  (none)") + (
        "\n(offer pending)" if res["pending_offer"] else "")


