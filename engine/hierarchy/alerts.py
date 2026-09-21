"""System Alerts & Announcements (Hierarchy -> System Alerts & Announcements).

Types: emergency | warning | announcement | routine.
Audience: admin_only | department | all_users | specific_users -- who may create each is
role-gated (all_users is Super User only). Delivery: immediate, scheduled, or recurring, via
the Scheduler; every alert is audited.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub

ALERT_TYPES = ("emergency", "warning", "announcement", "routine")
AUDIENCES = ("admin_only", "department", "all_users", "specific_users")


@handler("alerts.create")
async def create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"type", "audience", "department_id"?, "account_ids"?, "body", "action_link"?,
    "schedule": {"at": iso?, "recurrence": ...?}}"""
    return stub("alerts.create", payload)


@handler("alerts.list")
async def list_alerts(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Alerts addressed to the caller's role/department/account."""
    return stub("alerts.list", payload)
