"""Display Names (Hierarchy -> Display Names; schema `display_name_grants`).

Naming is strictly top-down and NEVER propagates between relationship layers: what Super User
privately calls an Admin is invisible to that Admin's Workers, who see only the Admin's own
self-facing name -- or a composed fallback built from existing identifiers.

Enforcement is a query rule, not a schema rule: `AccountsRepo.display_names_for` filters grants
by `namer_account_id = viewer` and nothing else.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, outranks, require_account, require_role, str_field
from protocol import ErrorCode, ProtocolError


def composed_fallback(account_id: int, hostname: str | None, department: str | None) -> str:
    """Derived at query time, never stored, so it can't go stale."""
    parts = [p for p in (hostname, department) if p]
    return f"{'-'.join(parts) or 'account'}-{account_id}"


@handler("hierarchy.set_display_name")
async def set_display_name(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_id": int, "label": str} -- the caller must outrank the named account
    (naming authority is top-down only). The label is private to the caller's view."""
    ident = require_role(ctx, "super_user", "admin")
    account_id = int_field(payload, "account_id")
    label = str_field(payload, "label")
    subject = await ctx.engine.db.accounts.by_id(account_id)
    if subject is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such account")
    if not outranks(ident.role, subject["role"]):
        raise ProtocolError(ErrorCode.FORBIDDEN, "naming is top-down only")
    if ident.role == "admin" and subject["department_id"] != ident.department_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "outside your department")
    await ctx.engine.db.accounts.grant_display_name(ident.account_id, account_id, label)
    await ctx.engine.audit.record(ctx, "display_name.set", target_type="accounts", target_id=account_id)
    return {"account_id": account_id, "label": label}


@handler("hierarchy.set_self_name")
async def set_self_name(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"label": str | null} -- the name shown to those *below* the caller."""
    ident = require_account(ctx)
    label = str_field(payload, "label", required=False)
    await ctx.engine.db.accounts.set_self_name(ident.account_id, label)
    await ctx.engine.audit.record(ctx, "display_name.self", target_type="accounts", target_id=ident.account_id)
    return {"label": label}


@handler("hierarchy.resolve_names")
async def resolve_names(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_ids": [..]} -> {"names": {id: name}} as seen by the caller only."""
    ident = require_account(ctx)
    ids = payload.get("account_ids")
    if not isinstance(ids, list):
        raise ProtocolError(ErrorCode.INVALID, "account_ids must be a list")
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [int(i) for i in ids])
    return {"names": {str(k): v for k, v in names.items()}}
