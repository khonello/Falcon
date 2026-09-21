"""Display Names (Hierarchy -> Display Names; schema `display_name_grants`).

Naming is strictly top-down and NEVER propagates between relationship layers: what Super User
privately calls an Admin is invisible to that Admin's Workers, who see only the Admin's own
self-facing name -- or a composed fallback built from existing identifiers.

Enforcement is a query rule, not a schema rule: every name resolution filters grants by
`namer_account_id = viewer`, never joining across other namers. The single easiest rule in the
system to break with a careless join -- see `AccountsRepo.display_name_for`.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub


def composed_fallback(account_id: int, hostname: str | None, department: str | None) -> str:
    """Derived at query time, never stored, so it can't go stale."""
    parts = [p for p in (hostname, department) if p]
    return f"{'-'.join(parts) or 'account'}-{account_id}"


@handler("hierarchy.set_display_name")
async def set_display_name(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_id": int, "label": str} -- caller must outrank the named account (top-down only)."""
    return stub("hierarchy.set_display_name", payload)


@handler("hierarchy.set_self_name")
async def set_self_name(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"label": str} -- the name shown to those *below* the caller."""
    return stub("hierarchy.set_self_name", payload)


@handler("hierarchy.resolve_names")
async def resolve_names(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"account_ids": [..]} -> {id: name} as seen by the caller only."""
    return stub("hierarchy.resolve_names", payload)
