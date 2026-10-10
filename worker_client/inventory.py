"""What runs and what is installed on this machine, reported to the Engine (`control.inventory`) so a console can
pick a program ("open on 5 machines") instead of typing its name (ENGINE-GAPS #5).

  * running()    the process table grouped by program name: {name, count, memory}
  * installed()  Windows' own program lists, read from the registry (winreg, stdlib): the Uninstall keys (what shows in
                 Settings -> Apps) and App Paths (what Windows can start by name). Each entry is {name, command};
                 `command` is the program to run, or None when only the name is known.

The service reports what runs on connect and every minute, and what is installed on connect and every six hours.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

RUNNING_SECONDS = 60.0
INSTALLED_SECONDS = 6 * 3600.0


def running() -> list[dict[str, Any]]:
    try:
        import psutil
    except ImportError:
        return []
    groups: dict[str, dict[str, Any]] = {}
    for p in psutil.process_iter(["name", "memory_info"]):
        name = p.info.get("name")
        if not name:
            continue
        g = groups.setdefault(name.lower(), {"name": name, "count": 0, "memory": 0})
        g["count"] += 1
        if p.info.get("memory_info"):
            g["memory"] += int(p.info["memory_info"].rss)
    return sorted(groups.values(), key=lambda g: (-g["memory"], g["name"].lower()))


def _exe_path(value: str) -> str | None:
    """A program path out of a registry value such as '"C:\\App\\app.exe",0' or 'C:\\App\\app.exe /arg'."""
    text = os.path.expandvars(value.strip())
    if text.startswith('"'):
        text = text[1:].split('"', 1)[0]
    else:
        lower = text.lower()
        end = lower.find(".exe")
        text = text[:end + 4] if end != -1 else text
    text = text.split(",", 1)[0] if text.lower().endswith(("exe,0", "exe,1")) else text
    return text if text.lower().endswith(".exe") else None


def installed() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return []
    import winreg

    found: dict[str, dict[str, Any]] = {}

    def add(name: str, command: str | None) -> None:
        key = name.lower()
        if key not in found or (command and not found[key]["command"]):
            found[key] = {"name": name, "command": command}

    uninstall = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    app_paths = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
    views = [(winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY), (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
             (winreg.HKEY_CURRENT_USER, 0)]
    for hive, view in views:
        try:
            root = winreg.OpenKey(hive, uninstall, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                try:
                    with winreg.OpenKey(root, winreg.EnumKey(root, i)) as k:
                        name = winreg.QueryValueEx(k, "DisplayName")[0]
                        hidden = _has(k, "SystemComponent") and winreg.QueryValueEx(k, "SystemComponent")[0] == 1
                        if not name or hidden:                  # a component of something else, not a program
                            continue
                        command = None
                        if _has(k, "DisplayIcon"):
                            command = _exe_path(str(winreg.QueryValueEx(k, "DisplayIcon")[0]))
                        add(str(name), command)
                except OSError:
                    continue
    for hive, view in views[:2]:
        try:
            root = winreg.OpenKey(hive, app_paths, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                try:
                    exe = winreg.EnumKey(root, i)
                    with winreg.OpenKey(root, exe) as k:
                        path = str(winreg.QueryValueEx(k, "")[0]).strip('"')
                        add(os.path.splitext(exe)[0], path or exe)
                except OSError:
                    continue
    return sorted(found.values(), key=lambda p: p["name"].lower())


def _has(key: object, value: str) -> bool:
    import winreg

    try:
        winreg.QueryValueEx(key, value)
        return True
    except OSError:
        return False


class Inventory:
    def __init__(self, report: Reporter, *, running_seconds: float = RUNNING_SECONDS,
                 installed_seconds: float = INSTALLED_SECONDS) -> None:
        self.report = report
        self.running_seconds = running_seconds
        self.installed_seconds = installed_seconds
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        self._tasks = [asyncio.create_task(self._every(self.running_seconds, "running", running)),
                       asyncio.create_task(self._every(self.installed_seconds, "installed", installed))]

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def send(self, what: str, read: Callable[[], list[dict[str, Any]]]) -> None:
        await self.report("control.inventory", {what: await asyncio.to_thread(read)})

    async def _every(self, seconds: float, what: str, read: Callable[[], list[dict[str, Any]]]) -> None:
        while True:
            try:
                await self.send(what, read)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 -- a failed report is tried again next time
                log.debug("inventory (%s) not reported: %s", what, exc)
            await asyncio.sleep(seconds)
