"""Accountability: the deviations (the Super User's Accountability page, Overview's *Worth a look*).

A deviation is a departure from a rule that someone can be asked about: the rule **as it was when it happened**, what was expected and what
happened, who or what it concerns, the timeline around it, the evidence the record shows -- and an outcome a person gives it. The system
never states a cause: it lists what is in the record ("an Admin entered the machine two minutes earlier") and only a person's written note
makes it an explanation.

    deviations.list    {kind?, rule_id?, outcome?, day?, department_id?, days? (default 7), group?: rule|department|subject}
    deviations.get     {deviation_id}                          the record, its timeline and its evidence
    deviations.outcome {deviation_id, outcome, note?}          explained / accepted (a note is required) / escalated / dismissed / open

Super User only: Accountability is the Super User's page. An Admin sees the rules ("set by the Super User") but not the deviations about them.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.console.feed import describe_many
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from protocol import ErrorCode, ProtocolError

OUTCOMES = ("open", "explained", "accepted", "escalated", "dismissed")
OUTCOME_LABEL = {"open": "Open", "explained": "Explained", "accepted": "Accepted", "escalated": "Escalated", "dismissed": "Dismissed"}
NEEDS_NOTE = ("explained", "accepted")
KINDS = ("pc", "worker", "admin", "dept")
KIND_LABEL = {"pc": "PC", "worker": "Worker", "admin": "Admin", "dept": "Department"}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _view(ctx: Context, found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = ctx.engine.db
    ids = {d["subject_account_id"] for d in found if d["subject_account_id"]} | {d["outcome_by_account_id"] for d in found if d["outcome_by_account_id"]}
    names = await db.accounts.display_names_for(ctx.identity.account_id, sorted(ids)) if ids else {}
    out = []
    for d in found:
        if d["kind"] in ("worker", "admin"):
            who = names.get(d["subject_account_id"]) or "someone"
        elif d["kind"] == "pc":
            who = d["hostname"] if d["pc_id"] == d["subject_pc_id"] else (await db.accounts.pc(d["subject_pc_id"]) or {}).get("hostname", "a machine")
        else:
            who = d["department_name"] or "a department"
        sub = {"worker": f"{d['hostname'] or ''} · {d['department_name'] or ''}".strip(" ·"), "admin": f"{d['department_name'] or ''} Admin".strip(),
               "pc": d["department_name"] or "", "dept": ""}[d["kind"]]
        out.append({
            "id": d["id"], "code": d["code"], "rule": {"id": d["rule_id"], "code": d["rule_code"], "name": d["rule_snapshot"].get("name", d["rule_name"]),
                                                       "locked": d["rule_builtin"], "sentence_now": d["rule_name"]},
            "severity": d["severity"], "kind": d["kind"], "kind_label": KIND_LABEL[d["kind"]], "who": who, "who_sub": sub,
            "department_id": d["department_id"], "department_name": d["department_name"], "pc_id": d["pc_id"], "host": d["hostname"],
            "at": _iso(d["at"]), "value": d["value"], "short": d["short"].replace("{who}", who), "expected": d["expected"], "happened": d["happened"],
            "outcome": d["outcome"], "outcome_label": OUTCOME_LABEL[d["outcome"]], "note": d["note"],
            "by": names.get(d["outcome_by_account_id"]) if d["outcome_by_account_id"] else None, "decided_at": _iso(d["outcome_at"])})
    return out


@handler("deviations.list")
async def deviations_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """-> {"deviations": [...] (open first, then the ones dealt with, each most serious first), "summary": {total, open, by_kind},
    "by_rule": [{rule_id, code, name, n, open}], "per_day": [{day, open, dealt, by_severity}], "groups"?: [{key, label, n, open}]}.
    `day` (ISO date) limits the list to one day; `days` is how far back to look (default 7). The strip's figures are over the whole period
    whatever `kind`/`rule_id` narrow the list to."""
    require_role(ctx, "super_user")
    db = ctx.engine.db
    days = min(int_field(payload, "days", required=False) or 7, 90)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    kind = str_field(payload, "kind", required=False, choices=KINDS)
    outcome = str_field(payload, "outcome", required=False, choices=OUTCOMES)
    everything = await _view(ctx, await db.rules.deviations(since=since, department_id=int_field(payload, "department_id", required=False)))
    narrowed = [d for d in everything if (not kind or d["kind"] == kind) and (not outcome or d["outcome"] == outcome)
                and (not payload.get("rule_id") or d["rule"]["id"] == payload["rule_id"])]
    if payload.get("day"):
        try:
            day = datetime.fromisoformat(str(payload["day"])).date()
        except ValueError as exc:
            raise ProtocolError(ErrorCode.INVALID, "day must be an ISO date") from exc
        narrowed = [d for d in narrowed if datetime.fromisoformat(d["at"]).astimezone(timezone.utc).date() == day]
    by_kind = {k: sum(1 for d in everything if d["kind"] == k and d["outcome"] == "open") for k in KINDS}
    by_rule: dict[int, dict[str, Any]] = {}
    for d in everything:
        r = by_rule.setdefault(d["rule"]["id"], {"rule_id": d["rule"]["id"], "code": d["rule"]["code"], "name": d["rule"]["name"], "n": 0, "open": 0})
        r["n"] += 1
        r["open"] += int(d["outcome"] == "open")
    per_day: dict[str, dict[str, Any]] = {}
    for r in await db.rules.deviation_days(since):
        day_key = r["day"].date().isoformat()
        p = per_day.setdefault(day_key, {"day": day_key, "open": 0, "dealt": 0, "by_severity": {}})
        p["open" if r["is_open"] else "dealt"] += r["n"]
        p["by_severity"][r["severity"]] = p["by_severity"].get(r["severity"], 0) + r["n"]
    out: dict[str, Any] = {"deviations": narrowed, "summary": {"total": len(everything), "open": sum(1 for d in everything if d["outcome"] == "open"), "by_kind": by_kind},
                           "by_rule": sorted(by_rule.values(), key=lambda r: -r["n"]), "per_day": [per_day[k] for k in sorted(per_day)]}
    group = str_field(payload, "group", required=False, choices=("rule", "department", "subject"))
    if group:
        groups: dict[str, dict[str, Any]] = {}
        for d in narrowed:
            key, label = {"rule": (d["rule"]["code"], d["rule"]["name"]), "department": (str(d["department_id"]), d["department_name"] or "No department"),
                          "subject": (f"{d['kind']}:{d['who']}", d["who"])}[group]
            g = groups.setdefault(key, {"key": key, "label": label, "n": 0, "open": 0})
            g["n"] += 1
            g["open"] += int(d["outcome"] == "open")
        out["groups"] = sorted(groups.values(), key=lambda g: (-g["open"], -g["n"]))
    return out


async def _evidence(ctx: Context, d: dict[str, Any]) -> list[str]:
    """What the record shows around the deviation -- facts only; the system never says why."""
    db = ctx.engine.db
    host = d["hostname"]
    out: list[str] = []
    if d["pc_id"] is not None and host:
        names = await db.accounts.display_names_for(ctx.identity.account_id, [s["occupant_account_id"] for s in await db.sessions.for_pc(d["pc_id"], d["at"] - timedelta(days=1))])
        around = [s for s in await db.sessions.for_pc(d["pc_id"], d["at"] - timedelta(hours=6))
                  if s["entered_at"] <= d["at"] + timedelta(hours=3) and (s["ended_at"] or datetime.now(timezone.utc)) >= d["at"] - timedelta(minutes=30)]
        owners = [s for s in around if s["occupied_via"] == "native" and s["entered_at"] <= d["at"] <= (s["ended_at"] or datetime.now(timezone.utc))]
        if owners:
            out.append(f"{names.get(owners[0]['occupant_account_id'], 'Its person')} was signed in to {host} at the time.")
        elif d["kind"] != "dept":
            out.append(f"Nobody was signed in to {host} at the time.")
        visits = sorted((s for s in around if s["occupied_via"] != "native"), key=lambda s: s["entered_at"])
        for s in visits[:3]:
            delta = s["entered_at"] - d["at"]
            mins = abs(round(delta.total_seconds() / 60))
            when = (f"{mins} minutes {'after' if delta.total_seconds() >= 0 else 'before'}" if mins < 120 else
                    f"{round(mins / 60)} hours {'after' if delta.total_seconds() >= 0 else 'before'}")
            out.append(f"{names.get(s['occupant_account_id'], 'An Admin')} entered {host} {when} it.")
        open_then = await db.issues.open_at(d["pc_id"], d["at"])
        out.append(f"No issue was open on {host} at the time." if not open_then else
                   f"{len(open_then)} issue{'s were' if len(open_then) != 1 else ' was'} open on {host} at the time.")
    if d["kind"] == "admin" and d["subject_account_id"] is not None:
        week = await db.audit.feed(since=d["at"] - timedelta(days=7), until=d["at"] + timedelta(minutes=1), kinds=["session"], pc_id=None,
                                   department_id=None, actor_account_id=d["subject_account_id"], before_id=None, limit=200)
        entries = sum(1 for e in week if e["action_type"] == "session.traversed")
        if entries:
            out.append(f"They entered machines {entries} time{'s' if entries != 1 else ''} in the week before.")
    return out


@handler("deviations.get")
async def deviations_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"deviation_id"} -> {"deviation", "context": [{at, who, what, kind}] (what the audit trail shows around it), "evidence": [...]}."""
    require_role(ctx, "super_user")
    db = ctx.engine.db
    d = await db.rules.deviation(int_field(payload, "deviation_id"))
    if d is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such deviation")
    around: list[dict[str, Any]] = []
    if d["pc_id"] is not None or d["subject_account_id"] is not None:
        found = await db.audit.feed(since=d["at"] - timedelta(hours=2), until=d["at"] + timedelta(hours=4), kinds=None, pc_id=d["pc_id"],
                                    department_id=None, actor_account_id=None if d["pc_id"] is not None else d["subject_account_id"],
                                    before_id=None, limit=12)
        around = [{"at": e["at"], "who": e["actor"], "what": e["what"], "kind": e["kind"]}
                  for e in await describe_many(db, found, ctx.identity.account_id) if not e["action_type"].startswith(("deviation.", "issue."))]
    around.append({"at": _iso(d["at"]), "who": "System", "what": f"Recorded: {d['rule_snapshot'].get('name', d['rule_name'])}", "kind": "deviation"})
    return {"deviation": (await _view(ctx, [d]))[0], "context": sorted(around, key=lambda e: e["at"]), "evidence": await _evidence(ctx, d)}


