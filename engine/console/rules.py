"""Rules: the standard the organisation is measured against (the Rules page; read-only in an Admin's console).

A rule is a **pattern**: what *should* happen. A deviation (engine/console/deviations.py) is a departure from one. Three shapes:

    never    the first time it happens it is a deviation           {trigger}
    follow   after one thing happens another must follow in time   {trigger, expect, within}  (minutes)
    limit    a count that must not go over a line in a period      {reading, limit: {n, per: hour|day|week}}

The stored shape is the `spec` JSON the concept's rule builder fills in:

    {"trigger"?, "expect"?, "within"?, "reading"?, "limit"?: {"n", "per"}, "who": everyone|workers|admins|machines|depts,
     "depts": "all" | [department ids], "severity"?: critical|high|medium|low, "resp": {"report": bool, "admin": bool, "action": bool, "action_id"?}}

`resp` is what the system does when the rule is broken, chosen by the Super User and nothing more: record it (always), report it to the
Super User, notify the department's Admin, run an Action. Nothing runs silently.

    rules.list     {}                      the built-in (locked) rules and the organisation's, each with this week's deviations
    rules.get      {rule_id}
    rules.library  {}                      the patterns to start from
    rules.create   {name, shape, ...spec}  Super User
    rules.update   {rule_id, name?, ...spec}   Super User; not a built-in
    rules.switch   {rule_id, on}           Super User; not a built-in. Off stops new deviations; old ones stay.
    rules.try      {rule_id, within? | limit?}  what a changed limit would have done to the last month's deviations

An Admin reads the same list ("set by the Super User"); they cannot change or switch off an organisation-wide rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from protocol import ErrorCode, ProtocolError

SHAPES = ("never", "follow", "limit")
# what can happen; and for each trigger of a *follow* rule, what must follow
TRIGGERS = {
    "file": "A copy of a restricted file appears where it is not allowed",
    "second": "A second session starts on a machine already in use",
    "cert": "A machine presents a name that does not match what it was registered with",
    "help": "A worker pings for help",
    "report": "A report is written for a department",
    "version": "A new version is approved",
    "outhours": "Someone enters a machine outside working hours",
    "task": "A department task is given",
    "seat": "A department loses its last Admin",
}
EXPECTS = {
    "answer": "An Admin answers the ping", "addressed": "Someone marks the report addressed", "updated": "The machine runs that version",
    "seen": "An Admin marks it seen", "appoint": "Another Admin is appointed",
}
NEVER_TRIGGERS = ("file", "second", "cert", "outhours")
FOLLOW = {"help": ("answer",), "report": ("addressed",), "version": ("updated",), "task": ("seen",), "seat": ("appoint",)}
READINGS = {
    "outhours": "Admin entries outside working hours",
    "crossdept": "Admin entries into other departments' machines",
    "samemachine": "Entries into one machine by the same Admin",
    "failedauth": "Failed sign-ins on one machine",
}
PERIODS = {"hour": timedelta(hours=1), "day": timedelta(days=1), "week": timedelta(days=7)}
WHOS = {"everyone": "Everyone: workers, Admins and machines", "workers": "Workers", "admins": "Admins", "machines": "Machines", "depts": "Departments"}
WITHIN_MAX = 60 * 24 * 90

# a rule's "who" and the kinds of subject a deviation can have
WHO_KINDS = {"everyone": {"worker", "admin", "pc", "dept"}, "workers": {"worker"}, "admins": {"admin"}, "machines": {"pc"}, "depts": {"dept"}}

# The patterns to start from: pick one, adjust the limits, choose the scope, switch it on.
LIBRARY = [
    {"key": "restricted-leaves", "name": "Restricted file leaves its folder", "shape": "never",
     "summary": "A copy of a marked file appears where its mark does not allow it.",
     "spec": {"trigger": "file", "who": "everyone", "depts": "all", "resp": {"report": True, "admin": True}}},
    {"key": "unanswered-help", "name": "Unanswered help request", "shape": "follow",
     "summary": "A worker pinged for help and nobody answered in time.",
     "spec": {"trigger": "help", "expect": "answer", "within": 60, "who": "admins", "depts": "all", "resp": {"report": True, "admin": True}}},
    {"key": "past-update-limit", "name": "Machine past the update limit", "shape": "follow",
     "summary": "A machine is still not on the approved version after the time allowed.",
     "spec": {"trigger": "version", "expect": "updated", "within": 2880, "who": "machines", "depts": "all", "resp": {"report": True, "admin": True}}},
    {"key": "admin-outside", "name": "Admin outside their department", "shape": "limit",
     "summary": "An Admin entering other departments' machines more than the line allows.",
     "spec": {"reading": "crossdept", "limit": {"n": 0, "per": "week"}, "who": "admins", "depts": "all", "resp": {"report": True, "admin": False}}},
    {"key": "out-of-hours", "name": "Out-of-hours session", "shape": "limit",
     "summary": "An Admin entering machines outside working hours.",
     "spec": {"reading": "outhours", "limit": {"n": 0, "per": "week"}, "who": "admins", "depts": "all", "resp": {"report": True, "admin": False}}},
]


def _dur(minutes: int) -> str:
    if minutes % 1440 == 0:
        n = minutes // 1440
        return f"{n} day{'s' if n != 1 else ''}"
    if minutes % 60 == 0:
        n = minutes // 60
        return f"{n} hour{'s' if n != 1 else ''}"
    return f"{minutes} minutes"


def sentence(shape: str, spec: dict[str, Any]) -> str:
    """The rule in one plain sentence."""
    if shape == "never":
        return f"{TRIGGERS[spec['trigger']]}: always a deviation."
    if shape == "follow":
        exp = EXPECTS[spec["expect"]]
        return f"{TRIGGERS[spec['trigger']]}, then {exp[0].lower()}{exp[1:]} within {_dur(spec['within'])}."
    lim = spec["limit"]
    return f"{READINGS[spec['reading']]}: {'none' if lim['n'] == 0 else 'no more than ' + str(lim['n'])} per {lim['per']}."


def scope_text(spec: dict[str, Any], dept_names: dict[int, str]) -> str:
    if spec.get("who") == "depts":
        return "Every department"
    depts = spec.get("depts")
    where = "every department" if depts in (None, "all") else ", ".join(dept_names.get(d, str(d)) for d in depts)
    return f"{WHOS[spec['who']].split(':')[0]}, {where}"


def validate(shape: str, raw: dict[str, Any], known_departments: set[int]) -> dict[str, Any]:
    """The spec for a rule, checked and cleaned. Raises INVALID with what is wrong."""
    if shape not in SHAPES:
        raise ProtocolError(ErrorCode.INVALID, f"shape must be one of {SHAPES}")
    spec: dict[str, Any] = {}
    if shape == "never":
        if raw.get("trigger") not in NEVER_TRIGGERS:
            raise ProtocolError(ErrorCode.INVALID, f"a 'never' rule's trigger must be one of {NEVER_TRIGGERS}")
        spec["trigger"] = raw["trigger"]
    elif shape == "follow":
        trigger, expect = raw.get("trigger"), raw.get("expect")
        if trigger not in FOLLOW or expect not in FOLLOW[trigger]:
            raise ProtocolError(ErrorCode.INVALID, "a 'follow' rule needs a trigger and what must follow it: "
                                + "; ".join(f"{t} -> {', '.join(e)}" for t, e in FOLLOW.items()))
        within = raw.get("within")
        if not isinstance(within, int) or isinstance(within, bool) or not 1 <= within <= WITHIN_MAX:
            raise ProtocolError(ErrorCode.INVALID, f"within is a whole number of minutes, 1 to {WITHIN_MAX}")
        spec.update({"trigger": trigger, "expect": expect, "within": within})
    else:
        if raw.get("reading") not in READINGS:
            raise ProtocolError(ErrorCode.INVALID, f"reading must be one of {sorted(READINGS)}")
        lim = raw.get("limit")
        if not isinstance(lim, dict) or not isinstance(lim.get("n"), int) or lim["n"] < 0 or lim.get("per") not in PERIODS:
            raise ProtocolError(ErrorCode.INVALID, f"limit is {{n: 0 or more, per: {'|'.join(PERIODS)}}}")
        spec.update({"reading": raw["reading"], "limit": {"n": lim["n"], "per": lim["per"]}})
    who = raw.get("who") or "everyone"
    if who not in WHOS:
        raise ProtocolError(ErrorCode.INVALID, f"who must be one of {sorted(WHOS)}")
    depts = raw.get("depts", "all")
    if depts != "all":
        if not isinstance(depts, list) or not depts or not all(isinstance(d, int) for d in depts):
            raise ProtocolError(ErrorCode.INVALID, "depts is 'all' or a list of department ids")
        if unknown := set(depts) - known_departments:
            raise ProtocolError(ErrorCode.NOT_FOUND, f"unknown departments {sorted(unknown)}")
    severity = raw.get("severity", "medium")
    if severity not in ("critical", "high", "medium", "low"):
        raise ProtocolError(ErrorCode.INVALID, "severity must be critical, high, medium or low")
    resp = raw.get("resp") or {}
    out_resp = {"report": bool(resp.get("report", True)), "admin": bool(resp.get("admin", False)), "action": bool(resp.get("action", False))}
    if out_resp["action"]:
        if not isinstance(resp.get("action_id"), int):
            raise ProtocolError(ErrorCode.INVALID, "resp.action needs action_id: the Action to run")
        out_resp["action_id"] = resp["action_id"]
    spec.update({"who": who, "depts": depts, "severity": severity, "resp": out_resp})
    return spec


def in_scope(spec: dict[str, Any], kind: str, department_id: int | None) -> bool:
    """Does this rule apply to a subject of this kind in this department?"""
    if kind not in WHO_KINDS[spec.get("who", "everyone")]:
        return False
    depts = spec.get("depts", "all")
    return depts == "all" or (department_id is not None and department_id in depts)


async def view(ctx: Context, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = ctx.engine.db
    since = datetime.now(timezone.utc) - timedelta(days=7)
    counts = {r["rule_id"]: r for r in await db.rules.deviation_counts(since)}
    depts = {d["id"]: d["name"] for d in await db.accounts.list_departments()}
    names = await db.accounts.display_names_for(
        ctx.identity.account_id, sorted({r["created_by_account_id"] for r in rules if r["created_by_account_id"]}))
    out = []
    for r in rules:
        c = counts.get(r["id"], {"n": 0, "open": 0})
        out.append({"id": r["id"], "code": r["code"], "name": r["name"], "shape": r["shape"], "locked": r["builtin"], "on": True if r["builtin"] else r["enabled"],
                    "spec": r["spec"], "sentence": sentence(r["shape"], r["spec"]), "scope": scope_text(r["spec"], depts),
                    "set_by": "Falcon" if r["builtin"] else ("You" if r["created_by_account_id"] == ctx.identity.account_id
                                                            else names.get(r["created_by_account_id"], "the Super User")),
                    "since": r["created_at"].isoformat(), "deviations_this_week": c["n"], "open_this_week": c["open"]})
    return out


@handler("rules.list")
async def rules_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """-> {"rules": [{id, code, name, shape, locked, on, spec, sentence, scope, set_by, since, deviations_this_week, open_this_week}],
    "summary": {rules, on, broken_this_week, kept}}. Built-in rules are listed locked. `broken_this_week` counts rules with a deviation,
    `kept` those without."""
    require_role(ctx, "super_user", "admin")
    found = await view(ctx, await ctx.engine.db.rules.rules())
    live = [r for r in found if r["on"]]
    broken = sum(1 for r in live if r["deviations_this_week"])
    return {"rules": found, "summary": {"rules": len(found), "on": len(live), "broken_this_week": broken, "kept": len(live) - broken}}


@handler("rules.get")
async def rules_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    rule = await ctx.engine.db.rules.rule(int_field(payload, "rule_id"))
    if rule is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such rule")
    return {"rule": (await view(ctx, [rule]))[0], "triggers": TRIGGERS, "expects": EXPECTS, "readings": READINGS}


@handler("rules.library")
async def rules_library(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The patterns to start from, with the words the rule builder uses for triggers, what follows, readings and who."""
    require_role(ctx, "super_user")
    return {"patterns": [{**p, "sentence": sentence(p["shape"], p["spec"])} for p in LIBRARY], "triggers": TRIGGERS, "expects": EXPECTS,
            "follow": {t: list(e) for t, e in FOLLOW.items()}, "never": list(NEVER_TRIGGERS), "readings": READINGS, "who": WHOS,
            "periods": list(PERIODS)}


