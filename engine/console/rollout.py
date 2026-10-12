"""The rollout gate (Rollout, and the Super User's decision to approve a version).

    rollout.gate     {}                          the current version and who approved it, the version waiting (if any), who runs the current one, the machines
                                                 holding the next approval back (attempts, last error, next try, escalation), who was left out and why,
                                                 adoption day by day, failed installs this week
    updates.stage    {version, note?}            Super User: a version is ready and waits for approval (the packaging pipeline calls the same)
    updates.retry    {pc_id, when: now|idle}     tell a machine to try its update now, or when it is idle (Admin: their department; Super User: any)
    updates.leave_out {pc_id, reason}            Super User: the coming approval does not wait for this machine
    updates.take_back {pc_id}                    Super User: put it back in the gate

A version is approved only when every machine runs the one before it; a machine left out does not hold the gate, and is recorded with the approval
(`updates.approve {version, leave_out?: [pc_id], reason?}` is in engine/updates.py). The version waiting is also one of the Super User's decisions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.console import overview
from engine.dispatch import Context, dispatch, handler
from engine.permissions import int_field, require_department_scope, require_role, str_field
from protocol import ErrorCode, ProtocolError

NEXT = "next"


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def holding(ctx: Context, department_id: int | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """(current version, the machines still holding the gate, the machines left out of it) -- optionally one department's."""
    db = ctx.engine.db
    cur = await db.updates.current_version()
    if cur is None:
        return None, [], []
    behind = [b for b in await db.updates.pcs_behind(cur["id"]) if department_id is None or b["department_id"] == department_id]
    left = {x["pc_id"]: x for x in await db.updates.exclusions(NEXT)}
    return cur, [b for b in behind if b["id"] not in left], [b for b in behind if b["id"] in left]


