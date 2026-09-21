"""Reading the audit trail (Hierarchy -> Audit & Logging; scenario 1 step 7).

Super User reads everything. An Admin reads entries whose actor is in their department (their
own actions and their Workers'). Workers have no audit surface. Deviations follow the same
scoping. Reading is itself audited only for Super User cross-department review.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from engine.serialize import rows


@handler("audit.recent")
async def recent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"limit"?, "actor_account_id"?, "prefix"?} -> entries newest first."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    limit = min(int_field(payload, "limit", required=False) or 100, 500)
    actor = int_field(payload, "actor_account_id", required=False)
    prefix = str_field(payload, "prefix", required=False)
    if ident.role == "admin":
        dept_ids = {a["id"] for a in await db.accounts.list_department(ident.department_id)}
        if actor is not None and actor not in dept_ids:
            return {"entries": []}
        found = await db.audit.recent(limit=limit * 4, actor_account_id=actor, action_prefix=prefix)
        found = [e for e in found if e["actor_account_id"] in dept_ids][:limit]
    else:
        found = await db.audit.recent(limit=limit, actor_account_id=actor, action_prefix=prefix)
        if actor is not None:
            await ctx.engine.audit.record(ctx, "audit.reviewed", target_type="accounts", target_id=actor)
    names = await db.accounts.display_names_for(
        ident.account_id, sorted({e["actor_account_id"] for e in found if e["actor_account_id"]}))
    out = rows(found)
    for e in out:
        e["actor_name"] = names.get(e["actor_account_id"]) if e["actor_account_id"] else "engine"
    return {"entries": out}


@handler("audit.deviations")
async def deviations(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    found = await ctx.engine.db.audit.deviations(unresolved_only=not payload.get("include_resolved", False))
    if ident.role == "admin":
        dept_ids = {a["id"] for a in await ctx.engine.db.accounts.list_department(ident.department_id)}
        found = [d for d in found if d["surfaced_to_account_id"] in dept_ids or d["observed_account_id"] in dept_ids]
    return {"deviations": rows(found)}
