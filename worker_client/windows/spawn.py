"""Opening a Worker window from the service: its own process, never blocking the loop (spec: the helper exes are
spawned with `asyncio.create_subprocess_exec`). A window that stays (blocked, locked) is closed by the service; one
that asks something hands back the person's answer."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from worker_client.windows import available

log = logging.getLogger(__name__)
_warned = False


class WindowHandle:
    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self.proc = proc

    async def answer(self) -> dict[str, Any] | None:
        """The person's answer, or None if the window was closed without one."""
        assert self.proc.stdout is not None
        line = await self.proc.stdout.readline()
        await self.proc.wait()
        try:
            return json.loads(line) if line.strip() else None
        except ValueError:
            return None

    def close(self) -> None:
        if self.proc.returncode is None:
            self.proc.terminate()


async def open_window(kind: str, spec: dict[str, Any]) -> WindowHandle | None:
    """Show one window; None when this machine has no window support (the headless install), said once."""
    global _warned
    if not available():
        if not _warned:
            log.warning("the Worker's windows need the worker-ui extra (PySide6); running without them")
            _warned = True
        return None
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "worker_client.windows", kind, json.dumps(spec),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    return WindowHandle(proc)


async def open_tray() -> WindowHandle | None:
    """Start the tray icon (the person's way of asking for help); None on a headless install."""
    if not available():
        return None
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "worker_client.windows.tray",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    return WindowHandle(proc)


def task_spec(task: dict[str, Any]) -> dict[str, Any]:
    """A task as the assignee reads it (TK07): what, when it is due, and the signs that will show the work."""
    text = str(task.get("description_raw") or "")
    first = text.split(".")[0].strip()
    signs = []
    for item in task.get("items") or []:
        if item.get("removed"):
            continue
        name = item.get("name") or item.get("program_name") or item.get("path") or "a file"
        seen = next((item.get(k) for k in ("satisfied_at", "changed_at", "last_seen_at") if item.get(k)), None)
        signs.append({"name": name, "program": item.get("target_type") == "program", "seen": seen,
                      "hint": "save it anywhere; it is found by name" if item.get("intent") == "create" else ""})
    return {"from": task.get("assigner_name") or "your Admin", "title": first[:60] or "A task",
            "description": text, "due": task.get("final_deadline_at"), "signs": signs,
            "started": bool(task.get("started_at"))}
