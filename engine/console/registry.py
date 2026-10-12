"""The Registry (machines, accounts, refused connections) and a department's page.

    registry.accounts {department_id?, roles?}   the Super User and every Admin (a Worker too, if asked): workstation, key number, whether signed in
    registry.refused  {days?}                    connections turned away at the handshake, grouped by who tried and from where, with what to do
    registry.blocked                             the addresses refused at the door
    registry.block    {address, reason?}         Super User: refuse an address from now on (the tries are still recorded)
    registry.unblock  {address}                  Super User
    departments.get   {department_id}            a department: its Admins, vacancy, machines, worst open issues, reports handling, open work, Workers who could be promoted

The machines list is `machines.list` (its `key_generation`, `version`, `last_seen_at`); registering a PC, provisioning an Admin and making a new key are
`hierarchy.pc_register`, `hierarchy.account_create` and `hierarchy.pc_rekey`.
"""

from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, dispatch, handler
from engine.permissions import int_field, require_department_scope, require_role, str_field
from protocol import ErrorCode, ProtocolError

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


@handler("registry.accounts")
async def accounts(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The Super User sees every account of the roles asked (default: Super User and Admins); an Admin their own department's."""
    ident = require_role(ctx, "super_user", "admin")
    roles = payload.get("roles") or (["super_user", "admin"] if ident.role == "super_user" else ["admin", "worker"])
    if not isinstance(roles, list) or not set(roles) <= {"super_user", "admin", "worker"}:
        raise ProtocolError(ErrorCode.INVALID, "roles must be some of super_user, admin, worker")
    department_id = ident.department_id if ident.role == "admin" else int_field(payload, "department_id", required=False)
    db = ctx.engine.db
    found = await db.registry.account_rows(department_id=department_id, roles=roles)
    online = ctx.engine.online_pc_ids()
    names = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in found]) if found else {}
    out = []
    for a in found:
        here = a["bound_pc_id"] in online
        out.append({"account_id": a["id"], "name": "You" if a["id"] == ident.account_id else names.get(a["id"]), "you": a["id"] == ident.account_id,
                    "role": a["role"], "department_id": a["department_id"], "department_name": a["department_name"], "pc_id": a["bound_pc_id"],
                    "workstation": a["hostname"], "key_generation": a["key_generation"], "online": here, "last_seen_at": _iso(a["last_seen_at"]),
                    "hours_limited": a["hours_limited"], "now": "Signed in now" if here else ("Not signed in" if a["last_seen_at"] else "Never signed in")})
    return {"accounts": out, "summary": {"accounts": len(out), "admins": sum(1 for a in out if a["role"] == "admin"), "online": sum(1 for a in out if a["online"])}}


# --- refused connections ---------------------------------------------------------------------------------------------------------


def _why(kind: str, d: dict[str, Any]) -> tuple[str, str, str, str]:
    """(why, tone, advice, what to say) for one kind of refusal."""
    machine = d.get("machine") or "the machine"
    if kind == "unknown":
        return ("not registered", "wait", "register",
                "A machine nobody registered keeps trying to connect. If it belongs to a department, register it; it gets a key and stops being refused.")
    if kind == "old_key":
        return (f"key no. {d.get('old_generation')}, replaced by no. {d.get('key_generation')}", "wait", "rekey",
                f"Something on {machine} still has the key that was replaced. Give it the new key, or make another one if you are not sure where the old one went.")
    if kind == "wrong_key":
        elsewhere = d.get("same_address") is False
        return (f"wrong key for {machine}" + (f", from an address {machine} never uses" if elsewhere else ""), "bad" if elsewhere else "wait",
                "rekey" if elsewhere else "block",
                f"A machine claimed to be {machine} with a key that does not match" + (f", from an address {machine} has never used. Make {machine} a new key and block the address until you know who it is."
                                                                                        if elsewhere else ". If it is the real machine, give it its key again."))
    if kind == "blocked":
        return ("address blocked", "wait", "unblock", "This address is blocked. It is turned away before it can say who it is.")
    return ("an answer to a challenge that was not outstanding", "wait", "block", "A connection answered a challenge it was not given. A reconnecting client does this once; many tries are worth a look.")


