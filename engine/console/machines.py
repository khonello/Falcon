"""The fleet and a machine's page (Machines, Overview's fleet map, Registry; the head of the organisation's Departments).

    machines.list {department_id?}                  every machine in scope, each with its health
    machines.get  {pc_id, range?: 1h|6h|24h|7d}     one machine: facts, four metric series, processes, sessions, files, events

Scope: the head of the organisation sees every machine (or one department's); an Admin their own department's. People are named the way the
caller names them. "Online" is the machine's client holding a connection now; "using it" is its own person's session.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.console.feed import describe_many
from engine.console.health import health_of, open_signals
from engine.dispatch import Context, handler
from engine.permissions import int_field, kept, require_department_scope, require_role, str_field
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
    department_id = ident.department_id if kept(ident) else int_field(payload, "department_id", required=False)
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
    processes = inventory.processes_of(pc_id)
    return {"machine": machine, "range": window, "series": series, "processes": processes,
            "running_now": _running_now(processes), "about": _about(pc, machine),
            **await _days(ctx, pc_id, machine, now),
            "sessions": session_rows, "files": await db.file_index.summary_for_pc(pc_id),
            "events": await describe_many(db, events, ident.account_id), "generated_at": now.isoformat()}


RUNNING_NOW = 7


def _running_now(processes: dict[str, Any] | None) -> dict[str, Any] | None:
    """The seven busiest programs, by processor then memory, from the machine's latest snapshot. Windows' own processes and the Worker
    are never in the snapshot (worker_client/protected.py), so they can never be ended from here."""
    if not processes:
        return None
    busiest = sorted(processes["items"], key=lambda p: (-p["cpu"], -p["memory_mb"]))[:RUNNING_NOW]
    return {"at": processes["at"], "items": busiest}


def _about(pc: dict[str, Any], machine: dict[str, Any]) -> dict[str, Any]:
    """About the machine, as its Worker said when it last connected; the registered date is the PC's own."""
    return {"os": pc["os"], "memory_total_mb": pc["memory_total_mb"], "disk_total_gb": round(pc["disk_total_gb"], 1) if pc["disk_total_gb"] is not None else None,
            "disk_percent": machine["disk"], "boot_at": _iso(pc["boot_at"]), "registered_at": _iso(pc["created_at"])}


async def _days(ctx: Context, pc_id: int, machine: dict[str, Any], now: datetime) -> dict[str, Any]:
    """At the keyboard (in use or idle now, and today's quarter hours of use) and check-ins this week (one yes or no per day, today
    last). Days are the Engine host's local days, as the quarter hours are."""
    from engine.control import events as control_events

    today, _ = control_events.quarter_of(now)
    rows = {r["day"]: r for r in await ctx.engine.db.accounts.days(pc_id, today - timedelta(days=7))}
    idle_s = machine["idle_s"]
    in_use = machine["online"] and idle_s is not None and idle_s < control_events.IN_USE_IDLE_S
    return {"keyboard": {"state": "offline" if not machine["online"] else "in_use" if in_use else "idle", "idle_s": idle_s,
                         "day": today.isoformat(), "quarters": sorted((rows.get(today) or {}).get("used_quarters") or [])},
            "check_ins": [{"day": (today - timedelta(days=n)).isoformat(), "yes": (today - timedelta(days=n)) in rows}
                          for n in range(7, -1, -1)]}


@handler("machines.end_program")
async def end_program(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"pc_id", "name"} -- End on a running program, then a notice on the person's screen saying IT ended it. The Worker refuses what is on its protected list."""
    from engine.console.system_actions import run_on_machine

    ident = require_role(ctx, "super_user", "admin")
    pc_id = int_field(payload, "pc_id")
    name = str_field(payload, "name")
    pc = await ctx.engine.db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such machine")
    require_department_scope(ident, pc["department_id"])
    ended = await run_on_machine(ctx, "kill_process", {"name": name}, pc_id, name=f"End {name}")
    told = await run_on_machine(ctx, "notify", {"message": f"Your IT Admin ended {name}."}, pc_id, name=f"Say {name} was ended")
    return {"pc_id": pc_id, "execution_id": ended, "notice_execution_id": told}
