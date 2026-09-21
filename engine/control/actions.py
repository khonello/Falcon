"""Action library (Control -> Action, Control, Monitoring, Custom Actions).

An Action is atomic: Control (do something) or Monitoring (observe something), each with its
own timeout and manual termination, independent of any other Action in the same Event chain.
Custom is a distinct third category (Admin-authored scripts), never merged into the other two.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub

CATEGORIES = ("control", "monitoring", "custom")
TIMING = ("immediate", "scheduled", "delayed", "recurring")
STATUSES = ("pending", "success", "failed", "terminated", "timeout")
SCRIPT_LANGUAGES = ("powershell", "python")

# Built-in actions ship as (category, key) with a spec the worker client knows how to execute.
BUILTIN: dict[str, dict[str, Any]] = {
    # control
    "control.screenshot": {"category": "control", "params": []},
    "control.notify": {"category": "control", "params": ["message"]},
    "control.lock_session": {"category": "control", "params": ["duration_s"]},
    "control.rename_file": {"category": "control", "params": ["path", "new_name"]},
    "control.kill_process": {"category": "control", "params": ["name"]},
    # monitoring
    "monitoring.process_list": {"category": "monitoring", "params": []},
    "monitoring.cpu_memory": {"category": "monitoring", "params": []},
    "monitoring.file_activity": {"category": "monitoring", "params": ["path"]},
    "monitoring.idle_time": {"category": "monitoring", "params": []},
}


@handler("control.action_list")
async def action_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Library: built-ins plus this Admin's Custom actions, grouped by category."""
    return stub("control.action_list", payload)


@handler("control.action_create")
async def action_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"name", "category", "builtin_key"? | "script": {"language", "source"}, "timeout_s",
    "timing": {...}}. Custom requires Admin role and passes `custom_actions.validate`."""
    return stub("control.action_create", payload)


@handler("control.action_update")
async def action_update(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("control.action_update", payload)


@handler("control.action_delete")
async def action_delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("control.action_delete", payload)


@handler("control.action_run")
async def action_run(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Run an Action now on a target PC, outside any Event. {"action_id", "pc_id"}"""
    return stub("control.action_run", payload)
