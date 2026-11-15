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
                         f"{_online(a)} {_session_line(a['session'])}")
        for w in d["workers"]:
            lines.append(f"    WORKER {w['name']:<22} account {w['account_id']:<3} pc {w['pc_id']:<3} {w['hostname']:<12} "
                         f"{_online(w)} {_session_line(w['session'])}")
    return "\n".join(lines) or "(no departments)"


def _online(a: dict) -> str:
    return "online " if a.get("online") else "offline"


@command("pc", "state", "<pc_id>", "A machine's live state: reachable, last seen, levels, the program in front")
async def pc_state(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.pc_state", {"pc_id": args.get_int(0, "pc_id")})
    lv, fg = res["levels"] or {}, res["foreground"] or {}
    return "\n".join([
        f"{res['hostname']} (pc {res['pc_id']}): {'online' if res['online'] else 'not reachable'}"
        + (f", last seen {res['last_seen_at']}" if res["last_seen_at"] else ", never connected"),
        f"levels: processor {lv['cpu']}%, memory {lv['memory']}%, idle {lv['idle_s']}s (at {lv['at']})" if lv
        else "levels: none reported since the Engine started",
        f"in front: {fg['program']} -- {fg['title']}" if fg else "in front: nothing reported"])


@command("traverse", usage="<pc_id> [force] [mode=see|control]",
         help_="Enter a PC's session. `force` = block-or-end an occupied session first (vertical only)")
async def traverse(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.traverse", {"pc_id": args.get_int(0, "pc_id"), "force": args.flag("force"), "mode": args.opt("mode") or "control"})
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


@command("sessions", usage="[hours=<n>]",
         help_="The record of the day: who held each PC and for how long, ended sessions included")
async def sessions(ctx: ShellContext, args: Args) -> str:
    payload = {"hours": args.opt_int("hours")} if args.opt("hours") else {}
    res = await ctx.call("hierarchy.sessions_today", payload)
    if not res["sessions"]:
        return f"(no sessions since {res['since'][11:16]})"
    lines = [f"since {res['since'][11:16]}"]
    for s in res["sessions"]:
        span = f"{s['entered_at'][11:16]}-{s['ended_at'][11:16] if s['ended_at'] else 'now '}"
        tag = "native" if s["occupied_via"] == "native" else s["occupied_via"].upper()
        ended = f"  ({s['ended_reason']})" if s["ended_reason"] else ""
        lines.append(f"  {s['hostname']:<12} {span}  {tag:<15} {s.get('occupant_name') or '?'}{ended}")
    return "\n".join(lines)


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


@command("dept", "rename", "<department_id> <name...>", "Rename a department; its machines stay in it")
async def dept_rename(ctx: ShellContext, args: Args) -> str:
    name = " ".join(args.positional[1:])
    if not name:
        raise UsageError("dept rename <department_id> <name...>")
    res = await ctx.call("hierarchy.department_rename", {"department_id": args.get_int(0, "department_id"), "name": name})
    return f"{res['was']} is now {res['name']}"


@command("pc", "move", "<pc_id> <department_id>", "Put a machine (and whoever is bound to it) in another department: a label, nothing on the machine changes")
async def pc_move(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.pc_move", {"pc_id": args.get_int(0, "pc_id"), "department_id": args.get_int(1, "department_id")})
    return f"pc {res['pc_id']} is in department {res['department_id']}" + ("" if res["moved"] else " already")


@command("dept", "add", "<name...>", "Create a department")
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


@command("account", "owns", "<account_id>", "What an account still owns: restrictions, flows, rules, actions, tasks to verify, issues")
async def account_owns(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.ownership", {"account_id": args.get_int(0, "account_id")})
    lines = [f"account {res['account_id']} ({res['status']}): {res['total']} thing(s)"]
    lines.extend(f"  {what}: {', '.join(map(str, ids))}" for what, ids in res["owned"].items() if ids)
    return "\n".join(lines)


@command("account", "handover", "<from_account_id> <to_account_id>",
         "An Admin who left (offboard them first) hands everything they still own to another Admin")
async def account_handover(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.hand_over", {"from_account_id": args.get_int(0, "from_account_id"),
                                                 "to_account_id": args.get_int(1, "to_account_id")})
    lines = [f"handed {res['total']} thing(s) from account {res['from_account_id']} to {res['to_account_id']}"]
    lines.extend(f"  {what}: {', '.join(map(str, ids))}" for what, ids in res["moved"].items() if ids)
    return "\n".join(lines)


@command("account", None, "<account_id>", "Show an account")
async def account_get(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.account_get", {"account_id": args.get_int(0, "account_id")})
    return f"name (as you see it): {res['name']}\n" + kv(res["account"])


@command("pc", "add", "<hostname> <pc_type> [dept=<id>]", "Register a PC without an account yet")
async def pc_add(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("hierarchy.pc_register", {"hostname": args.get(0, "hostname"), "pc_type": args.get(1, "pc_type"),
                                                  "department_id": args.opt_int("dept")})
    return f"pc {res['pc_id']} registered"
