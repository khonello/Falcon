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

from engine.dispatch import Context, handler, stub

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
    """Super User: everything. Admin: only categories routed to their department."""
    return stub("reports.list", payload)


@handler("reports.mark")
async def mark(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Admin marks a routed report seen/addressed. Never touches Super User's copy; writes a
    `report_addressed_views` row instead."""
    return stub("reports.mark", payload)


@handler("reports.routing_get")
async def routing_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("reports.routing_get", payload)


@handler("reports.routing_set")
async def routing_set(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only. {"category": str, "department_ids": [..]}"""
    return stub("reports.routing_set", payload)


@handler("reports.addressed_view")
async def addressed_view(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only -- the View. Refused for every other role."""
    return stub("reports.addressed_view", payload)
