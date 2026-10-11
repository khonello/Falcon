"""The fleet and a machine's page (Machines, Overview's fleet map, Registry; the Super User's Departments).

    machines.list {department_id?}                  every machine in scope, each with its health
    machines.get  {pc_id, range?: 1h|6h|24h|7d}     one machine: facts, four metric series, processes, sessions, files, events

Scope: the Super User sees every machine (or one department's); an Admin their own department's. People are named the way the
caller names them. "Online" is the machine's client holding a connection now; "using it" is its own person's session.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.console.feed import describe_many
from engine.console.health import health_of, open_signals
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_department_scope, require_role
from protocol import ErrorCode, ProtocolError

RANGES = {"1h": (timedelta(hours=1), 10), "6h": (timedelta(hours=6), 10), "24h": (timedelta(hours=24), 30),
          "7d": (timedelta(days=7), 180)}
SESSION_TYPE = {"native": "owner", "traversal": "admin", "assisted_access": "assist"}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _machines(ctx: Context, department_id: int | None, pc_id: int | None = None) -> list[dict[str, Any]]:
    from engine.control import events as control_events

    ident = ctx.identity
    db = ctx.engine.db
    found = await db.accounts.fleet(department_id=department_id, pc_id=pc_id)
    online = ctx.engine.online_pc_ids()
    current = await db.updates.current_version()
    signals = await open_signals(db, [m["id"] for m in found])
    people = {m["account_id"] for m in found if m["account_id"]} | {m["occupant_account_id"] for m in found if m["occupant_account_id"]}
    names = await db.accounts.display_names_for(ident.account_id, sorted(people)) if people else {}
    out = []
    for m in found:
        is_online = m["id"] in online
        health, note = health_of(is_online, signals[m["id"]])
        occupant = m["occupant_account_id"]
        owner_in = occupant is not None and occupant == m["account_id"]
        metrics = control_events.latest_metrics(m["id"]) or {}
        out.append({
            "pc_id": m["id"], "hostname": m["hostname"], "department_id": m["department_id"], "department_name": m["department_name"],
            "pc_type": m["pc_type"], "key_generation": m["key_generation"],
            "owner": {"account_id": m["account_id"], "name": names.get(m["account_id"])} if m["account_id"] else None,
            "user": names.get(m["account_id"]) if owner_in and is_online else None,
            "online": is_online, "last_seen_at": _iso(m["last_seen_at"]), "ip": m["last_ip"], "os": m["os"],
            "version": m["agent_version"], "behind": bool(current and m["agent_version"] and m["agent_version"] != current["version_string"]),
            "agent_started_at": _iso(m["agent_started_at"]), "health": health, "note": note,
            "open_issues": len(signals[m["id"]]),
            "held_by": names.get(occupant) if occupant is not None and not owner_in else None,
            "held_via": SESSION_TYPE.get(m["occupied_via"]) if occupant is not None and not owner_in else None,
            "held_since": _iso(m["session_entered_at"]) if occupant is not None and not owner_in else None,
            "held_by_you": occupant == ident.account_id and occupant != m["account_id"],
            "session_id": m["session_id"],
            "cpu": metrics.get("cpu"), "memory": metrics.get("memory"), "disk": metrics.get("disk"), "idle_s": metrics.get("idle_s"),
            "foreground": metrics.get("foreground"),
        })
    return out


@handler("machines.list")
async def machines_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"department_id"?} -> {"machines": [...], "summary": {machines, online, behind, by_health}, "current_version"}.
    An Admin's list is always their own department's."""
    ident = require_role(ctx, "super_user", "admin")
    department_id = ident.department_id if ident.role == "admin" else int_field(payload, "department_id", required=False)
    found = await _machines(ctx, department_id)
    by_health: dict[str, int] = {}
    for m in found:
        by_health[m["health"]] = by_health.get(m["health"], 0) + 1
    current = await ctx.engine.db.updates.current_version()
    return {"machines": found, "current_version": current["version_string"] if current else None,
            "summary": {"machines": len(found), "online": sum(1 for m in found if m["online"]),
                        "behind": sum(1 for m in found if m["behind"]), "by_health": by_health}}


@handler("machines.get")
async def machines_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """One machine's page. {"pc_id", "range"?: "1h"|"6h"|"24h" (default)|"7d"} -> the machine (as in the list) plus:
    `series` {cpu, memory, disk, net_kbps: [{at, v}]}, `processes` {at, items: [{pid, name, cpu, memory_mb, user}]} as the machine
    last reported them, `sessions` (the last seven days: who, how, when, how long), `files` (what the index holds here, by tier) and
    `events` (the last dozen things recorded about it)."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    pc_id = int_field(payload, "pc_id")
    pc = await db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such machine")
    require_department_scope(ident, pc["department_id"])
    window = str(payload.get("range") or "24h")
    if window not in RANGES:
        raise ProtocolError(ErrorCode.INVALID, f"range must be one of {sorted(RANGES)}")
    span, bucket = RANGES[window]
    now = datetime.now(timezone.utc)
    machine = (await _machines(ctx, None, pc_id))[0]
    samples = await db.control.metric_series(pc_id, now - span, now + timedelta(minutes=1), bucket)
    series = {k: [{"at": _iso(s["at"]), "v": round(s[k], 1)} for s in samples if s[k] is not None]
              for k in ("cpu", "memory", "disk", "net_kbps")}
    from engine.control import inventory

    sessions = await db.sessions.for_pc(pc_id, now - timedelta(days=7))
    people = {s["occupant_account_id"] for s in sessions}
    names = await db.accounts.display_names_for(ident.account_id, sorted(people)) if people else {}
    owner_id = (machine["owner"] or {}).get("account_id")
    session_rows = [{"session_id": s["id"], "who": names.get(s["occupant_account_id"]),
                     "type": "you" if s["occupant_account_id"] == ident.account_id and s["occupant_account_id"] != owner_id
                     else SESSION_TYPE.get(s["occupied_via"]),
                     "started_at": _iso(s["entered_at"]), "ended_at": _iso(s["ended_at"]),
                     "ended_reason": s["ended_reason"],
                     "seconds": int(((s["ended_at"] or now) - s["entered_at"]).total_seconds())} for s in sessions]
    events = await db.audit.feed(since=now - timedelta(days=7), until=now + timedelta(minutes=1), kinds=None, pc_id=pc_id,
                                 department_id=None, actor_account_id=None, before_id=None, limit=12)
    return {"machine": machine, "range": window, "series": series, "processes": inventory.processes_of(pc_id),
            "sessions": session_rows, "files": await db.file_index.summary_for_pc(pc_id),
            "events": await describe_many(db, events, ident.account_id), "generated_at": now.isoformat()}