async def _known_departments(ctx: Context) -> set[int]:
    return {d["id"] for d in await ctx.engine.db.accounts.list_departments()}


async def _check_action(ctx: Context, spec: dict[str, Any]) -> None:
    action_id = spec["resp"].get("action_id")
    if action_id is not None:
        action = await ctx.engine.db.control.action(action_id)
        if action is None or action.get("archived_at"):
            raise ProtocolError(ErrorCode.NOT_FOUND, f"no such action {action_id}")


@handler("rules.create")
async def rules_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"name", "shape", ...spec} -> {"rule"}. Super User only; applies to the whole organisation."""
    ident = require_role(ctx, "super_user")
    name = " ".join(str_field(payload, "name").split())[:80]
    if not name:
        raise ProtocolError(ErrorCode.INVALID, "a rule needs a name")
    shape = str_field(payload, "shape")
    spec = validate(shape, payload, await _known_departments(ctx))
    await _check_action(ctx, spec)
    rule_id = await ctx.engine.db.rules.create_rule(name, shape, spec, ident.account_id)
    rule = await ctx.engine.db.rules.rule(rule_id)
    assert rule is not None
    await ctx.engine.audit.record(ctx, "rule.created", target_type="rules", target_id=rule_id, detail={"code": rule["code"], "name": name, "shape": shape})
    return {"rule": (await view(ctx, [rule]))[0]}


async def _own_rule(ctx: Context, rule_id: int) -> dict[str, Any]:
    require_role(ctx, "super_user")
    rule = await ctx.engine.db.rules.rule(rule_id)
    if rule is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such rule")
    if rule["builtin"]:
        raise ProtocolError(ErrorCode.FORBIDDEN, f"{rule['code']} is built into Falcon: it can be seen, not changed or switched off")
    return rule


@handler("rules.update")
async def rules_update(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"rule_id", "name"?, and any of the spec fields to change}. The shape cannot change; deviations already recorded keep the rule as it was."""
    rule = await _own_rule(ctx, int_field(payload, "rule_id"))
    name = " ".join(str(payload["name"]).split())[:80] if payload.get("name") else None
    merged = {**rule["spec"], **{k: v for k, v in payload.items() if k in ("trigger", "expect", "within", "reading", "limit", "who", "depts", "severity", "resp")}}
    spec = validate(rule["shape"], merged, await _known_departments(ctx))
    await _check_action(ctx, spec)
    await ctx.engine.db.rules.update_rule(rule["id"], name=name, spec=spec)
    fresh = await ctx.engine.db.rules.rule(rule["id"])
    assert fresh is not None
    await ctx.engine.audit.record(ctx, "rule.updated", target_type="rules", target_id=rule["id"], detail={"code": rule["code"], "was": rule["spec"], "now": spec})
    return {"rule": (await view(ctx, [fresh]))[0]}


