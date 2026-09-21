"""Cross-Department Assisted Access (Hierarchy -> Cross-Department Assisted Access; spec 7.1).

A consent-based, temporary, peer-to-peer relationship between Admins. Deliberately its own
state machine -- it does NOT reuse the traversal code path, because entry is granted by
consent, not seized by authority (no block-or-end-first, no eviction mechanic).

Two entry paths, both live at once:
  * requester-initiated: request help, optionally targeting a department; matched to an
    available Admin (not occupying any session, opted in as reachable)
  * helper-initiated: broadcast availability; a requester acts on it directly

No lingering requests: no match now -> "try again", never queued.

Access is two-layered: a system-defined baseline ceiling per department/Admin, which the
requester may only narrow, never loosen. Once granted, the session behaves like any occupied
session (overlay, blocked to others) and ends when either party closes it. Every instance is a
Report under its own category; Super User always sees it, no approval gate.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub

STATES = ("requested", "matched", "active", "closed", "no_match")


@handler("assisted_access.request")
async def request(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"department_id": int?, "narrowing": {...}?} -> matched helper or `no_match`."""
    return stub("assisted_access.request", payload)


@handler("assisted_access.set_available")
async def set_available(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Helper broadcasts / withdraws availability. {"available": bool}"""
    return stub("assisted_access.set_available", payload)


@handler("assisted_access.available_helpers")
async def available_helpers(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Moment-in-time list of Admins currently reachable (not occupying a session, opted in)."""
    return stub("assisted_access.available_helpers", payload)


@handler("assisted_access.accept")
async def accept(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Helper consents; opens a session with occupied_via='assisted_access' and writes the
    'Cross-Department Assistance' Report."""
    return stub("assisted_access.accept", payload)


@handler("assisted_access.close")
async def close(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Either party ends it."""
    return stub("assisted_access.close", payload)


def effective_scope(baseline_ceiling: dict[str, Any], narrowing: dict[str, Any]) -> dict[str, Any]:
    """Intersect: the requester can only remove from the ceiling, never add to it."""
    return {k: v for k, v in baseline_ceiling.items() if narrowing.get(k, True)}  # SCAFFOLD shape