@handler("deviations.outcome")
async def deviations_outcome(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"deviation_id", "outcome": explained|accepted|escalated|dismissed|open, "note"?}. *Explained* and *accepted* need a note in the person's
    own words: that, and only that, is an explanation. The record, the rule as it was and the outcome stay."""
    ident = require_role(ctx, "super_user")
    d = await ctx.engine.db.rules.deviation(int_field(payload, "deviation_id"))
    if d is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such deviation")
    outcome = str_field(payload, "outcome", choices=OUTCOMES)
    note = " ".join(str(payload.get("note") or "").split())[:500] or None
    if outcome in NEEDS_NOTE and not note:
        raise ProtocolError(ErrorCode.INVALID, f"{outcome} needs a note: say why, in your own words")
    await ctx.engine.db.rules.set_outcome(d["id"], outcome, note if outcome != "open" else None, ident.account_id)
    await ctx.engine.audit.record(ctx, "deviation.outcome", target_type="deviations", target_id=d["id"], pc_id=d["pc_id"],
                                  detail={"code": d["code"], "outcome": outcome, "note": note, "department_id": d["department_id"]})
    fresh = await ctx.engine.db.rules.deviation(d["id"])
    assert fresh is not None
    return {"deviation": (await _view(ctx, [fresh]))[0]}