@handler("rules.switch")
async def rules_switch(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"rule_id", "on": bool}: off stops new deviations and never deletes old ones."""
    rule = await _own_rule(ctx, int_field(payload, "rule_id"))
    on = payload.get("on")
    if not isinstance(on, bool):
        raise ProtocolError(ErrorCode.INVALID, "on must be true or false")
    await ctx.engine.db.rules.update_rule(rule["id"], enabled=on)
    fresh = await ctx.engine.db.rules.rule(rule["id"])
    assert fresh is not None
    await ctx.engine.audit.record(ctx, "rule.switched", target_type="rules", target_id=rule["id"], detail={"code": rule["code"], "on": on})
    return {"rule": (await view(ctx, [fresh]))[0]}


@handler("rules.try")
async def rules_try(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"rule_id", "within"? (minutes) | "limit"? ({n})} -> {"deviations", "would_clear", "would_remain"} over the last 30 days: what changing the line
    would have done to the deviations already recorded, before saving it. A deviation's value is how late (minutes) or how many."""
    require_role(ctx, "super_user")
    rule = await ctx.engine.db.rules.rule(int_field(payload, "rule_id"))
    if rule is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such rule")
    values = await ctx.engine.db.rules.deviation_values(rule["id"], datetime.now(timezone.utc) - timedelta(days=30))
    total = len(await ctx.engine.db.rules.deviations(since=datetime.now(timezone.utc) - timedelta(days=30), rule_id=rule["id"]))
    if rule["shape"] == "follow" and isinstance(payload.get("within"), int):
        clear = sum(1 for v in values if v <= payload["within"])
    elif rule["shape"] == "limit" and isinstance(payload.get("limit"), dict) and isinstance(payload["limit"].get("n"), int):
        clear = sum(1 for v in values if v <= payload["limit"]["n"])
    else:
        raise ProtocolError(ErrorCode.INVALID, "give within (a follow rule) or limit {n} (a limit rule) to try")
    return {"deviations": total, "would_clear": clear, "would_remain": total - clear, "counted": len(values)}
