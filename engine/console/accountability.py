"""Accountability: recording the departures from the rules (engine/console/rules.py).

The combos tell this module what happened; it decides whether a rule was broken and records a **deviation** that someone can be asked about.

  * *never* rules: the combo calls `never(engine, trigger, ...)` when the thing happens (a copy of a restricted file, a machine
    presenting another name, a session refused because the machine is held); each enabled rule on that trigger records a deviation.
  * *follow* rules: the combo calls `watch(engine, trigger, ...)` when the trigger happens (a ping, a report, a version approved, a task
    given, a department left without an Admin); a watch is opened, due `within` minutes later. The sweep checks, when it is due, whether
    what must follow has happened -- and if not (or if it came late) records a deviation.
  * *limit* rules: the sweep counts what the audit trail shows per subject in the rolling period and records a deviation for each subject over
    the line (once per period).

A deviation says what was expected and what happened; the people it names are held as ids and named for whoever reads it (`{who}` in the
text), because a name is the reader's own (Display Names never propagate). Whatever the rule says to do about it -- report it to the Super
User, tell the department's Admin, run an Action -- is done here and nothing else runs silently.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.console.rules import EXPECTS, PERIODS, READINGS, TRIGGERS, _dur, in_scope

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)


async def _active(engine: Engine, shape: str, key: str, value: str) -> list[dict[str, Any]]:
    """The enabled rules of a shape whose spec has `key == value`."""
    if not engine.db.connected:
        return []
    return [r for r in await engine.db.rules.rules() if r["shape"] == shape and r["enabled"] and r["spec"].get(key) == value]


async def deviate(engine: Engine, rule: dict[str, Any], *, kind: str, short: str, expected: str, happened: str, severity: str | None = None,
                  subject_account_id: int | None = None, subject_pc_id: int | None = None, subject_department_id: int | None = None,
                  pc_id: int | None = None, department_id: int | None = None, value: float | None = None,
                  detail: dict[str, Any] | None = None, source_key: str | None = None, at: datetime | None = None) -> int | None:
    """Record one departure from a rule, once. None when the rule does not apply to this subject, or it was already recorded."""
    if department_id is None:
        department_id = subject_department_id
    if not in_scope(rule["spec"], kind, department_id):
        return None
    db = engine.db
    deviation_id = await db.rules.record_deviation({
        "rule_id": rule["id"], "rule_snapshot": {"code": rule["code"], "name": rule["name"], "shape": rule["shape"], "spec": rule["spec"]},
        "severity": severity or rule["spec"].get("severity") or "medium", "kind": kind, "subject_account_id": subject_account_id,
        "subject_pc_id": subject_pc_id, "subject_department_id": subject_department_id, "department_id": department_id, "pc_id": pc_id,
        "at": at or datetime.now(timezone.utc), "short": short, "expected": expected, "happened": happened, "value": value,
        "detail": detail or {}, "source_key": source_key})
    if deviation_id is None:
        return None
    deviation = await db.rules.deviation(deviation_id)
    assert deviation is not None
    await engine.audit.record(None, "deviation.raised", target_type="deviations", target_id=deviation_id, pc_id=pc_id,
                              detail={"code": deviation["code"], "rule": rule["code"], "kind": kind, "severity": deviation["severity"],
                                      "department_id": department_id})
    payload = {"deviation_id": deviation_id, "code": deviation["code"], "rule_code": rule["code"], "rule_name": rule["name"],
               "severity": deviation["severity"], "kind": kind, "department_id": department_id, "pc_id": pc_id}
    await engine.push_to_role("super_user", "deviation.raised", payload)
    await _respond(engine, rule, deviation, payload)
    return deviation_id


async def _respond(engine: Engine, rule: dict[str, Any], deviation: dict[str, Any], payload: dict[str, Any]) -> None:
    """What the rule says to do when it is broken: report it, tell the department's Admin, run an Action. Nothing else."""
    resp = rule["spec"].get("resp") or {}
    if resp.get("report"):
        from engine.hierarchy import reports

        category = "about_admin" if deviation["kind"] == "admin" else "deviation"
        await reports.emit(engine, category, source_table="deviations", source_id=deviation["id"],
                           summary=f"{rule['name']}: {deviation['short'].replace('{who}', 'someone')}")
    if resp.get("admin") and deviation["kind"] != "admin" and deviation["department_id"] is not None:
        await engine.push_to_role("admin", "deviation.raised", payload, department_id=deviation["department_id"])    # never about an Admin
    if resp.get("action") and resp.get("action_id") and deviation["pc_id"] is not None:
        from engine.control import executions

        action = await engine.db.control.action(resp["action_id"])
        if action and not action.get("archived_at"):
            await executions.start(engine, action, None, deviation["pc_id"])


async def never(engine: Engine, trigger: str, *, kind: str, short: str, expected: str, happened: str, severity: str | None = None,
                subject_account_id: int | None = None, subject_pc_id: int | None = None, subject_department_id: int | None = None,
                pc_id: int | None = None, department_id: int | None = None, detail: dict[str, Any] | None = None,
                source_key: str | None = None) -> int | None:
    """A 'never' thing happened: every enabled rule on this trigger records a deviation. Returns the first one recorded."""
    first = None
    for rule in await _active(engine, "never", "trigger", trigger):
        found = await deviate(engine, rule, kind=kind, short=short, expected=expected, happened=happened, severity=severity,
                              subject_account_id=subject_account_id, subject_pc_id=subject_pc_id, subject_department_id=subject_department_id,
                              pc_id=pc_id, department_id=department_id, detail=detail, source_key=source_key)
        first = first or found
    return first