@handler("registry.refused")
async def refused(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User. {"days"?: 7} -> {"refused": [...], "summary": {groups, tries, bad}}. One row per (who tried, from where): the name it claimed, the address,
    why it was refused, how many times, the first and last try, the machine it claimed to be (if the client id is one of ours), whether that machine has
    ever used the address, whether the address is blocked now, and what to do about it (`advice`: register, rekey, block, unblock)."""
    require_role(ctx, "super_user")
    db = ctx.engine.db
    days = max(1, min(int_field(payload, "days", required=False) or 7, 90))
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for r in await db.registry.refused(datetime.now(timezone.utc) - timedelta(days=days)):
        d = r["detail"] or {}
        address = d.get("address") or (d.get("peer") or "").strip("()'").split("'")[0] or "unknown"
        kind = d.get("kind") or "other"
        key = (address, r["client_id"] or d.get("claimed_name") or "")
        g = groups.get(key)
        if g is None:
            why, tone, advice, say = _why(kind, d)
            groups[key] = g = {"id": f"door:{address}:{key[1]}", "address": address, "client_id": r["client_id"] or None, "kind": kind, "why": why, "tone": tone,
                               "advice": advice, "say": say, "tries": 0, "last": r["occurred_at"], "first": r["occurred_at"], "claimed_name": d.get("claimed_name"),
                               "pc_id": d.get("pc_id"), "machine": d.get("machine"), "same_address": d.get("same_address"),
                               "host": (f"Claims to be {d['machine']}" if kind == "wrong_key" and d.get("machine") else d.get("machine") or d.get("claimed_name")
                                        or r["client_id"] or address)}
        g["tries"] += 1
        g["first"] = min(g["first"], r["occurred_at"])
    blocked = await db.registry.blocked_set()
    out = []
    for g in groups.values():
        g["blocked"] = g["address"] in blocked
        if g["blocked"]:
            g["advice"] = "unblock"
        g["last"], g["first"] = _iso(g["last"]), _iso(g["first"])
        out.append(g)
    out.sort(key=lambda g: (g["tone"] != "bad", -g["tries"]))
    return {"refused": out, "days": days, "summary": {"groups": len(out), "tries": sum(g["tries"] for g in out), "bad": sum(1 for g in out if g["tone"] == "bad")}}


@handler("registry.blocked")
async def blocked(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user")
    rows = await ctx.engine.db.registry.blocked()
    return {"blocked": [{"address": r["address"], "reason": r["reason"], "at": _iso(r["at"])} for r in rows]}


def _address(payload: dict[str, Any]) -> str:
    raw = str_field(payload, "address")
    try:
        return str(ipaddress.ip_address(raw.strip()))
    except ValueError as exc:
        raise ProtocolError(ErrorCode.INVALID, f"{raw!r} is not an address") from exc


@handler("registry.block")
async def block(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User. {"address", "reason"?}. The address is refused at the door from now on, whoever it is; a connection already open stays until it ends."""
    ident = require_role(ctx, "super_user")
    address = _address(payload)
    own = ctx.connection.peer[0] if getattr(ctx.connection, "peer", None) else None
    if own is not None and address == str(own):
        raise ProtocolError(ErrorCode.CONFLICT, "that is the address you are connected from")
    reason = " ".join(str(payload.get("reason") or "").split())[:300]
    fresh = await ctx.engine.db.registry.block(address, reason, ident.account_id)
    ctx.engine.blocked_addresses.add(address)
    if fresh:
        await ctx.engine.audit.record(ctx, "registry.address_blocked", detail={"address": address, "reason": reason})
    return {"address": address, "blocked": True, "was_blocked": not fresh}


@handler("registry.unblock")
async def unblock(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    address = _address(payload)
    lifted = await ctx.engine.db.registry.unblock(address, ident.account_id)
    ctx.engine.blocked_addresses.discard(address)
    if lifted:
        await ctx.engine.audit.record(ctx, "registry.address_unblocked", detail={"address": address})
    return {"address": address, "blocked": False, "was_blocked": lifted}


# --- a department's page ---------------------------------------------------------------------------------------------------------


@handler("departments.get")
async def department_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"department_id"} -> the department's page: Admins (with their workstation and key), `vacant`, its machines with health, the worst open issues,
    how it handles reports, open department work, and the Workers who could be promoted into an empty seat."""
    ident = require_role(ctx, "super_user", "admin")
    department_id = ident.department_id if ident.role == "admin" else int_field(payload, "department_id")
    require_department_scope(ident, department_id)
    db = ctx.engine.db
    department = next((d for d in await db.accounts.list_departments() if d["id"] == department_id), None)
    if department is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such department")
    people = (await dispatch(ctx, "registry.accounts", {"department_id": department_id, "roles": ["admin", "worker"]}))["accounts"]
    admins = [a for a in people if a["role"] == "admin"]
    machines = (await dispatch(ctx, "machines.list", {"department_id": department_id}))
    issues = sorted(await db.issues.list(department_id=department_id, open_only=True), key=lambda i: SEV_ORDER.get(i["severity"], 3))
    overview = {d["department_id"]: d for d in (await dispatch(ctx, "overview.departments", {}))["departments"]}.get(department_id, {})
    tasks = [t for t in (await dispatch(ctx, "task.dept_list", {"department_id": department_id}))["tasks"] if t["standing"] != "complete"] if ident.role == "super_user" else []
    return {"department": {"id": department_id, "name": department["name"]}, "admins": admins, "vacant": not admins,
            "machines": machines["machines"], "summary": machines["summary"],
            "issues": [{"id": i["id"], "code": i["code"], "severity": i["severity"], "title": i["title"], "subject": i["subject"], "state": i["state"],
                        "pc_id": i["pc_id"], "opened_at": _iso(i["opened_at"])} for i in issues[:8]],
            "open_issues": len(issues), "median_minutes": overview.get("median_minutes"), "reports": overview.get("reports"),
            "tasks": [{"id": t["id"], "title": t["title"], "standing": t["standing"], "deadline_at": t["deadline_at"]} for t in tasks],
            "workers": [w for w in people if w["role"] == "worker"] if ident.role == "super_user" else []}
