"""Report Routing (Hierarchy -> Report Routing; schema 8).

Two strictly distinct categories:
  * Reports (routable): system-generated, auto-categorized by origin -- Resource violation,
    Directory Structure Conflict, Flow failure, Listener report, Cross-Department Assistance,
    update status, ...
  * Views (never routable, Super User-only): meta-information about reports -- who addressed
    what, when. Kept in `report_addressed_views`, never insertable as a Report row.

Super User always receives every report. Routing is additive: a routed category ALSO reaches
every Admin in the routed department (the department as a whole, no designated contact).

`emit()` is the single write path every combo uses to raise a report.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

CATEGORIES = (
    "resource_violation",
    "directory_structure_conflict",
    "flow_failure",
    "listener_report",
    "cross_department_assistance",
    "update_status",
    "deviation",
)


async def emit(engine: Engine, category: str, *, source_table: str, source_id: int,
               summary: str) -> int:
    """Write once; visibility is decided at read time from `report_routing_config`. The push
    goes to every Super User connection and to Admins of departments the category routes to."""
    assert category in CATEGORIES, category
    if not engine.db.connected:
        log.info("REPORT (no db) %s: %s", category, summary)
        return 0
    report_id = await engine.db.reports.write(category, source_table, source_id)
    log.info("REPORT %s #%s: %s", category, report_id, summary)
    routed = set(await engine.db.reports.departments_for_category(category))
    await engine.broadcast(
        "report.new", {"id": report_id, "category": category, "summary": summary},
        predicate=lambda c: c.ctx.identity.role == "super_user"
        or (c.ctx.identity.role == "admin" and c.ctx.identity.department_id in routed))
    return report_id




@handler("reports.list")
async def list_reports(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User: everything, unconditionally. Admin: only categories routed to their
    department (the routed pane). Workers have no reports."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    if ident.role == "super_user":
        found = await db.reports.all()
    else:
        found = await db.reports.routed_to_department(ident.department_id)
    return {"reports": rows(found)}


@handler("reports.mark")
async def mark(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"report_id": int}. An Admin in a routed department marks a report addressed. Never
    touches the report row; writes a `report_addressed_views` row (Super User's View)."""
    ident = require_role(ctx, "admin")
    report_id = int_field(payload, "report_id")
    db = ctx.engine.db
    visible = {r["id"] for r in await db.reports.routed_to_department(ident.department_id)}
    if report_id not in visible:
        raise ProtocolError(ErrorCode.NOT_FOUND, "report is not routed to your department")
    view_id = await db.reports.mark_addressed(report_id, ident.account_id)
    await ctx.engine.audit.record(ctx, "report.addressed", target_type="reports", target_id=report_id)
    await ctx.engine.push_to_role("super_user", "report.addressed",
                                  {"report_id": report_id, "by_account_id": ident.account_id,
                                   "department_id": ident.department_id})
    return {"view_id": view_id}


@handler("reports.routing_get")
async def routing_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user")
    return {"categories": list(CATEGORIES), "routing": rows(await ctx.engine.db.reports.routing_config())}


@handler("reports.routing_set")
async def routing_set(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only. {"category": str, "department_ids": [..]} -- replaces the routed
    departments for that category. Additive to Super User's own visibility, always."""
    ident = require_role(ctx, "super_user")
    category = str_field(payload, "category", choices=CATEGORIES)
    dept_ids = payload.get("department_ids")
    if not isinstance(dept_ids, list):
        raise ProtocolError(ErrorCode.INVALID, "department_ids must be a list")
    dept_ids = [int(d) for d in dept_ids]
    known = {d["id"] for d in await ctx.engine.db.accounts.list_departments()}
    if unknown := set(dept_ids) - known:
        raise ProtocolError(ErrorCode.NOT_FOUND, f"unknown departments {sorted(unknown)}")
    await ctx.engine.db.reports.set_routing(category, dept_ids, ident.account_id)
    await ctx.engine.audit.record(ctx, "report_routing.set", detail={"category": category, "departments": dept_ids})
    return {"category": category, "department_ids": dept_ids}


@handler("reports.addressed_view")
async def addressed_view(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only -- the View: who addressed what, when. Refused for every other role,
    and structurally never a Report."""
    require_role(ctx, "super_user")
    return {"addressed": rows(await ctx.engine.db.reports.addressed_views())}
