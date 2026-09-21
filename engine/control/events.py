"""Events (Control -> Events, Actions + Events = Automation).

Two evaluation mechanisms, chosen per event type by how it is actually detected:
  * native/pushed  -- OS-emitted (file change, USB, login/logout, program launch). Worker Clients relay
                      the signal; the Engine matches it against registered definitions.
  * polled/evaluated -- state, not occurrence (thresholds, idle duration, scheduled time).
                      Checked on an interval by the Scheduler, Engine-side.

When an Event fires, each attached Action is dispatched as its own independent execution --
no ordering dependency, no output piping (v1).

Task deadlines are Events (kind='scheduled', trigger='task.deadline'), not a separate scheduler.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

MECHANISMS = ("native", "polled")

# Event type -> mechanism. Extend as types are defined; the classification follows detection.
EVENT_TYPES: dict[str, str] = {
    "file.created": "native",
    "file.modified": "native",
    "file.accessed": "native",
    "usb.inserted": "native",
    "usb.removed": "native",
    "user.login": "native",
    "user.logout": "native",
    "program.launched": "native",
    "network.connected": "native",
    "system.idle": "polled",
    "threshold.cpu": "polled",
    "threshold.memory": "polled",
    "time.scheduled": "polled",
    "time.recurring": "polled",
    "task.deadline_soft": "polled",
    "task.deadline_final": "polled",
    "task.started": "native",
    "task.target_appeared": "native",
    "flow.failed": "native",
    "resource.violation": "native",
}


async def on_signal(engine: Engine, pc_id: int, event_type: str, data: dict[str, Any]) -> None:
    """Entry point for native/pushed signals (from worker clients) and internal signals (Flow failure,
    Resource violation, Task target appeared). Matches definitions, fires attached Actions."""
    from engine.control import executions

    for definition in await engine.db.control.event_definitions(kind=event_type) or []:
        if not _matches(definition, pc_id, data):
            continue
        await engine.audit.record(None, "event.fired", target_type="event", target_id=definition["id"],
                                  detail={"pc_id": pc_id, "type": event_type})
        for action in await engine.db.control.actions_for_event(definition["id"]) or []:
            await executions.start(engine, action, definition["id"], pc_id)


def _matches(definition: dict[str, Any], pc_id: int, data: dict[str, Any]) -> bool:
    """Compare `condition_spec` (shape is an implementation-phase decision) with the signal."""
    return True  # SCAFFOLD


async def evaluate_polled(engine: Engine) -> None:
    """Scheduler job: check every polled/evaluated definition against current state."""
    # SCAFFOLD


@handler("control.event_create")
async def event_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"type", "condition_spec", "pc_ids", "action_ids": [..]}"""
    return stub("control.event_create", payload)


@handler("control.event_update")
async def event_update(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("control.event_update", payload)


@handler("control.event_delete")
async def event_delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("control.event_delete", payload)


@handler("control.event_list")
async def event_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("control.event_list", payload)


@handler("control.signal")
async def signal(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker Client relays a native OS signal: {"type": "usb.inserted", "data": {...}}"""
    pc_id = ctx.identity.pc_id or int(payload.get("pc_id", 0))
    await on_signal(ctx.engine, pc_id, str(payload.get("type", "")), payload.get("data", {}))
    return {"accepted": True}
