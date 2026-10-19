"""The Overviews and the Reports page's figures (Overview for both levels, Reports > Handling, the Super User's decisions).

    reports.board     {days?, department_id?}   reports with where they came from, who may take them, who addressed them and how fast;
                                                the strip (waiting, with the department, addressed, typical time) and per-department handling
    overview.queue    {}                        Super User: what only they can decide -- reports nobody below them can take, a department with
                                                no Admin, a department's work called done -- each with the options and their effects
    overview.decide   {decision, option, ...}   Super User: carry out one option of one decision
    overview.su       {}                        Super User: the four figures, deviations by day and severity, Worth a look
    overview.admin    {}                        Admin: Waiting on you, machines online, open issues, sessions held
    overview.departments {}                     one row per department (an Admin gets their own): Admins, machines, issues, version, time to address

A report is the Super User's to take when nobody below them can: it is about an Admin (never routed), its department has no Admin, or its
category is not routed to its department. Everything else is the department's, and the Super User only watches how fast it goes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from engine.dispatch import Context, dispatch, handler
from engine.hierarchy.reports import CATEGORIES, FIXED_CATEGORIES
from engine.permissions import int_field, require_role, str_field
from protocol import ErrorCode, ProtocolError

LABELS = {
    "resource_violation": "Restricted file", "flow_failure": "Flow failed",
    "update_status": "Update stuck", "deviation": "Deviation", "about_admin": "About an Admin",
}
SEVERITY = {
    "resource_violation": "high", "update_status": "high", "flow_failure": "medium", "deviation": "medium", "about_admin": "medium",
}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
HELD_FOR = timedelta(hours=24)
# Other parts of the Engine add their own decisions (the version gate): a source returns cards, a decider carries one out.
CARD_SOURCES: list[Callable[[Context, set[str]], Awaitable[list[dict[str, Any]]]]] = []
DECIDERS: dict[str, Callable[[Context, dict[str, Any], str, dict[str, Any]], Awaitable[tuple[str, dict[str, Any] | None]]]] = {}
ONE_DEPARTMENT = "An Admin belongs to one department. Giving another department an Admin means promoting one of its Workers or provisioning a new one."


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _minutes(a: datetime, b: datetime) -> int:
    return max(0, round((b - a).total_seconds() / 60))


def _median(values: list[float]) -> int | None:
    return round(median(values)) if values else None


def owner_of(report: dict[str, Any], admin_depts: set[int], routed: set[tuple[str, int]]) -> str:
    """Whose a report is: the department's ('dept'), or the Super User's because it is about an Admin ('fixed'), its department has no
    Admin ('noadmin'), or its category is not routed there ('unrouted')."""
    if report["category"] in FIXED_CATEGORIES:
        return "fixed"
    dept = report["department_id"]
    if dept is None:
        return "unrouted"
    if dept not in admin_depts:
        return "noadmin"
    if (report["category"], dept) not in routed:
        return "unrouted"
    return "dept"


async def _context(ctx: Context) -> tuple[set[int], set[tuple[str, int]], dict[int, list[dict[str, Any]]]]:
    db = ctx.engine.db
    admins = await db.accounts.active_admins()
    by_dept: dict[int, list[dict[str, Any]]] = {}
    for a in admins:
        by_dept.setdefault(a["department_id"], []).append(a)
    return set(by_dept), await db.reports.routing_pairs(), by_dept


def _view(r: dict[str, Any], owner: str, names: dict[int, str]) -> dict[str, Any]:
    done = r["addressed_at"] is not None
    return {"id": r["id"], "category": r["category"], "label": LABELS.get(r["category"], r["category"]), "severity": SEVERITY.get(r["category"], "low"),
            "summary": r["summary"], "at": _iso(r["generated_at"]), "pc_id": r["pc_id"], "host": r["hostname"],
            "department_id": r["department_id"], "department_name": r["department_name"],
            "about": names.get(r["about_account_id"]) if r["about_account_id"] else None, "owner": owner, "seen": r["seen_at"] is not None,
            "addressed": {"by": names.get(r["addressed_by_account_id"]), "at": _iso(r["addressed_at"]),
                          "took_minutes": _minutes(r["generated_at"], r["addressed_at"])} if done else None}


def _handling(department: dict[str, Any], reports: list[dict[str, Any]], has_admin: bool) -> dict[str, Any]:
    mine = [r for r in reports if r["owner"] == "dept"]
    took = [r["addressed"]["took_minutes"] for r in mine if r["addressed"]]
    return {"department_id": department["id"], "name": department["name"], "has_admin": has_admin, "all": len(reports),
            "done": len(took), "waiting": len(mine) - len(took),
            "to_you": sum(1 for r in reports if r["owner"] != "dept" and not r["addressed"]), "median_minutes": _median(took)}


@handler("reports.board")
async def board(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"days"?: 7, "department_id"?} -> {"reports", "strip", "handling", "categories"}. The Super User sees every report, each marked with
    whose it is; an Admin the ones routed to their department (all theirs)."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    days = max(1, min(int_field(payload, "days", required=False) or 7, 90))
    since = _now() - timedelta(days=days)
    admin_depts, routed, _ = await _context(ctx)
    if ident.role == "admin":
        found = await db.reports.board(since=since, routed_to=ident.department_id, reader_id=ident.account_id)
    else:
        found = await db.reports.board(since=since, department_id=int_field(payload, "department_id", required=False), reader_id=ident.account_id)
    people = {r["about_account_id"] for r in found if r["about_account_id"]} | {r["addressed_by_account_id"] for r in found if r["addressed_by_account_id"]}
    names = await db.accounts.display_names_for(ident.account_id, sorted(people)) if people else {}
    views = [_view(r, "dept" if ident.role == "admin" else owner_of(r, admin_depts, routed), names) for r in found]
    if ident.role == "admin":
        mine = [v for v in views if v["owner"] == "dept"]
        took = [v["addressed"]["took_minutes"] for v in mine if v["addressed"]]
        strip = {"waiting": len(mine) - len(took), "with_department": None, "addressed": len(took), "typical_minutes": _median(took)}
        handling = []
    else:
        you = [v for v in views if v["owner"] != "dept" and not v["addressed"]]
        dept_side = [v for v in views if v["owner"] == "dept"]
        took = [v["addressed"]["took_minutes"] for v in dept_side if v["addressed"]]
        strip = {"waiting": len(you), "with_department": sum(1 for v in dept_side if not v["addressed"]), "addressed": sum(1 for v in views if v["addressed"]),
                 "typical_minutes": _median(took)}
        handling = [_handling(d, [v for v in views if v["department_id"] == d["id"]], d["id"] in admin_depts)
                    for d in await db.accounts.list_departments()]
    return {"reports": views, "strip": strip, "handling": handling, "days": days,
            "categories": [{"key": c, "label": LABELS.get(c, c), "severity": SEVERITY.get(c, "low"), "fixed": c in FIXED_CATEGORIES} for c in CATEGORIES]}


# --- the Super User's decisions -------------------------------------------------------------------------------------------------


def _option(key: str, title: str, desc: str, verb: str, done: str, need: str | None = None, pick: list[dict[str, Any]] | None = None,
            disabled: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"key": key, "title": title, "desc": desc, "verb": verb, "done": done, "need": need, "pick": pick, "disabled": disabled, **extra}


def _list_names(names: list[str], n: int = 2) -> str:
    return " and ".join(names) if len(names) <= n else f"{', '.join(names[:n])} and {len(names) - n} more"


async def _seat_card(ctx: Context, department: dict[str, Any], held: set[str]) -> dict[str, Any] | None:
    db = ctx.engine.db
    key = f"seat:{department['id']}"
    if key in held:
        return None
    ident = ctx.identity
    fleet = await db.accounts.fleet(department_id=department["id"])
    people = [m for m in fleet if m["account_id"] and m["pc_type"] == "client_pc"]
    names = await db.accounts.display_names_for(ident.account_id, [m["account_id"] for m in people]) if people else {}
    options = [_option(f"promote:{m['account_id']}", f"{names.get(m['account_id']) or m['hostname']}, promoted from {m['hostname']}",
                       "Works in the department every day. Promoting gives them an Admin workstation and a new key, shown once.",
                       "Promote", f"{names.get(m['account_id']) or m['hostname']} promoted to {department['name']} Admin") for m in people]
    others = [a for a in await db.accounts.active_admins() if a["department_id"] != department["id"]]
    if others:
        options.append(_option("elsewhere", "An Admin from another department", ONE_DEPARTMENT, "Not possible", "", disabled=ONE_DEPARTMENT))
    options.append(_option("provision", "A new Admin", "A new Admin account and its workstation; the key is shown once.", "Provision", f"New Admin for {department['name']}", need="hostname"))
    return {"id": key, "kind": "empty-seat", "severity": "high", "department_id": department["id"], "department": department["name"],
            "title": f"{department['name']} has no Admin", "short": f"{department['name']} has no Admin", "at": None,
            "why": f"{len(fleet)} machine{'s' if len(fleet) != 1 else ''} and every report from them have nobody below you. Only you can assign an Admin.",
            "machines": [m["hostname"] for m in fleet], "options": options}


async def _task_cards(ctx: Context, held: set[str]) -> list[dict[str, Any]]:
    from engine.task.dept_tasks import standing

    db = ctx.engine.db
    tasks = await db.department_tasks.list()
    out = []
    for t in tasks:
        key = f"dtask:{t['id']}"
        admins = await db.department_tasks.admins([t["id"]])
        if standing([a["state"] for a in admins]) != "done" or key in held:
            continue
        done_by = next((a for a in admins if a["state"] == "done"), None)
        names = await db.accounts.display_names_for(ctx.identity.account_id, [done_by["account_id"]]) if done_by else {}
        late = t["deadline_at"] < _now()
        out.append({"id": key, "kind": "task-done", "severity": "medium" if late else "low", "department_id": t["department_id"],
                    "department": t["department_name"], "task_id": t["id"], "title": f"{t['department_name']} says “{t['title']}” is done",
                    "short": f"Done: {t['title']}", "at": _iso(done_by["state_at"]) if done_by else None,
                    "why": f"{names.get(done_by['account_id']) or 'An Admin'} marked it done. Only you can call it complete." if done_by else "Only you can call it complete.",
                    "options": [_option("complete", "Complete", "It leaves the list, recorded as complete with your name and the time.", "Complete", "Marked complete"),
                                _option("notyet", "Not done yet", f"It goes back to {t['department_name']} as ongoing, with your note. Every Admin there sees it.",
                                        "Send back", "Sent back", need="message")]})
    return out


def _report_card(category: str, rs: list[dict[str, Any]], depts: dict[int, dict[str, Any]]) -> dict[str, Any]:
    fixed = category in FIXED_CATEGORIES
    label = LABELS.get(category, category)
    no_admin = sorted({r["department_id"] for r in rs if r["owner"] == "noadmin"})
    unrouted = sorted({r["department_id"] for r in rs if r["owner"] == "unrouted" and r["department_id"] is not None})
    dn = lambda ids: [depts[i]["name"] for i in ids if i in depts]
    if fixed:
        why = "Reports about an Admin are never routed: the department would be judging its own Admin. Only you see them."
    else:
        why = " ".join(x for x in (
            f"{_list_names(dn(no_admin))} {'has' if len(no_admin) == 1 else 'have'} no Admin, so {label.lower()} reports from there come to you." if no_admin else "",
            f"{label} is not routed to {_list_names(dn(unrouted))}. Route it and their Admins take these." if unrouted else "") if x)
    options = [_option("mark", "Mark the ticked ones addressed", "They stay in the record with your name and the time.", "Mark addressed", "Marked addressed")]
    if unrouted and not fixed:
        options.append(_option("route", f"Route {label.lower()} to {_list_names(dn(unrouted))}", "Their Admins take these and every later one. You still receive every report.",
                               "Route it", "Routed", department_ids=unrouted))
    if no_admin:
        options.append(_option("seat", f"Give {dn(no_admin)[0]} an Admin", "Then reports from there can be routed to them. Opens that decision.", "Open it", "",
                               opens=f"seat:{no_admin[0]}"))
    if category == "update_status":
        hosts = sorted({r["host"] for r in rs if r["host"]})
        options.append(_option("exclude", f"Leave {hosts[0] if len(hosts) == 1 else 'these machines'} out of the next version's gate",
                               "The next version can then be approved without them. They stay where they are until they update.", "Leave out", "Left out of the gate", need="reason"))
    if fixed:
        who = sorted({r["about"] for r in rs if r["about"]})
        them = who[0] if len(who) == 1 else "them"
        options += [_option("ask", f"Ask {them} to explain", "A message from you, recorded with these reports.", "Send", f"Asked {them}", need="message"),
                    _option("limit", f"Limit {them} to working hours", "They can enter machines only within working hours until you lift it.", "Limit", f"Limited {them} to working hours"),
                    _option("fine", "It was expected", "Note why. The reports are marked addressed with your note.", "Note it", "Noted as expected", need="reason")]
    options.append(_option("later", "Leave them for now", "They come back tomorrow if still waiting.", "Leave them", "Left for now"))
    first = rs[0]
    hosts = sorted({r["host"] for r in rs if r["host"]})
    return {"id": f"reports:{category}", "kind": "reports", "severity": SEVERITY.get(category, "low"), "category": category, "label": label,
            "department_ids": sorted({r["department_id"] for r in rs if r["department_id"] is not None}), "pc_ids": sorted({r["pc_id"] for r in rs if r["pc_id"]}),
            "title": f"{len(rs)} {label.lower()} report{'s' if len(rs) != 1 else ''} only you can address", "short": f"{label} · {len(rs)}",
            "at": first["at"], "why": why, "host": hosts[0] if len(hosts) == 1 else None, "about": first["about"], "report_ids": [r["id"] for r in rs],
            "reports": rs, "options": options}


async def _queue(ctx: Context) -> list[dict[str, Any]]:
    db = ctx.engine.db
    held = await db.decisions.held_keys()
    admin_depts, routed, _ = await _context(ctx)
    depts = {d["id"]: d for d in await db.accounts.list_departments()}
    found = await db.reports.board(since=_now() - timedelta(days=60), reader_id=ctx.identity.account_id)
    people = {r["about_account_id"] for r in found if r["about_account_id"]}
    names = await db.accounts.display_names_for(ctx.identity.account_id, sorted(people)) if people else {}
    views = [_view(r, owner_of(r, admin_depts, routed), names) for r in found]
    cards = []
    for category in CATEGORIES:
        rs = [v for v in views if v["category"] == category and v["owner"] != "dept" and not v["addressed"]]
        if rs and f"reports:{category}" not in held:
            cards.append(_report_card(category, rs, depts))
    for d in depts.values():
        if d["id"] not in admin_depts:
            card = await _seat_card(ctx, d, held)
            if card:
                cards.append(card)
    cards += await _task_cards(ctx, held)
    for source in CARD_SOURCES:
        cards += await source(ctx, held)
    return sorted(cards, key=lambda c: SEV_ORDER.get(c["severity"], 3))


@handler("overview.queue")
async def queue(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User: the decisions waiting on them, worst first, each with its options. -> {"decisions", "urgent"}."""
    require_role(ctx, "super_user")
    cards = await _queue(ctx)
    return {"decisions": cards, "urgent": sum(1 for c in cards if c["severity"] in ("high", "critical"))}


