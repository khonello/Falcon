"""Periodic reporting the Engine cannot observe on its own.

  * control.metrics {cpu, memory, idle_s}          -- for polled Events (thresholds, idle)
  * task.program_signal {task_id, item_id, ...}     -- Expectation evidence for Program targets:
    running, active (CPU in the last interval), rss_bytes, open_files, present (installed)

Program presence: a name is "present" if a matching executable is on PATH or a matching process
has been seen -- a cheap, honest proxy; the assigner's manual verification remains the only
completion path.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Awaitable, Callable
from typing import Any

from worker_client import idle

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _psutil() -> Any:
    try:
        import psutil
    except ImportError:
        return None
    return psutil


def _matches(proc_name: str, program: str) -> bool:
    a, b = proc_name.lower().removesuffix(".exe"), program.lower().removesuffix(".exe")
    return a == b or a.startswith(b) or b in a


def snapshot_program(program: str) -> dict[str, Any]:
    """Evidence for one program name from the current process table."""
    ps = _psutil()
    out: dict[str, Any] = {"running": False, "active": False, "rss_bytes": 0, "open_files": [],
                           "present": bool(shutil.which(program) or shutil.which(program + ".exe"))}
    if ps is None:
        return out
    for p in ps.process_iter(["name", "memory_info", "cpu_percent"]):
        try:
            if not _matches(p.info["name"] or "", program):
                continue
            out["running"] = True
            out["present"] = True
            out["rss_bytes"] += int(p.info["memory_info"].rss) if p.info.get("memory_info") else 0
            if (p.info.get("cpu_percent") or p.cpu_percent(interval=None)) > 0.5:
                out["active"] = True
            try:
                out["open_files"].extend(f.path for f in p.open_files()[:50])
            except (ps.AccessDenied, ps.NoSuchProcess, OSError):
                pass
        except (ps.NoSuchProcess, ps.AccessDenied):
            continue
    return out


class Signals:
    def __init__(self, report: Reporter, *, metrics_seconds: float = 15.0, program_seconds: float = 20.0) -> None:
        self.report = report
        self.metrics_seconds = metrics_seconds
        self.program_seconds = program_seconds
        self._tasks: list[asyncio.Task[None]] = []
        self.watch_programs: dict[tuple[int, int], str] = {}  # (task_id, item_id) -> program name

    async def start(self) -> None:
        self._tasks = [asyncio.create_task(self._metrics_loop()), asyncio.create_task(self._program_loop())]

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def refresh_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """From task.list: which Program items to keep reporting on."""
        self.watch_programs = {}
        for t in tasks:
            if t.get("verification_mode") != "stack" or t.get("status") == "completed":
                continue
            for item in t.get("items", []):
                if item.get("target_type") == "program" and item.get("program_name"):
                    self.watch_programs[(t["id"], item["id"])] = item["program_name"]

    async def report_metrics(self) -> None:
        ps = _psutil()
        cpu = ps.cpu_percent(interval=None) if ps else 0.0
        mem = ps.virtual_memory().percent if ps else 0.0
        await self.report("control.metrics", {"cpu": cpu, "memory": mem, "idle_s": idle.idle_seconds() or 0.0})

    async def report_programs(self) -> int:
        n = 0
        for (task_id, item_id), program in list(self.watch_programs.items()):
            evidence = await asyncio.to_thread(snapshot_program, program)
            try:
                await self.report("task.program_signal", {"task_id": task_id, "item_id": item_id, **evidence})
                n += 1
            except Exception as exc:  # noqa: BLE001
                log.debug("program signal for task %s failed: %s", task_id, exc)
        return n

    async def _metrics_loop(self) -> None:
        while True:
            try:
                await self.report_metrics()
            except Exception as exc:  # noqa: BLE001
                log.debug("metrics report failed: %s", exc)
            await asyncio.sleep(self.metrics_seconds)

    async def _program_loop(self) -> None:
        while True:
            await asyncio.sleep(self.program_seconds)
            await self.report_programs()
