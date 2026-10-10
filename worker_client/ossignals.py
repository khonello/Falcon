"""Machine-state signals the Worker relays to the Engine (`control.signal`): a drive arriving or leaving,
the network coming up or going down, a program starting or stopping, a person signing in or out.

Only what an automation on this machine waits for is watched: the Engine says which signal types
matter (and their match blocks) through `control.signal_interest`, asked on connect and again on every
`control.interest_changed` push. Nothing is sent for a type no automation wants.

Each signal is the difference between two snapshots taken a few seconds apart. The first snapshot after
a type becomes wanted is only a baseline, so turning an automation on never reports what was already
there.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

INTERVAL_SECONDS = 3.0
WATCHED = ("usb.inserted", "usb.removed", "network.connected", "network.disconnected",
           "program.launched", "program.exited", "user.login", "user.logout")


def _psutil() -> Any:
    try:
        import psutil
    except ImportError:
        return None
    return psutil


def drives() -> dict[str, str]:
    """Removable drives now: mount point -> device."""
    ps = _psutil()
    if ps is None:
        return {}
    out = {}
    for part in ps.disk_partitions(all=False):
        if "removable" in part.opts.lower():
            out[part.mountpoint] = part.device
    return out


def interfaces() -> dict[str, bool]:
    """Network interfaces now: name -> up (loopback left out)."""
    ps = _psutil()
    if ps is None:
        return {}
    return {name: bool(st.isup) for name, st in ps.net_if_stats().items() if "loopback" not in name.lower()}


def programs() -> dict[int, str]:
    """Running processes now: pid -> executable name."""
    ps = _psutil()
    if ps is None:
        return {}
    out = {}
    for p in ps.process_iter(["name"]):
        if p.info.get("name"):
            out[p.pid] = p.info["name"]
    return out


def sessions() -> dict[str, str]:
    """People signed in now: session key (user@terminal) -> user name."""
    ps = _psutil()
    if ps is None:
        return {}
    return {f"{u.name}@{u.terminal or 'console'}": u.name for u in ps.users()}


def diff_sessions(before: dict[str, str], after: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    return ([("user.login", {"user": after[k]}) for k in sorted(set(after) - set(before))]
            + [("user.logout", {"user": before[k]}) for k in sorted(set(before) - set(after))])


def diff_drives(before: dict[str, str], after: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    return ([("usb.inserted", {"device": k, "path": k}) for k in sorted(set(after) - set(before))]
            + [("usb.removed", {"device": k, "path": k}) for k in sorted(set(before) - set(after))])


def diff_interfaces(before: dict[str, bool], after: dict[str, bool]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for name in sorted(set(before) | set(after)):
        was, now = before.get(name, False), after.get(name, False)
        if now and not was:
            out.append(("network.connected", {"interface": name}))
        elif was and not now:
            out.append(("network.disconnected", {"interface": name}))
    return out


def diff_programs(before: dict[int, str], after: dict[int, str]) -> list[tuple[str, dict[str, Any]]]:
    return ([("program.launched", {"process": after[p]}) for p in sorted(set(after) - set(before))]
            + [("program.exited", {"process": before[p]}) for p in sorted(set(before) - set(after))])


class OsSignals:
    """Watches the signal types the Engine said matter here and relays each change."""

    def __init__(self, report: Reporter, *, interval: float = INTERVAL_SECONDS) -> None:
        self.report = report
        self.interval = interval
        self.interest: dict[str, list[dict[str, Any]]] = {}
        self._base: dict[str, Any] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def refresh(self) -> None:
        """Ask the Engine what matters on this machine (on connect, and when told it changed)."""
        res = await self.report("control.signal_interest", {})
        self.set_interest(res.get("interest") or {})

    def set_interest(self, interest: dict[str, list[dict[str, Any]]]) -> None:
        self.interest = interest
        # A group that is no longer wanted forgets its baseline, so wanting it again starts clean.
        for group, types in self._groups().items():
            if not any(t in interest for t in types):
                self._base.pop(group, None)

    @staticmethod
    def _groups() -> dict[str, tuple[str, ...]]:
        return {"drives": ("usb.inserted", "usb.removed"),
                "network": ("network.connected", "network.disconnected"),
                "programs": ("program.launched", "program.exited"),
                "sessions": ("user.login", "user.logout")}

    def wanted(self, etype: str, data: dict[str, Any]) -> bool:
        """Some automation here waits for this signal. A program match is applied here, by the same rule
        the Engine uses (the process name, ignoring case), so nothing is sent that would only be dropped."""
        for match in self.interest.get(etype, []):
            proc = match.get("process")
            if proc is None or str(data.get("process", "")).lower() == str(proc).lower():
                return True
        return False

    async def tick(self) -> int:
        """One comparison pass; returns how many signals were sent."""
        readers = {"drives": (drives, diff_drives), "network": (interfaces, diff_interfaces),
                   "programs": (programs, diff_programs), "sessions": (sessions, diff_sessions)}
        sent = 0
        for group, types in self._groups().items():
            if not any(t in self.interest for t in types):
                continue
            read, diff = readers[group]
            now = await asyncio.to_thread(read)
            before = self._base.get(group)
            self._base[group] = now
            if before is None:
                continue                                  # the first look is only a baseline
            for etype, data in diff(before, now):
                if not self.wanted(etype, data):
                    continue
                try:
                    await self.report("control.signal", {"type": etype, "data": data})
                    sent += 1
                except Exception as exc:  # noqa: BLE001
                    log.warning("could not relay %s: %s", etype, exc)
        return sent

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001
                log.warning("signal pass failed: %s", exc)
