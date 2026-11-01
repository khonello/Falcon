"""The Overviews and the Reports page's figures (Overview for both levels, Reports > Handling, the Super User's decisions).

    reports.board     {days?, department_id?}   reports with where they came from, who may take them, who addressed them and how fast;
                                                the strip (waiting, with the department, addressed, typical time) and per-department handling
    overview.queue    {}                        Super User: what only they can decide -- reports nobody below them can take, a department with
                                                no Admin, a department's work called done -- each with the options and their effects
    overview.decide   {decision, option, ...}   Super User: carry out one option of one decision
    overview.su       {}                        Super User: the four figures, deviations by day and severity, Worth a look
    overview.admin    {}                        Admin: Waiting on you (with their own to-dos due within a day), machines online, open issues, sessions held
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
from engine.permissions import in_scope, int_field, kept, own_department, require_role

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
    if kept(ident):
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


@handler("overview.admin")
async def overview_admin(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """An Admin's figures: Waiting on you (tasks to verify, issues that are theirs, pings), machines online, open issues, sessions held now."""
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    fleet = (await dispatch(ctx, "machines.list", {}))
    issues = await db.issues.list(department_id=own_department(ident), open_only=True)
    mine = [i for i in issues if i["owner_account_id"] in (None, ident.account_id)]
    verify = await db.overview.tasks_to_verify(ident.account_id)
    pings = await db.overview.pings_waiting(ident.account_id)
    by_sev: dict[str, int] = {}
    for i in issues:
        by_sev[i["severity"]] = by_sev.get(i["severity"], 0) + 1
    from engine.flow import guard

    suggestions = [p for p in await db.proposals.list("open", 500) if in_scope(ident, p.get("department_id"))]
    to_allow = [c for c in await db.flows.asked_consents() if guard.can_decide(ident, c)]
    now_ = _now()
    todos = [t for t in await db.todos.list(ident.account_id) if t["due_at"] is not None and t["due_at"] < now_ + timedelta(days=1)]
    waiting = verify + len(mine) + pings + len(suggestions) + len(to_allow)
    return {"waiting": {"total": waiting, "to_verify": verify, "issues": len(mine), "pings": pings,
                        "suggestions": len(suggestions), "flows_to_allow": len(to_allow),
                        "todos_due": len(todos), "todos_overdue": sum(1 for t in todos if t["due_at"] < now_)},
            "machines": {"online": fleet["summary"]["online"], "total": fleet["summary"]["machines"], "by_health": fleet["summary"]["by_health"]},
            "issues": {"open": len(issues), "by_severity": by_sev, "unassigned": sum(1 for i in issues if i["owner_account_id"] is None)},
            "sessions_held": await db.overview.sessions_held(own_department(ident)), "current_version": fleet["current_version"]}


@handler("overview.departments")
async def overview_departments(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """One row per department (an Admin gets only their own), most in need first: no Admin, something critical, reports that come to the
    Super User, something high, the rest. Median time to address is read from the issues resolved in the last 30 days."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    now = _now()
    depts = [d for d in await db.accounts.list_departments() if in_scope(ident, d["id"])]
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