async def watch(engine: Engine, trigger: str, *, target_table: str, target_id: int, kind: str, label: str,
                account_id: int | None = None, pc_id: int | None = None, department_id: int | None = None,
                extra: dict[str, Any] | None = None) -> int:
    """A trigger of a 'follow' rule happened: open a watch, due `within` minutes later, for each enabled rule on it. Returns how many."""
    opened = 0
    now = datetime.now(timezone.utc)
    for rule in await _active(engine, "follow", "trigger", trigger):
        if not in_scope(rule["spec"], kind, department_id):
            continue
        subject = {"kind": kind, "account_id": account_id, "pc_id": pc_id, "department_id": department_id, "label": label, **(extra or {})}
        if await engine.db.rules.open_watch(rule["id"], now + timedelta(minutes=rule["spec"]["within"]), rule["spec"]["expect"],
                                            target_table, target_id, subject):
            opened += 1
    return opened


# --- when a watch is due -------------------------------------------------------------------------

async def _fulfilled_at(engine: Engine, w: dict[str, Any]) -> datetime | None:
    """When what the rule requires happened, or None if it has not."""
    db = engine.db
    expect, subj = w["expect"], w["subject"]
    if expect == "answer":
        ping = await db.assistance.get_ping(w["target_id"])
        return ping["addressed_at"] if ping else None
    if expect == "addressed":
        return await db.rules.addressed_by_department(w["target_id"], subj.get("department_id"))
    if expect == "updated":
        st = await db.updates.status_for_pc(w["target_id"])
        if st and subj.get("version_id") and st["current_version_id"] == subj["version_id"]:
            return max(st["last_attempt_at"] or w["opened_at"], w["opened_at"]) if st["last_attempt_at"] else w["opened_at"]
        return None
    if expect == "seen":
        return await db.rules.dept_task_seen_at(int(w["target_table"].split(":")[1]), w["target_id"])
    if expect == "appoint":
        return await db.rules.first_admin_since(subj.get("department_id"), w["opened_at"])
    return None


async def sweep(engine: Engine, now: datetime | None = None) -> int:
    """Check the watches that have come due and the limit rules. Returns how many deviations were recorded."""
    if not engine.db.connected:
        return 0
    now = now or datetime.now(timezone.utc)
    recorded = 0
    rules = {r["id"]: r for r in await engine.db.rules.rules()}
    for w in await engine.db.rules.watches_due(now):
        rule = rules.get(w["rule_id"])
        if rule is None or not rule["enabled"]:
            await engine.db.rules.close_watch(w["id"], "kept")
            continue
        done = await _fulfilled_at(engine, w)
        if done is not None and done <= w["due_at"]:
            await engine.db.rules.close_watch(w["id"], "kept")
            continue
        elapsed = ((done or now) - w["opened_at"]).total_seconds() / 60
        spec, s = rule["spec"], w["subject"]
        label = s.get("label", "")
        happened = (f"Done after {_dur(max(1, round(elapsed)))}" if done else f"Still not done after {_dur(max(1, round(elapsed)))}")
        found = await deviate(
            engine, rule, kind=s["kind"], short=f"{label}: {EXPECTS[spec['expect']].lower()} did not happen in time",
            expected=f"{EXPECTS[spec['expect']]} within {_dur(spec['within'])}", happened=happened,
            subject_account_id=s.get("account_id"), subject_pc_id=s.get("pc_id") if s["kind"] == "pc" else None,
            subject_department_id=s.get("department_id") if s["kind"] == "dept" else None, pc_id=s.get("pc_id"),
            department_id=s.get("department_id"), value=round(elapsed, 1),
            detail={"trigger": spec["trigger"], "after": TRIGGERS[spec["trigger"]], "target": [w["target_table"], w["target_id"]]},
            source_key=f"watch:{w['id']}", at=w["due_at"])
        await engine.db.rules.close_watch(w["id"], "broken", found)
        recorded += int(found is not None)
    return recorded + await _sweep_limits(engine, now, rules)


async def _sweep_limits(engine: Engine, now: datetime, rules: dict[int, dict[str, Any]]) -> int:
    recorded = 0
    for rule in rules.values():
        if rule["shape"] != "limit" or not rule["enabled"]:
            continue
        spec = rule["spec"]
        window = PERIODS[spec["limit"]["per"]]
        bucket = int(now.timestamp() // window.total_seconds())
        for row in await engine.db.audit.count_by(spec["reading"], now - window):
            if row["n"] <= spec["limit"]["n"]:
                continue
            account, pc_id = row["subject"], row["pc_id"]
            acct = await engine.db.accounts.by_id(account) if account else None
            pc = await engine.db.accounts.pc(pc_id) if pc_id else None
            kind = "pc" if spec["reading"] == "failedauth" else "admin"
            lim = spec["limit"]
            found = await deviate(
                engine, rule, kind=kind, short=f"{{who}}: {READINGS[spec['reading']].lower()}, {row['n']} in the last {lim['per']}",
                expected=f"{READINGS[spec['reading']]}: {'none' if lim['n'] == 0 else 'no more than ' + str(lim['n'])} per {lim['per']}",
                happened=f"{row['n']} in the last {lim['per']}", subject_account_id=account if kind == "admin" else None,
                subject_pc_id=pc_id if kind == "pc" else None, pc_id=pc_id, department_id=(acct or pc or {}).get("department_id"),
                value=float(row["n"]), detail={"reading": spec["reading"], "period": lim["per"]},
                source_key=f"limit:{account}:{pc_id}:{bucket}")
            recorded += int(found is not None)
    return recorded
