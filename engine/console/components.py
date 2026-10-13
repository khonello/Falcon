"""A Worker's own parts, as the Engine hears of them: the indexer and the event tracker run as their own programs under the
Worker service (`worker_client.childproc`), which restarts them. If one keeps dying the service says so here, and it is an
issue on that machine until a later report says it is healthy again.

    control.component_status {component: "indexer"|"tracker", healthy: bool}      (a machine's own report)
"""

from __future__ import annotations

from typing import Any

from engine.console import issues
from engine.dispatch import Context, handler
from engine.permissions import require_account
from protocol import ErrorCode, ProtocolError

COMPONENTS = {"indexer": "The file indexer", "tracker": "The event tracker"}


@handler("control.component_status")
async def component_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only a machine reports its own parts")
    name = str(payload.get("component") or "")
    if name not in COMPONENTS:
        raise ProtocolError(ErrorCode.INVALID, f"component must be one of {', '.join(COMPONENTS)}")
    healthy = bool(payload.get("healthy"))
    source = ident.pc_id * 10 + (1 if name == "indexer" else 2)       # one issue per machine and part
    if healthy:
        await issues.resolve_source(ctx.engine, "component_status", source, f"{COMPONENTS[name]} is running steadily again")
        return {"raised": False}
    _, created = await issues.raise_issue(
        ctx.engine, type_="component", severity="medium", title=f"{COMPONENTS[name]} keeps stopping",
        subject=name, pc_id=ident.pc_id, source_table="component_status", source_id=source,
        detail={"component": name})
    await ctx.engine.audit.record(ctx, "component.unhealthy", target_type="pcs", target_id=ident.pc_id, pc_id=ident.pc_id,
                                  detail={"component": name})
    return {"raised": created}
