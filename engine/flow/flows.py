"""Flow definition and management (Flow -> Core Components, Failure Handling, Creation).

Before a flow (or any branch/destination edit) is accepted:
  * Destination Consent -- implicit only when the creator already outranks the destination
    owner; lateral flows and flows into a superior's space need explicit consent.
  * Pre-Flight Collision Check -- destination path vs. existing indexed content in the
    Global File Index; surfaced, never silently overwritten.
  * Cycle Prevention -- validated against the flow graph; a loop is refused.

Failure handling: pause only the affected flow/branch; persistent status on both creator and
destination sides; a predefined fix suggestion per (stage type, failure type) surfaced
reactively; automatic resume once resolved.

Resource folders are never a direct source/destination -- Flow moves resource files under the
hood within the same access tiers (Resource -> Integration).
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub

STAGE_TYPES = ("branch", "transformation", "categorization")
STATUSES = ("active", "paused", "inactive")
SYNC_MODES = ("realtime", "scheduled", "manual")

# Predefined, reactive fix suggestions -- built-in knowledge, never configured upfront.
FAILURE_SUGGESTIONS: dict[tuple[str, str], str] = {
    ("transformation", "convert_failed"): "Remove or reconfigure the Transformation stage.",
    ("categorization", "place_failed"): "Add a fallback category or relax the categorization rule.",
    ("destination", "unreachable"): "Check the destination PC's connection, then resume.",
    ("destination", "permission_denied"): "Grant the flow write access at the destination, then resume.",
}


def has_cycle(edges: list[tuple[str, str]], new_edge: tuple[str, str]) -> bool:
    """Would adding source->destination `new_edge` create a loop in the flow graph?"""
    graph: dict[str, set[str]] = {}
    for a, b in [*edges, new_edge]:
        graph.setdefault(a, set()).add(b)
    start, target = new_edge[1], new_edge[0]
    seen, stack = set(), [start]
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    return False


@handler("flow.create")
async def create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"source": {pc_id, path}, "destinations": [...], "stages": [...], "sync_mode"}
    Runs consent / collision / cycle checks; returns what needs resolving, or the new flow."""
    return stub("flow.create", payload)


@handler("flow.consent")
async def consent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Destination owner grants/denies an explicit Destination Consent request."""
    return stub("flow.consent", payload)


@handler("flow.edit")
async def edit(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Stages/destinations edits re-run the same pre-flight checks."""
    return stub("flow.edit", payload)


@handler("flow.pause")
async def pause(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("flow.pause", payload)


@handler("flow.resume")
async def resume(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("flow.resume", payload)


@handler("flow.delete")
async def delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Status -> inactive; the row and its sync history are kept."""
    return stub("flow.delete", payload)


@handler("flow.list")
async def list_flows(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("flow.list", payload)


@handler("flow.status")
async def status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Per-flow/branch status incl. persistent failure state and its suggestion."""
    return stub("flow.status", payload)


@handler("flow.history")
async def history(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Sync log and conflicts."""
    return stub("flow.history", payload)