async def _adoption(ctx: Context, cur: dict[str, Any], pcs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Machines running the current version at the end of each day since it was approved, and who joined that day."""
    db = ctx.engine.db
    start = cur["approved_at"].replace(hour=0, minute=0, second=0, microsecond=0)
    version = cur["version_string"]
    log = [r for r in await db.updates.version_log(start - timedelta(days=60)) if r["pc_id"] in {p["id"] for p in pcs}]
    first_on: dict[int, tuple[datetime, str]] = {}
    for r in log:
        if r["version"] == version:
            first_on.setdefault(r["pc_id"], (r["at"], r["hostname"]))
    days = []
    day = start
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= today:
        end = day + timedelta(days=1)
        state: dict[int, str] = {}
        for r in log:
            if r["at"] < end:
                state[r["pc_id"]] = r["version"]
        days.append({"day": day.date().isoformat(), "n": sum(1 for v in state.values() if v == version),
                     "joined": sorted(h for at, h in first_on.values() if day <= at < end), "note": f"{version} approved" if day == start else None})
        day = end
    return days


@handler("rollout.gate")
async def gate(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Everything the Rollout page shows. The Super User sees the fleet (or one department's); an Admin their own department's."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    department_id = ident.department_id if ident.role == "admin" else int_field(payload, "department_id", required=False)
    cur, blocking, left_out = await holding(ctx, department_id)
    fleet = [m for m in await db.accounts.fleet(department_id=department_id)]
    staged = await db.updates.staged()
    approver = None
    if cur is not None:
        names = await db.accounts.display_names_for(ident.account_id, [cur["approved_by_account_id"]])
        approver = "You" if cur["approved_by_account_id"] == ident.account_id else names.get(cur["approved_by_account_id"])
    online = ctx.engine.online_pc_ids()
    statuses = await db.updates.statuses()
    admins = await db.accounts.active_admins()
    names_by = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in admins]) if admins else {}
    exclusions = {x["pc_id"]: x for x in await db.updates.exclusions(NEXT)}
    by_pc = {m["id"]: m for m in fleet}
    rows = []
    for b in blocking + left_out:
        m = by_pc.get(b["id"], {})
        s = statuses.get(b["id"]) or {}
        dept_admins = [a for a in admins if a["department_id"] == b["department_id"]]
        out_ = b["id"] in exclusions
        escalated = s.get("escalated_at") is not None
        state = "left_out" if out_ else "offline" if b["id"] not in online else "escalated" if escalated else "retrying"
        rows.append({"pc_id": b["id"], "hostname": b["hostname"], "department_id": b["department_id"], "department_name": m.get("department_name"),
                     "running": m.get("agent_version"), "should_run": cur["version_string"] if cur else None, "attempts": s.get("attempt_failure_count") or 0,
                     "last_attempt_at": _iso(s.get("last_attempt_at")), "last_error": s.get("last_error") or ("Not checking in" if b["id"] not in online else None),
                     "next_try": "When it is back online" if b["id"] not in online else "Next idle window", "online": b["id"] in online, "state": state,
                     "escalated_at": _iso(s.get("escalated_at")),
                     "escalated_to": (("you" if ident.role == "super_user" else "the Super User") if not dept_admins else names_by.get(dept_admins[0]["id"])) if escalated else None,
                     "left_out": {"reason": exclusions[b["id"]]["reason"], "at": _iso(exclusions[b["id"]]["at"])} if out_ else None})
    order = {"escalated": 0, "offline": 1, "retrying": 2, "left_out": 3}
    rows.sort(key=lambda r: (order[r["state"]], r["hostname"]))
    failed = await db.updates.failed_installs(datetime.now(timezone.utc) - timedelta(days=7))
    failed = [f for f in failed if f["pc_id"] in by_pc]
    running = sum(1 for m in fleet if cur and m["agent_version"] == cur["version_string"]) if cur else 0
    return {"current": ({"version": cur["version_string"], "approved_at": _iso(cur["approved_at"]), "approved_by": approver} if cur else None),
            "next": ({"version": staged["version_string"], "staged_at": _iso(staged["staged_at"]), "note": staged["note"]} if staged else None),
            "strip": {"running": running, "total": len(fleet), "pct": round(100 * running / len(fleet)) if fleet else None, "holding": len(blocking),
                      "left_out": len(left_out), "failed_installs": sum(f["n"] for f in failed),
                      "failed_hosts": [{"hostname": by_pc[f["pc_id"]]["hostname"], "n": f["n"]} for f in failed]},
            "holding": rows, "adoption": await _adoption(ctx, cur, [{"id": m["id"]} for m in fleet]) if cur else [],
            "can_approve": bool(staged) and not blocking and ident.role == "super_user"}


@handler("updates.stage")
async def stage(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    version = str_field(payload, "version")
    db = ctx.engine.db
    if await db.updates.version_by_string(version):
        raise ProtocolError(ErrorCode.CONFLICT, f"version {version} is approved already")
    note = " ".join(str(payload.get("note") or "").split())[:300]
    fresh = await db.updates.stage(version, note, ident.account_id)
    if fresh:
        await ctx.engine.audit.record(ctx, "update.staged", target_type="versions", detail={"version": version, "note": note})
        await ctx.engine.push_to_role("super_user", "update.staged", {"version": version})
    return {"version": version, "staged": True, "was_staged": not fresh}


@handler("updates.retry")
async def retry(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"pc_id", "when": "now"|"idle"} -- ask a machine that is behind to try its update (now, which may show whoever is signed in a restart prompt;
    or when it is idle, the default). Offline machines can only be told to try when they are back."""
    ident = require_role(ctx, "super_user", "admin")
    pc_id = int_field(payload, "pc_id")
    when = str_field(payload, "when", choices=("now", "idle"), required=False) or "idle"
    db = ctx.engine.db
    pc = await db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such machine")
    require_department_scope(ident, pc["department_id"])
    cur = await db.updates.current_version()
    if cur is None:
        raise ProtocolError(ErrorCode.CONFLICT, "no approved version")
    online = pc_id in ctx.engine.online_pc_ids()
    if when == "now" and not online:
        raise ProtocolError(ErrorCode.UNAVAILABLE, f"{pc['hostname']} is offline; it tries when it is back")
    await db.updates.set_target([pc_id], cur["id"])
    if online:
        await ctx.engine.push_to_pc(pc_id, "update.available", {"version_id": cur["id"], "version": cur["version_string"], **({"now": True} if when == "now" else {})})
    await ctx.engine.audit.record(ctx, "update.retry", target_type="pcs", target_id=pc_id, detail={"version": cur["version_string"], "when": when})
    return {"pc_id": pc_id, "when": when if online else "when it is back", "version": cur["version_string"]}


@handler("updates.leave_out")
async def leave_out(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user")
    pc_id = int_field(payload, "pc_id")
    reason = " ".join(str(payload.get("reason") or "").split())[:300]
    if not reason:
        raise ProtocolError(ErrorCode.INVALID, "leaving a machine out needs a reason")
    if await ctx.engine.db.accounts.pc(pc_id) is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such machine")
    await ctx.engine.db.updates.exclude_from_gate(pc_id, NEXT, reason, ident.account_id)
    await ctx.engine.audit.record(ctx, "update.left_out", target_type="pcs", target_id=pc_id, detail={"reason": reason})
    return {"pc_id": pc_id, "left_out": True}


@handler("updates.take_back")
async def take_back(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user")
    pc_id = int_field(payload, "pc_id")
    lifted = await ctx.engine.db.updates.lift_exclusion(pc_id, NEXT)
    if lifted:
        await ctx.engine.audit.record(ctx, "update.left_in", target_type="pcs", target_id=pc_id)
    return {"pc_id": pc_id, "left_out": False, "was_left_out": lifted}


# --- the decision: approve the version that is waiting ----------------------------------------------------------------------------


async def gate_card(ctx: Context, held: set[str]) -> list[dict[str, Any]]:
    db = ctx.engine.db
    staged = await db.updates.staged()
    if staged is None or f"gate:{staged['version_string']}" in held:
        return []
    version = staged["version_string"]
    cur, blocking, _ = await holding(ctx)
    names = [b["hostname"] for b in blocking]
    options = [overview._option("wait", "Wait for the gate", f"Approve it yourself once {overview._list_names(names)} {'is' if len(names) == 1 else 'are'} on {cur['version_string'] if cur else 'the current version'}. "
                                "You are told when.", "Wait", "Waiting for the gate")] if blocking else []
    if blocking:
        options.append(overview._option("without", f"Approve now, leaving {'it' if len(names) == 1 else f'the {len(names)}'} out",
                                        f"{overview._list_names(names)} stay behind and are recorded as left out, with your reason.", f"Approve {version}",
                                        f"{version} approved without {overview._list_names(names)}", need="reason"))
    else:
        options.append(overview._option("approve", f"Approve {version}", "Every machine runs the current version, so nothing holds it back.", f"Approve {version}", f"{version} approved"))
    why = ("A version is approved only when every machine runs the one before it. "
           + (f"{len(names)} machine{'s' if len(names) != 1 else ''} still {'do' if len(names) != 1 else 'does'}n't." if blocking else "Every machine does."))
    return [{"id": f"gate:{version}", "kind": "version-gate", "severity": "medium", "version": version, "title": f"{version} is ready, and only you can approve it",
             "short": f"Approve {version}", "at": _iso(staged["staged_at"]), "why": why, "pc_ids": [b["id"] for b in blocking], "machines": names, "options": options}]


async def decide_gate(ctx: Context, card: dict[str, Any], option: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    chosen = next((o for o in card["options"] if o["key"] == option), None)
    if chosen is None:
        raise ProtocolError(ErrorCode.INVALID, f"{option!r} is not an option of this decision")
    if option == "wait":
        await overview._hold(ctx, card["id"], "wait", None)
        return chosen["done"], None
    args: dict[str, Any] = {"version": card["version"]}
    if option == "without":
        args.update(leave_out=card["pc_ids"], reason=overview._text(payload, "reason", "a reason"))
    approved = await dispatch(ctx, "updates.approve", args)
    return chosen["done"], approved


overview.CARD_SOURCES.append(gate_card)
overview.DECIDERS["version-gate"] = decide_gate
