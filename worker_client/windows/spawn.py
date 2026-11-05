"""Opening a Worker window from the service: its own process, never blocking the loop (spec: the helper exes are
spawned with `asyncio.create_subprocess_exec`). A window that stays (blocked, locked) is closed by the service; one
that asks something hands back the person's answer."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from typing import Any

from worker_client import winsession
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


async def _launch(argv: list[str]) -> Any:
    """Start a window program where the person can see it: on their desktop when the Worker is a service (session 0 has no screen), plainly otherwise."""
    if winsession.in_service_session():
        return await asyncio.get_running_loop().run_in_executor(None, winsession.spawn_in_user_session, argv)
    return await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)


async def open_window(kind: str, spec: dict[str, Any]) -> WindowHandle | None:
    """Show one window; None when this machine has no window support (the headless install), said once."""
    global _warned
    if not available():
        if not _warned:
            log.warning("the Worker's windows need the worker-ui extra (PySide6); running without them")
            _warned = True
        return None
    proc = await _launch([sys.executable, "-m", "worker_client.windows", kind, json.dumps(spec)])
    return WindowHandle(proc) if proc is not None else None


async def open_program() -> WindowHandle | None:
    """Start the person's Falcon program (tray icon, and a window on demand); None on a headless install. One copy runs per person: a second start
    only asks the first to come forward and exits."""
    if not available():
        return None
    proc = await _launch([sys.executable, "-m", "worker_client.program", "--background"])
    return WindowHandle(proc) if proc is not None else None


def first_sentence(text: str) -> str:
    """A task's first sentence, for its title: a dot only ends one before a space or the end, or "Update sales.xlsx" would read "Update sales"."""
    return re.split(r"\.(?:\s|$)", text, maxsplit=1)[0].strip()


def signs_of(task: dict[str, Any]) -> list[dict[str, Any]]:
    """The signs that will show the work, and whether each has been seen."""
    signs = []
    for item in task.get("items") or []:
        path = item.get("file_path") or item.get("proposed_path") or ""
        name = item.get("program_name") or item.get("proposed_filename") or path.replace("\\", "/").rsplit("/", 1)[-1] or "a file"
        seen = item.get("seen_at")                                   # when the Engine last saw a sign of it (its expectations)
        signs.append({"name": name, "program": item.get("target_type") == "program", "seen": seen,
                      "hint": "save it anywhere; it is found by name" if item.get("intent") == "create" else ""})
    return signs


def task_spec(task: dict[str, Any]) -> dict[str, Any]:
    """A task as the assignee reads it (TK07): what, when it is due, and the signs that will show the work."""
    text = str(task.get("description_raw") or "")
    first = first_sentence(text)
    return {"from": task.get("assigner_name") or "your Admin", "title": first[:60] or "A task",
            "description": text, "due": task.get("final_deadline_at"), "signs": signs_of(task),
            "started": bool(task.get("started_at"))}
