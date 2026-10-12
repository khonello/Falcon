"""The Automation and Actions pages: rules with how often they fired and how their runs ended, the runs, and a test on one machine.

    automation.board {days?}                    the rules in scope (name or a sentence, what they watch for and do, who set them, on/off), each with how often it
                                                fired, when last, how its last firing's runs ended and its problems; the strip; runs per day by outcome
    actions.board    {days?}                    the library in scope: each action with the rules that use it, its runs, its last run, its time limit, its own days;
                                                the strip (actions, custom, runs this week, by hand, problems)
    actions.runs     {action_id?, event_id?, hand?, days?, limit?}   recent runs, each with how it ended, how long it took, what it said and what set it off
    control.event_test {event_id, pc_id}        run a rule's actions once on one machine, as if it had fired (recorded as run by hand; not a firing)

Outcomes are Success, Failed, Timed out (it ran out of its time: not a failure), Stopped by you, Running. An Admin sees their department's machines only; an
organisation-wide rule counts just those.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.control.events import _load_event_in_scope, last_fired, outcome_of
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_department_scope, require_role
from protocol import ErrorCode, ProtocolError

OUTCOMES = ("Success", "Failed", "Timed out", "Stopped by you")
PROBLEMS = ("Failed", "Timed out")
WHEN_WORDS = {
    "usb.inserted": "a USB drive is inserted", "usb.removed": "a USB drive is removed", "user.login": "someone signs in", "user.logout": "someone signs out",
    "program.launched": "a program starts", "program.exited": "a program stops", "network.connected": "the network comes up", "network.disconnected": "the network goes down",
    "file.created": "a file is created", "file.modified": "a file changes", "file.moved": "a file is moved", "file.copied": "a file is copied", "file.deleted": "a file is deleted",
    "file.accessed": "a file is opened", "file.attributes_changed": "a file's attributes change", "file.permissions_changed": "a file's permissions change",
    "folder.created": "a folder is created", "folder.moved": "a folder is moved", "folder.deleted": "a folder is deleted",
    "task.started": "a task is started", "task.target_appeared": "a task's file appears", "task.deadline_soft": "a task's soft deadline passes",
    "task.deadline_final": "a task's final deadline passes", "flow.failed": "a flow fails", "resource.violation": "a restricted file turns up where it should not",
    "system.idle": "a machine has been idle", "threshold.cpu": "the processor is busy", "threshold.memory": "memory is nearly full",
    "time.scheduled": "a set time comes", "time.recurring": "a repeating time comes",
}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def when_of(spec: dict[str, Any]) -> str:
    """What a rule watches for, in words: the type's phrase, narrowed by what it matches."""
    etype, match = spec.get("type", ""), spec.get("match") or {}
    base = WHEN_WORDS.get(etype, etype.replace(".", " "))
    if etype in ("program.launched", "program.exited") and match.get("process"):
        return f"{match['process']} {'starts' if etype.endswith('launched') else 'stops'}"
    if etype == "threshold.cpu" and match.get("percent"):
        return f"the processor is at {match['percent']}% or more" + (f" for {match['duration_s'] // 60} minutes" if match.get("duration_s", 0) >= 60 else "")
    if etype == "threshold.memory" and match.get("percent"):
        return f"memory is at {match['percent']}% or more"
    if etype == "system.idle" and match.get("seconds"):
        return f"a machine has been idle for {match['seconds'] // 60} minutes"
    if etype == "time.recurring" and match.get("at"):
        return f"it is {match['at']}"
    if etype.startswith("file.") and match.get("tier"):
        return f"{base} ({match['tier']} file)"
    return base


def kind_of(etype: str) -> str:
    return "Schedule" if etype.startswith("time.") else "Level" if etype.startswith("threshold.") or etype == "system.idle" else "Event"


def _day(at: datetime) -> str:
    return at.astimezone(timezone.utc).date().isoformat()


def _days(now: datetime, n: int) -> list[str]:
    return [(now - timedelta(days=i)).date().isoformat() for i in range(n - 1, -1, -1)]


def _per_day(runs: list[dict[str, Any]], days: list[str]) -> list[dict[str, Any]]:
    out = {d: {"day": d, **dict.fromkeys(OUTCOMES, 0)} for d in days}
    for r in runs:
        d, o = _day(r["started_at"]), outcome_of(r)
        if d in out and o in OUTCOMES:
            out[d][o] += 1
    return list(out.values())


