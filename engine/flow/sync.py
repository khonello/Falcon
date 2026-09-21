"""Synchronization (Flow -> Synchronization Mechanism, Conflict Handling).

Trigger: the Global File Index's event stream, filtered against registered flow sources on that
PC. Only matches trigger a sync check. Polling fallback per source where native events prove
unreliable.

Write attribution: every sync-driven write carries (hash, who, hierarchy level) so the flow can
tell its own writes from external ones. An external modification at a destination is preserved
as `<name>-modified.<ext>` and a fresh copy is synced from source alongside it.

The Engine coordinates; the actual file moves/transforms run on the agent that owns the
destination (or the source, for Admin-to-Admin flows), via the Script Execution Model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WriteAttribution:
    content_hash: str
    account_id: int | None
    role: str | None
    flow_id: int | None  # set for sync-driven writes; None means external


def is_own_write(attr: WriteAttribution, flow_id: int) -> bool:
    return attr.flow_id == flow_id


def modified_name(path: str) -> str:
    """report.xlsx -> report-modified.xlsx"""
    p = PurePath(path)
    return str(p.with_name(f"{p.stem}-modified{p.suffix}"))


def install(engine: "Engine") -> None:
    engine.file_index.subscribe(_on_file_event)


async def _on_file_event(event: dict[str, Any]) -> None:
    # SCAFFOLD:
    #   sources = db.flows.sources_for_pc(event.pc_id); if event.path not under any -> return
    #   for each matching flow: propagate(engine, flow, event)
    log.debug("flow sync: file event %s on pc %s", event.get("op"), event.get("pc_id"))


async def propagate(engine: "Engine", flow: dict[str, Any], event: dict[str, Any]) -> None:
    """Walk stages; dispatch per-destination sync commands to the owning agent; log the sync;
    on failure pause only the affected branch and write the persistent failure status."""
    ...


@handler("flow.destination_write")
async def destination_write(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Agent reports a write observed at a flow destination with its attribution, so the Engine
    can classify it as own-sync vs. external (conflict)."""
    return stub("flow.destination_write", payload)


@handler("flow.sync_result")
async def sync_result(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Agent reports the outcome of a sync command: {"flow_id", "branch_id", "status",
    "failure": {"stage_type", "kind"}?}. Failures pause the branch and surface a suggestion."""
    return stub("flow.sync_result", payload)


@handler("flow.trigger")
async def trigger(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Manual sync trigger for sync_mode='manual'."""
    return stub("flow.trigger", payload)
