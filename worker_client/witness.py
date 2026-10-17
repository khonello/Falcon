"""What the machine saw when something happened to a file: was a person at the keyboard, and what were they looking at?

Detective weighs a change differently when a person's hands made it than when a program did it on its own, so each file event the Worker reports carries a
small stamp, taken at that moment:

    by      "hand"     input happened in the last two seconds: a person is doing this
            "started"  a person is about, input within the last half minute: a program they started is probably working
            "alone"    nobody has touched the machine for half a minute or more: a program (or a script, or a scheduled job) on its own
            "unknown"  it cannot be told (no desktop to ask, or not Windows)
    front   the program in front when it happened (only claimed for "hand": it is the program the person is using)
    title   that program's window title, as the person sees it (usually the document or the page): kept in the evidence of a finding, never in the event history
    program the program that last opened the file in the seconds before (Windows' own file trace, where this process may have one): it names who made the
            change, and a person who runs a script (powershell, robocopy, python ...) is "started", not "hand": their hands started it, a program did the work

It is a weight, never a verdict: a person who starts a script is "started" or "alone" depending on how long they then leave it.

A service lives in session 0 and sees no desktop: its input and foreground are not the person's. There the stamp comes from the helper on the person's desktop
(`worker_client/helper.py`, "witness"), and if there is none it says "unknown" rather than guess.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)

HAND_SECONDS = 2.0
ALONE_SECONDS = 30.0
TTL = 1.0                      # one look serves every event in the same second (a burst of fourteen copies is one look)

Source = Callable[[], Awaitable[tuple[Any, ...]]]          # (idle seconds, program in front[, its window title])
TITLE_MAX = 160
Toucher = Callable[[str], str]

# programs a person starts to make a machine do work for them: a change they make is by their hand only in the sense that they started it
SCRIPT_HOSTS = frozenset({"powershell.exe", "pwsh.exe", "cmd.exe", "python.exe", "pythonw.exe", "wscript.exe", "cscript.exe", "robocopy.exe", "xcopy.exe", "7z.exe",
                          "7zg.exe", "rclone.exe", "bash.exe", "wsl.exe", "node.exe"})


def classify(idle_s: float | None) -> str:
    if idle_s is None:
        return "unknown"
    if idle_s <= HAND_SECONDS:
        return "hand"
    return "started" if idle_s < ALONE_SECONDS else "alone"


async def here() -> tuple[float | None, str | None, str | None]:
    """Idle seconds, the program in front and its window title, as this process sees them (right for a process on the person's desktop)."""
    from worker_client import idle
    from worker_client.foreground import foreground

    def look() -> tuple[float | None, str | None, str | None]:
        try:
            front = foreground()
        except OSError:
            front = None
        return idle.idle_seconds(), (front or {}).get("program"), (front or {}).get("title")

    return await asyncio.to_thread(look)


class Witness:
    def __init__(self, source: Source | None = None, *, clock: Callable[[], float] = time.monotonic, toucher: Toucher | None = None) -> None:
        self._source = source or here
        self._clock = clock
        self._toucher = toucher
        self._last: tuple[float, dict[str, Any]] | None = None

    async def _look(self) -> dict[str, Any]:
        now = self._clock()
        if self._last is not None and now - self._last[0] < TTL:
            return self._last[1]
        try:
            got = await self._source()
            idle_s, front, title = (tuple(got) + (None, None))[:3]
        except Exception as exc:  # noqa: BLE001 -- a stamp that cannot be taken is "unknown", never a failed report
            log.debug("could not take a witness stamp: %s", exc)
            idle_s, front, title = None, None, None
        by = classify(idle_s)
        out: dict[str, Any] = {"by": by}
        if by == "hand" and front:
            out["front"] = str(front)[:120]
            if title:
                out["title"] = " ".join(str(title).split())[:TITLE_MAX]
        self._last = (now, out)
        return out

    async def stamp(self, path: str | None = None) -> dict[str, Any]:
        out = dict(await self._look())
        program = self._toucher(path) if (self._toucher and path) else ""
        if program:
            out["program"] = program[:120]
            if out["by"] == "hand" and program.lower() in SCRIPT_HOSTS:
                out["by"] = "started"                    # a person's hands started it; the program did the work
                out.pop("front", None)
                out.pop("title", None)
        return out
