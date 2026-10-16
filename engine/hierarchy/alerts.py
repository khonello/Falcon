"""System Alerts & Announcements (Hierarchy -> System Alerts & Announcements).

Types: emergency | warning | announcement | routine.
Audience and who may create it:
    admin_only      Super User or Admin        -> all Admins + Super User
    department      Super User or that dept's Admin -> Admins & Workers of the department
    all_users       Super User only            -> everyone
    specific_users  Super User or Admin        -> the listed accounts (Admin: own dept only)
Delivery: immediate, or scheduled (`deliver_at`); recurring is stored and left to the
Scheduler. Every alert is audited; delivery is a push plus the alert list.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler
from engine.isotime import parse_iso
from engine.permissions import (
    int_field,
    require_account,
    require_department_scope,
    require_role,
    str_field,
)
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

ALERT_TYPES = ("emergency", "warning", "announcement", "routine")
AUDIENCES = ("admin_only", "department", "all_users", "specific_users")


@handler("alerts.create")
async def create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"type", "audience", "body", "department_id"?, "account_ids"?, "action_link"?,
    "deliver_at": iso?, "recurrence": {...}?}"""
    ident = require_role(ctx, "super_user", "admin")
    alert_type = str_field(payload, "type", choices=ALERT_TYPES)
    audience = str_field(payload, "audience", choices=AUDIENCES)
    body = str_field(payload, "body")
    title = " ".join(str(payload.get("title") or "").split())[:120] or None
    department_id = int_field(payload, "department_id", required=audience == "department")
    account_ids = payload.get("account_ids")
    if audience == "all_users" and ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "all-users alerts are Super User only")
    if audience == "department":
        require_department_scope(ident, department_id)
    if audience == "specific_users":
        if not isinstance(account_ids, list) or not account_ids:
            raise ProtocolError(ErrorCode.INVALID, "account_ids required for specific_users")
        account_ids = [int(a) for a in account_ids]
        if ident.role == "admin":
            for aid in account_ids:
                acct = await ctx.engine.db.accounts.by_id(aid)
                if acct is None or acct["department_id"] != ident.department_id:
                    raise ProtocolError(ErrorCode.FORBIDDEN, f"account {aid} is outside your department")
    else:
        account_ids = None
    deliver_at = None
    if payload.get("deliver_at"):
        try:
            deliver_at = parse_iso(str(payload["deliver_at"]))
        except ValueError as exc:
            raise ProtocolError(ErrorCode.INVALID, "deliver_at must be ISO 8601") from exc
    alert_id = await ctx.engine.db.alerts.create(
        ident.account_id, alert_type, audience, body, department_id=department_id,
        recipient_account_ids=account_ids, action_link=payload.get("action_link"),
        deliver_at=deliver_at, recurrence=payload.get("recurrence"), title=title)
    await ctx.engine.audit.record(ctx, "alert.created", target_type="system_alerts", target_id=alert_id,
                                  detail={"type": alert_type, "audience": audience, "title": title})
    if deliver_at is None:
        await deliver(ctx.engine, {"id": alert_id, "alert_type": alert_type, "audience": audience, "body": body, "title": title,
                                   "department_id": department_id, "recipient_account_ids": account_ids,
                                   "action_link": payload.get("action_link")})
        await ctx.engine.db.alerts.mark_delivered(alert_id)
    return {"alert_id": alert_id, "deliver_at": deliver_at.isoformat() if deliver_at else None}


async def deliver(engine: Any, alert: dict[str, Any]) -> None:
    """Push to every connected recipient. Offline users pick it up from alerts.list."""
    audience = alert["audience"]
    payload = {k: alert.get(k) for k in ("id", "alert_type", "audience", "title", "body", "action_link")}

    def wants(c: Any) -> bool:
        i = c.ctx.identity
        if audience == "all_users":
            return True
        if audience == "admin_only":
            return i.role in ("admin", "super_user")
        if audience == "department":
            return i.department_id == alert["department_id"]
        return i.account_id in (alert.get("recipient_account_ids") or [])

    await engine.broadcast("alert.delivered", payload, predicate=wants)


async def deliver_due(engine: Any) -> int:
    """Scheduler job: deliver scheduled alerts whose time has come, exactly once."""
    if not engine.db.connected:
        return 0
    n = 0
    for alert in await engine.db.alerts.due_undelivered():
        await deliver(engine, alert)
        await engine.db.alerts.mark_delivered(alert["id"])
        await engine.audit.record(None, "alert.delivered", target_type="system_alerts", target_id=alert["id"])
        n += 1
    return n


@handler("alerts.list")
async def list_alerts(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Delivered alerts addressed to the caller's role/department/account."""
    ident = require_account(ctx)
    found = await ctx.engine.db.alerts.for_account(ident.account_id, ident.role, ident.department_id)
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, sorted({a["created_by_account_id"] for a in found}))
    out = rows(found)
    for a in out:
        a["from_name"] = names.get(a["created_by_account_id"])          # as the reader names them, never anyone else's name for them
    return {"alerts": out}


@handler("alerts.sent")
async def sent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """What this person has sent, scheduled or withdrawn (the Super User: everything), with who it reached."""
    ident = require_role(ctx, "super_user", "admin")
    found = await ctx.engine.db.alerts.sent(None if ident.role == "super_user" else ident.account_id)
    depts = {d["id"]: d["name"] for d in await ctx.engine.db.accounts.list_departments()}
    out = rows(found)
    for a in out:
        a["status"] = "withdrawn" if a["cancelled_at"] else "delivered" if a["delivered_at"] else "scheduled"
        a["audience_label"] = {"all_users": "Everyone", "admin_only": "All Admins", "department": depts.get(a["department_id"], "A department"),
                               "specific_users": f"{len(a['recipient_account_ids'] or [])} chosen people"}[a["audience"]]
    return {"alerts": out}


@handler("alerts.cancel")
async def cancel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Withdraw a scheduled announcement before it goes out. {"alert_id"}; its sender, or the Super User."""
    ident = require_role(ctx, "super_user", "admin")
    alert = await ctx.engine.db.alerts.get(int_field(payload, "alert_id"))
    if alert is None or (ident.role != "super_user" and alert["created_by_account_id"] != ident.account_id):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such announcement of yours")
    if not await ctx.engine.db.alerts.cancel(alert["id"]):
        raise ProtocolError(ErrorCode.CONFLICT, "it has already been delivered or withdrawn")
    await ctx.engine.audit.record(ctx, "alert.withdrawn", target_type="system_alerts", target_id=alert["id"])
    return {"alert_id": alert["id"], "status": "withdrawn"}
