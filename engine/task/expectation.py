"""Expectation (Task -> Expectation): soft signals that work is happening. Never completion.

File targets ride on the Global File Index's event stream (created / modified / activity
frequency / directory-level activity). Program targets use client-reported usage evidence
(active vs idle, memory footprint, open file descriptors, activity over time). Skipped
entirely when a task's verification is an explicit None.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)


def install(engine: Engine) -> None:
    """Subscribe to the Global File Index so file-target expectations update from the same
    event stream Flow and Resource use."""
    engine.file_index.subscribe(_on_file_event)


async def _on_file_event(event: dict[str, Any]) -> None:
    # SCAFFOLD: match event name/path against active tasks' File items; bump activity signals;
    # for 'update' items compare against baseline_at.
    log.debug("expectation: file event %s", event.get("op"))


@handler("task.program_signal")
async def program_signal(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker Client reports usage evidence for a Program target:
    {"task_id", "item_index", "active": bool, "rss_bytes": int, "open_files": [..]}"""
    return stub("task.program_signal", payload)
