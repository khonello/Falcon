"""Parked with the Super User (docs/design/v1-it-admin.md), 1 Nov 2026: handlers only that role could call, cut from the shipped Engine.
Each block names the file it came from and goes back there, with that file's imports."""

# --- from engine/hierarchy/reports.py
@handler("reports.addressed_view")
async def addressed_view(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only -- the View: who addressed what, when. Refused for every other role,
    and structurally never a Report."""
    require_role(ctx, "super_user")
    return {"addressed": rows(await ctx.engine.db.reports.addressed_views())}


# --- from engine/hierarchy/reports.py
@handler("reports.routing_get")
async def routing_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user")
    return {"categories": list(CATEGORIES), "fixed": sorted(FIXED_CATEGORIES),
            "routing": rows(await ctx.engine.db.reports.routing_config())}


# --- from engine/hierarchy/reports.py
@handler("reports.routing_set")
async def routing_set(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User only. {"category": str, "department_ids": [..], "include_earlier": bool = true}
    -- sets the routed departments for that category, one category per call; an empty list sends
    it back to the Super User only. Additive to Super User's own visibility, always.

    `include_earlier` applies to departments added by this call: true, they also see the reports
    of this category already written (and can address the ones nobody has); false, only reports
    written from now on. Departments already routed keep what they had. A department removed stops
    seeing the category; what it addressed stays recorded in the Super User's View."""
    ident = require_role(ctx, "super_user")
    category = str_field(payload, "category", choices=CATEGORIES)
    if category in FIXED_CATEGORIES:
        raise ProtocolError(ErrorCode.FORBIDDEN, f"{category} reports go to the Super User only and cannot be routed")
    dept_ids = payload.get("department_ids")
    if not isinstance(dept_ids, list):
        raise ProtocolError(ErrorCode.INVALID, "department_ids must be a list")
    dept_ids = sorted({int(d) for d in dept_ids})
    include_earlier = payload.get("include_earlier", True)
    if not isinstance(include_earlier, bool):
        raise ProtocolError(ErrorCode.INVALID, "include_earlier must be true or false")
    known = {d["id"] for d in await ctx.engine.db.accounts.list_departments()}
    if unknown := set(dept_ids) - known:
        raise ProtocolError(ErrorCode.NOT_FOUND, f"unknown departments {sorted(unknown)}")
    db = ctx.engine.db
    changed = await db.reports.set_routing(category, dept_ids, ident.account_id, include_earlier)
    earlier = await db.reports.earlier_unaddressed(category) if changed["added"] and include_earlier else 0
    await ctx.engine.audit.record(ctx, "report_routing.set", detail={
        "category": category, "departments": dept_ids, "added": changed["added"], "removed": changed["removed"],
        "include_earlier": include_earlier, "earlier_unaddressed": earlier})
    return {"category": category, "department_ids": dept_ids, **changed, "include_earlier": include_earlier,
            "earlier_unaddressed": earlier}


# --- from engine/hierarchy/accounts.py
@handler("hierarchy.admin_limit")
async def admin_limit(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_id", "on": bool} -- Super User only. Limit an Admin to working hours (they cannot enter a machine outside them), or lift it."""
    require_role(ctx, "super_user")
    account_id = int_field(payload, "account_id")
    on = payload.get("on", True)
    if not isinstance(on, bool):
        raise ProtocolError(ErrorCode.INVALID, "on must be true or false")
    subject = await ctx.engine.db.accounts.by_id(account_id)
    if subject is None or subject["role"] != "admin" or subject["status"] != "active":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active Admin")
    await ctx.engine.db.accounts.set_hours_limited(account_id, on)
    await ctx.engine.audit.record(ctx, "admin.limited" if on else "admin.limit_lifted", target_type="accounts", target_id=account_id)
    await ctx.engine.push_to_account(account_id, "account.limited", {"on": on, "working_hours": ctx.engine.settings.working_hours})
    return {"account_id": account_id, "hours_limited": on}