def _summary(runs: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for r in runs:
        counts[outcome_of(r)] = counts.get(outcome_of(r), 0) + 1
    ok = counts.get("Success", 0)
    if len(counts) == 1 and ok:
        return "Succeeded" if ok == 1 else f"All {ok} succeeded"
    return ", ".join(f"{counts[k]} {k.lower()}" for k in ("Timed out", "Failed", "Stopped by you", "Running", "Success") if counts.get(k))


def _run_view(r: dict[str, Any], rules: dict[int, str]) -> dict[str, Any]:
    took = int((r["ended_at"] - r["started_at"]).total_seconds()) if r["ended_at"] else None
    return {"run_id": r["id"], "action_id": r["action_id"], "action": r["action_name"] or r["builtin_type"] or "Action", "pc_id": r["pc_id"], "host": r["hostname"],
            "at": _iso(r["started_at"]), "took_s": took, "limit_s": r["timeout_seconds"], "outcome": outcome_of(r), "summary": r["summary"], "exit": r["exit_code"],
            "has_image": bool(r.get("has_image")), "event_id": r["event_id"], "by": f"rule: {rules.get(r['event_id'], 'a rule')}" if r["event_id"] else "hand"}


async def _scope(ctx: Context, payload: dict[str, Any]) -> tuple[int | None, datetime, int, datetime]:
    ident = require_role(ctx, "super_user", "admin")
    days = max(1, min(int_field(payload, "days", required=False) or 7, 30))
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (ident.department_id if ident.role == "admin" else None), start, days, now


@handler("automation.board")
async def automation_board(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = ctx.identity
    department_id, start, days, now = await _scope(ctx, payload)
    db = ctx.engine.db
    defs = await db.control.events_in_department(department_id) if department_id is not None else await db.control.event_definitions(enabled_only=False)
    runs = await db.control.runs_since(start, department_id=department_id)
    firings = await db.control.firing_counts(start)
    mine = {p["id"] for p in await db.accounts.pcs_in_department(department_id)} if department_id is not None else None
    makers = {d["created_by_account_id"] for d in defs}
    names = await db.accounts.display_names_for(ident.account_id, sorted(makers)) if makers else {}
    rules = []
    for d in defs:
        spec = d["condition_spec"] or {}
        fired = [f for f in firings if f["event_id"] == d["id"] and (mine is None or f["pc_id"] in mine or not f["pc_id"])]
        mine_runs = [r for r in runs if r["event_id"] == d["id"]]
        last = max((f["last"] for f in fired), default=None)
        latest = [r for r in mine_runs if abs((r["started_at"] - mine_runs[0]["started_at"]).total_seconds()) < 90] if mine_runs else []
        actions = await db.control.actions_for_event(d["id"])
        rules.append({"event_id": d["id"], "name": d.get("name") or (when_of(spec)[0].upper() + when_of(spec)[1:]), "named": bool(d.get("name")), "type": spec.get("type"),
                      "kind": kind_of(spec.get("type", "")), "when": when_of(spec), "scope": "every machine" if not spec.get("pc_ids") else f"{len(spec['pc_ids'])} machine(s)",
                      "actions": [{"action_id": a["id"], "name": a.get("name") or a.get("builtin_type")} for a in actions], "on": d["enabled"],
                      "owner": "Super User" if d["org_wide"] else names.get(d["created_by_account_id"]), "org_wide": bool(d["org_wide"]),
                      "read_only": ident.role == "admin" and bool(d["org_wide"]),
                      "fired": sum(f["n"] for f in fired), "last_fired_at": _iso(last) or last_fired(d["id"]),
                      "last_run": _summary(latest) if latest else None, "last_run_problem": any(outcome_of(r) in PROBLEMS for r in latest),
                      "problems": sum(1 for r in mine_runs if outcome_of(r) in PROBLEMS)})
    problems = sum(1 for r in runs if outcome_of(r) in PROBLEMS)
    return {"rules": rules, "days": _per_day(runs, _days(now, days)), "period_days": days,
            "strip": {"rules": len(rules), "on": sum(1 for r in rules if r["on"]), "fired": sum(r["fired"] for r in rules), "problems": problems,
                      "set_by_super_user": sum(1 for r in rules if r["org_wide"])}}


async def _libraries(ctx: Context, department_id: int | None) -> list[dict[str, Any]]:
    db = ctx.engine.db
    return await db.control.actions_in_department(department_id) if department_id is not None else await db.control.actions()


@handler("actions.board")
async def actions_board(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    department_id, start, days, now = await _scope(ctx, payload)
    db = ctx.engine.db
    library = await _libraries(ctx, department_id)
    runs = await db.control.runs_since(start, department_id=department_id)
    links = await db.control.event_links()
    out = []
    for a in library:
        mine = [r for r in runs if r["action_id"] == a["id"]]
        used = [{"event_id": l["event_id"], "name": l["event_name"] or when_of({"type": l["event_type"]})} for l in links if l["action_id"] == a["id"]]
        last = mine[0] if mine else None
        out.append({"action_id": a["id"], "name": a.get("name") or a.get("builtin_type"), "kind": a["action_kind"], "builtin_type": a.get("builtin_type"),
                    "language": a.get("custom_script_language"), "description": a.get("description"), "timeout_s": a["timeout_seconds"], "used_by": used,
                    "runs": len(mine), "by_hand": sum(1 for r in mine if not r["event_id"]), "problems": sum(1 for r in mine if outcome_of(r) in PROBLEMS),
                    "last_run": {"outcome": outcome_of(last), "at": _iso(last["started_at"]), "host": last["hostname"]} if last else None,
                    "days": _per_day(mine, _days(now, days))})
    return {"actions": out, "days": _per_day(runs, _days(now, days)), "period_days": days,
            "strip": {"actions": len(out), "control": sum(1 for a in out if a["kind"] == "control"), "monitoring": sum(1 for a in out if a["kind"] == "monitoring"),
                      "custom": sum(1 for a in out if a["kind"] == "custom"), "runs": len(runs), "by_hand": sum(1 for r in runs if not r["event_id"]),
                      "problems": sum(1 for r in runs if outcome_of(r) in PROBLEMS)}}


@handler("actions.runs")
async def actions_runs(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    department_id, start, _, _ = await _scope(ctx, payload)
    db = ctx.engine.db
    action_id = int_field(payload, "action_id", required=False)
    event_id = int_field(payload, "event_id", required=False)
    limit = max(1, min(int_field(payload, "limit", required=False) or 50, 500))
    runs = await db.control.runs_since(start, department_id=department_id)
    found = [r for r in runs if (action_id is None or r["action_id"] == action_id) and (event_id is None or r["event_id"] == event_id)
             and (not payload.get("hand") or not r["event_id"])]
    labels = {d["id"]: d.get("name") or when_of(d["condition_spec"] or {}) for d in await db.control.event_definitions(enabled_only=False)}
    return {"runs": [_run_view(r, labels) for r in found[:limit]], "total": len(found)}


@handler("control.event_test")
async def event_test(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"event_id", "pc_id"} -- run what the rule does, once, on one machine it applies to. Allowed on a rule you cannot change (the Super User's, seen in an
    Admin's console): it only runs its actions where you may. Recorded as run by hand, not as the rule firing."""
    ident = require_role(ctx, "super_user", "admin")
    event_id = int_field(payload, "event_id")
    pc_id = int_field(payload, "pc_id")
    ev = await _load_event_in_scope(ctx, event_id, write=False)
    db = ctx.engine.db
    pc = await db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such machine")
    require_department_scope(ident, pc["department_id"])
    named = (ev["condition_spec"] or {}).get("pc_ids")
    if named and pc_id not in named:
        raise ProtocolError(ErrorCode.INVALID, "this rule does not apply to that machine")
    if pc_id not in ctx.engine.online_pc_ids():
        raise ProtocolError(ErrorCode.UNAVAILABLE, f"{pc['hostname']} is offline")
    from engine.control import executions

    started = []
    for action in await db.control.actions_for_event(event_id):
        execution_id = await executions.start(ctx.engine, action, None, pc_id, actor=ctx)
        started.append({"action_id": action["id"], "execution_id": execution_id})
    if not started:
        raise ProtocolError(ErrorCode.CONFLICT, "this rule has no actions to run")
    await ctx.engine.audit.record(ctx, "event.tested", target_type="event_definitions", target_id=event_id, pc_id=pc_id, detail={"executions": started})
    return {"event_id": event_id, "pc_id": pc_id, "runs": started}
