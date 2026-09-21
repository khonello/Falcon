"""Expectation (Task -> Expectation): soft signals that work is happening. Never completion.

File targets ride on the Global File Index's event stream (created / modified / activity).
Program targets use worker-client-reported usage evidence (active vs idle, memory footprint,
open file descriptors, running state). Skipped entirely when a task's verification is an
explicit None.

Signals recorded in `expectations`:
    file_created, file_modified, file_activity          (from index events)
    process_state {running, active, rss_bytes}, process_active, open_file_descriptor
    {open_files}, program_present {present}             (from task.program_signal)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_account
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)


def install(engine: Engine) -> None:
    """Subscribe to the Global File Index so file-target expectations update from the same
    event stream Flow and Resource use."""
    engine.file_index.subscribe(lambda event: _on_file_event(engine, event))


async def _on_file_event(engine: Engine, event: dict[str, Any]) -> None:
    if not engine.db.connected:
        return
    name = (event.get("name") or "").lower()
    if not name:
        return
    for task in await engine.db.tasks.active_for_pc(event["pc_id"]):
        if task["verification_mode"] == "none":
            continue
        touched = False
        for item in task["items"]:
            if item["target_type"] != "file":
                continue
            same_file = item.get("file_index_id") is not None and item["file_index_id"] == event.get("file_index_id")
            same_name = (item.get("proposed_filename") or "").lower() == name
            if not (same_file or same_name):
                continue
            if item["intent"] == "create" and item.get("file_index_id") is None and event["op"] != "delete":
                if item.get("proposed_path") and not _under(event["path"], item["proposed_path"]):
                    continue
                await engine.db.tasks.bind_item_file(item["id"], event["file_index_id"])
                await engine.db.tasks.add_expectation(item["id"], "file_created", {"path": event["path"]})
                from engine.control import events

                await events.on_signal(engine, event["pc_id"], "task.target_appeared",
                                       {"task_id": task["id"], "item_id": item["id"], "path": event["path"]})
                touched = True
            else:
                signal = "file_modified" if event["op"] in ("modify", "create", "copy", "move") else "file_activity"
                await engine.db.tasks.add_expectation(item["id"], signal, {"op": event["op"], "path": event["path"],
                                                                           "hash": event.get("hash")})
                touched = True
        if touched:
            await push_stack(engine, task["id"])


def _under(path: str, folder: str) -> bool:
    p, f = path.replace("\\", "/").lower().rstrip("/"), folder.replace("\\", "/").lower().rstrip("/")
    return p.startswith(f + "/")


async def push_stack(engine: Engine, task_id: int) -> None:
    """Re-evaluate the stack and push it to both parties (the assigner's live status view)."""
    from engine.task import verification

    stack = await verification.evaluate_stack(engine, task_id)
    task = await engine.db.tasks.get(task_id)
    if task is None:
        return
    payload = {"task_id": task_id, "items": rows(stack)}
    await engine.push_to_account(task["assigner_account_id"], "task.stack", payload)
    await engine.push_to_account(task["assignee_account_id"], "task.stack", payload)


@handler("task.program_signal")
async def program_signal(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker client reports usage evidence for a Program target:
    {"task_id", "item_id", "running": bool, "active": bool, "rss_bytes": int?,
     "open_files": [..]?, "present": bool?}"""
    ident = require_account(ctx)
    task_id = int_field(payload, "task_id")
    item_id = int_field(payload, "item_id")
    db = ctx.engine.db
    task = await db.tasks.get(task_id)
    if task is None or task["assignee_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such task assigned to you")
    item = next((i for i in task["items"] if i["id"] == item_id), None)
    if item is None or item["target_type"] != "program":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such program item on this task")
    if task["verification_mode"] == "none":
        return {"recorded": False}

    running = bool(payload.get("running", False))
    await db.tasks.add_expectation(item_id, "process_state", {
        "running": running, "active": bool(payload.get("active", False)),
        "rss_bytes": payload.get("rss_bytes")})
    if payload.get("active"):
        await db.tasks.add_expectation(item_id, "process_active", {"rss_bytes": payload.get("rss_bytes")})
    if payload.get("open_files"):
        await db.tasks.add_expectation(item_id, "open_file_descriptor", {"open_files": list(payload["open_files"])})
    if "present" in payload:
        await db.tasks.add_expectation(item_id, "program_present", {"present": bool(payload["present"])})
    await push_stack(ctx.engine, task_id)
    return {"recorded": True}