async def _hold(ctx: Context, key: str, option: str, note: str | None, hours: int | None = 24) -> None:
    until = _now() + timedelta(hours=hours) if hours else None
    await ctx.engine.db.decisions.record(key, option, note, ctx.identity.account_id, until)


def _text(payload: dict[str, Any], key: str, what: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ProtocolError(ErrorCode.INVALID, f"{what} is needed for this")
    return value[:1000]


async def _decide_reports(ctx: Context, card: dict[str, Any], option: str, payload: dict[str, Any]) -> str:
    db = ctx.engine.db
    ident = ctx.identity
    ids = payload.get("report_ids") or card["report_ids"]
    if not isinstance(ids, list) or not set(ids) <= set(card["report_ids"]):
        raise ProtocolError(ErrorCode.INVALID, "report_ids must be reports in this decision")
    chosen = next(o for o in card["options"] if o["key"] == option)
    if option in ("mark", "fine"):
        note = _text(payload, "reason", "a reason") if option == "fine" else None
        for rid in ids:
            await db.reports.mark_addressed(rid, ident.account_id)
            await ctx.engine.audit.record(ctx, "report.addressed", target_type="reports", target_id=rid, detail={"by": "super_user", "note": note})
    elif option == "route":
        for dept in chosen["department_ids"]:
            current = await db.reports.departments_for_category(card["category"])
            await dispatch(ctx, "reports.routing_set", {"category": card["category"], "department_ids": sorted({*current, dept})})
    elif option == "exclude":
        reason = _text(payload, "reason", "a reason")
        for pc_id in card["pc_ids"]:
            await db.updates.exclude_from_gate(pc_id, "next", reason, ident.account_id)
            await ctx.engine.audit.record(ctx, "update.left_out", target_type="pcs", target_id=pc_id, detail={"reason": reason})
    elif option == "ask":
        text = _text(payload, "message", "a message")
        for account_id in sorted({r["about_account_id"] for r in await db.reports.board(since=_now() - timedelta(days=60)) if r["id"] in ids and r["about_account_id"]}):
            await ctx.engine.audit.record(ctx, "admin.asked", target_type="accounts", target_id=account_id, detail={"message": text, "report_ids": ids})
            await ctx.engine.push_to_account(account_id, "admin.question", {"message": text, "report_ids": ids})
    elif option == "limit":
        for account_id in sorted({r["about_account_id"] for r in await db.reports.board(since=_now() - timedelta(days=60)) if r["id"] in ids and r["about_account_id"]}):
            await dispatch(ctx, "hierarchy.admin_limit", {"account_id": account_id, "on": True})
    elif option == "later":
        await _hold(ctx, card["id"], "later", None)
    else:
        raise ProtocolError(ErrorCode.INVALID, f"{option!r} is not an option of this decision")
    return chosen["done"]


async def _decide_seat(ctx: Context, card: dict[str, Any], option: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    chosen = next((o for o in card["options"] if o["key"] == option), None)
    if chosen is None:
        raise ProtocolError(ErrorCode.INVALID, f"{option!r} is not an option of this decision")
    if chosen["disabled"]:
        raise ProtocolError(ErrorCode.CONFLICT, chosen["disabled"])
    if option.startswith("promote:"):
        made = await dispatch(ctx, "hierarchy.admin_promote", {"account_id": int(option.split(":", 1)[1])})
        return chosen["done"], made
    made = await dispatch(ctx, "hierarchy.account_create", {"role": "admin", "department_id": card["department_id"], "hostname": _text(payload, "hostname", "a machine name")})
    return chosen["done"], made


async def _decide_task(ctx: Context, card: dict[str, Any], option: str, payload: dict[str, Any]) -> str:
    if option == "complete":
        await dispatch(ctx, "task.dept_complete", {"task_id": card["task_id"]})
    elif option == "notyet":
        await dispatch(ctx, "task.dept_reopen", {"task_id": card["task_id"], "note": _text(payload, "message", "a note")})
    else:
        raise ProtocolError(ErrorCode.INVALID, f"{option!r} is not an option of this decision")
    return next(o["done"] for o in card["options"] if o["key"] == option)


@handler("overview.decide")
async def decide(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User: {"decision": "<id from overview.queue>", "option": "<key>", "report_ids"?, "reason"?, "message"?, "hostname"?}. Carries the option out
    through the same handler the console would otherwise call, and says what was done. -> {"done", "result"?, "decisions": <what is left>}."""
    require_role(ctx, "super_user")
    key = str_field(payload, "decision")
    option = str_field(payload, "option")
    card = next((c for c in await _queue(ctx) if c["id"] == key), None)
    if card is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "that decision is no longer waiting")
    result: dict[str, Any] | None = None
    if card["kind"] == "reports":
        done = await _decide_reports(ctx, card, option, payload)
    elif card["kind"] == "empty-seat":
        done, result = await _decide_seat(ctx, card, option, payload)
    elif card["kind"] == "task-done":
        done = await _decide_task(ctx, card, option, payload)
    else:
        decider = DECIDERS.get(card["kind"])
        if decider is None:
            raise ProtocolError(ErrorCode.INVALID, f"nothing decides a {card['kind']} decision")
        done, result = await decider(ctx, card, option, payload)
    await ctx.engine.audit.record(ctx, "decision.made", detail={"decision": key, "option": option, "done": done})
    left = await _queue(ctx)
    return {"done": done, "result": result, "decisions": left, "urgent": sum(1 for c in left if c["severity"] in ("high", "critical"))}


# --- the Super User's Overview --------------------------------------------------------------------------------------------------


@handler("overview.su")
async def overview_su(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The four figures, deviations by day and severity (7 days), and Worth a look (this week's deviations, open ones first)."""
    require_role(ctx, "super_user")
    db = ctx.engine.db
    now = _now()
    cards = await _queue(ctx)
    fleet = (await dispatch(ctx, "machines.list", {}))
    machines = fleet["machines"]
    summary = fleet["summary"]
    week = await dispatch(ctx, "deviations.list", {})
    deviations = week["deviations"]
    open_ = [d for d in deviations if d["outcome"] == "open"]
    grid: dict[str, dict[str, int]] = {}
    for r in await db.overview.deviations_by_day(now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)):
        grid.setdefault(r["day"].date().isoformat(), {})[r["severity"]] = r["n"]
    days = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date().isoformat()
        days.append({"day": day, **{s: grid.get(day, {}).get(s, 0) for s in SEV_ORDER}})
    behind = [m["hostname"] for m in machines if m["behind"]]
    offline = [m["hostname"] for m in machines if not m["online"]]
    return {
        "kpis": {"waiting": len(cards), "urgent": sum(1 for c in cards if c["severity"] in ("high", "critical")),
                 "deviations": len(deviations), "deviations_open": len(open_), "deviations_high": sum(1 for d in open_ if d["severity"] in ("critical", "high")),
                 "machines": summary["machines"], "online": summary["online"], "offline": offline[:5], "offline_count": len(offline),
                 "current_version": fleet["current_version"], "behind": behind[:5], "behind_count": len(behind),
                 "on_current_pct": round(100 * (summary["machines"] - len(behind)) / summary["machines"]) if summary["machines"] else None},
        "decisions": [{k: c[k] for k in ("id", "kind", "severity", "title", "short", "at")} for c in cards],
        "days": days, "worth_a_look": sorted(deviations, key=lambda d: (d["outcome"] != "open", SEV_ORDER.get(d["severity"], 3)))[:8]}


@handler("overview.admin")
async def overview_admin(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """An Admin's figures: Waiting on you (tasks to verify, issues that are theirs, pings), machines online, open issues, sessions held now."""
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    fleet = (await dispatch(ctx, "machines.list", {}))
    issues = await db.issues.list(department_id=ident.department_id, open_only=True)
    mine = [i for i in issues if i["owner_account_id"] in (None, ident.account_id)]
    verify = await db.overview.tasks_to_verify(ident.account_id)
    pings = await db.overview.pings_waiting(ident.account_id)
    by_sev: dict[str, int] = {}
    for i in issues:
        by_sev[i["severity"]] = by_sev.get(i["severity"], 0) + 1
    dept_tasks = await db.department_tasks.list(account_id=ident.account_id)
    unseen = 0
    for t in dept_tasks:
        row = next((a for a in await db.department_tasks.admins([t["id"]]) if a["account_id"] == ident.account_id), None)
        unseen += 1 if row and row["state"] == "told" else 0
    from engine.flow import guard

    suggestions = [p for p in await db.proposals.list("open", 500) if p.get("department_id") == ident.department_id]
    to_allow = [c for c in await db.flows.asked_consents() if guard.can_decide(ident, c)]
    waiting = verify + len(mine) + pings + len(suggestions) + len(to_allow)
    return {"waiting": {"total": waiting, "to_verify": verify, "issues": len(mine), "pings": pings, "department_tasks_unseen": unseen,
                        "suggestions": len(suggestions), "flows_to_allow": len(to_allow)},
            "machines": {"online": fleet["summary"]["online"], "total": fleet["summary"]["machines"], "by_health": fleet["summary"]["by_health"]},
            "issues": {"open": len(issues), "by_severity": by_sev, "unassigned": sum(1 for i in issues if i["owner_account_id"] is None)},
            "sessions_held": await db.overview.sessions_held(ident.department_id), "current_version": fleet["current_version"]}


@handler("overview.departments")
async def overview_departments(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """One row per department (an Admin gets only their own), most in need first: no Admin, something critical, reports that come to the
    Super User, something high, the rest. Median time to address is read from the issues resolved in the last 30 days."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    now = _now()
    depts = [d for d in await db.accounts.list_departments() if ident.role == "super_user" or d["id"] == ident.department_id]
    admin_depts, routed, by_dept = await _context(ctx)
    fleet = (await dispatch(ctx, "machines.list", {}))["machines"]
    issues = await db.issues.list(open_only=True)
    handled: dict[int, list[float]] = {}
    for r in await db.overview.issue_handling(now - timedelta(days=30)):
        handled.setdefault(r["department_id"], []).append(r["minutes"])
    found = await db.reports.board(since=now - timedelta(days=7))
    out = []
    for d in depts:
        ms = [m for m in fleet if m["department_id"] == d["id"]]
        iss = [i for i in issues if i["department_id"] == d["id"]]
        rs = [_view(r, owner_of(r, admin_depts, routed), {}) for r in found if r["department_id"] == d["id"]]
        h = _handling(d, rs, d["id"] in admin_depts)
        names = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in by_dept.get(d["id"], [])]) if by_dept.get(d["id"]) else {}
        worst = min((i["severity"] for i in iss), key=lambda s: SEV_ORDER.get(s, 3), default=None)
        rank = 0 if d["id"] not in admin_depts else 1 if worst == "critical" else 2 if h["to_you"] else 3 if worst == "high" else 4
        out.append({"department_id": d["id"], "name": d["name"], "admins": [names.get(a["id"]) for a in by_dept.get(d["id"], [])], "vacant": d["id"] not in admin_depts,
                    "machines": len(ms), "online": sum(1 for m in ms if m["online"]), "open_issues": len(iss), "worst": worst,
                    "on_current_version": sum(1 for m in ms if not m["behind"]), "behind": sum(1 for m in ms if m["behind"]),
                    "median_minutes": _median(handled.get(d["id"], [])), "reports": h, "rank": rank})
    return {"departments": sorted(out, key=lambda r: (r["rank"], r["name"]))}
