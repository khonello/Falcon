"""A picture put on the clipboard -- PrintScreen, the Snipping Tool, "copy image" -- seen from the person's desktop (stdlib only, Windows).

Detective weighs a screenshot taken while restricted files are in front of someone, and a person does not need a screenshot program for that: PrintScreen puts the
whole screen on the clipboard and Win+Shift+S puts a region there. So this looks at the clipboard itself, and only at its SHAPE: Windows numbers every change
(`GetClipboardSequenceNumber`), and when the number moves and the clipboard now holds a picture, its width and height are read from the picture's header. The pixels
are never read, and neither is any text on the clipboard.

    look()   -> {"seq": n, "image": {"w", "h"} | None, "screen": {"w", "h"}}   or None where there is no clipboard (not Windows, locked desktop)

It must run where the person's desktop is (the Worker's helper when the Worker is a service).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)

CF_DIB = 8
SCREEN_SHARE = 0.9              # a picture at least this much of the screen's width and height is "the screen"; smaller is a region or any picture
INTERVAL = 1.5
QUIET = 3.0                     # one picture is one signal, however many times Windows renumbers the clipboard for it

Source = Callable[[], Awaitable[dict[str, Any] | None]]


def look() -> dict[str, Any] | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    out: dict[str, Any] = {"seq": int(user32.GetClipboardSequenceNumber()), "image": None,
                           "screen": {"w": int(user32.GetSystemMetrics(0)), "h": int(user32.GetSystemMetrics(1))}}
    if out["seq"] == 0 or not user32.IsClipboardFormatAvailable(CF_DIB):
        return out                                          # (0 means this desktop cannot be asked)
    if not user32.OpenClipboard(None):
        return out                                          # someone else has it open this instant: the next look will do
    try:
        handle = user32.GetClipboardData(CF_DIB)
        if handle:
            ptr = kernel32.GlobalLock(handle)
            if ptr:
                try:
                    header = (ctypes.c_int32 * 3).from_address(ptr)          # biSize, biWidth, biHeight: the picture's shape, nothing of what it shows
                    out["image"] = {"w": abs(int(header[1])), "h": abs(int(header[2]))}
                finally:
                    kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
    return out


def kind_of(image: dict[str, int], screen: dict[str, int]) -> str:
    """"screen" for a picture of (nearly) the whole screen, "region" for a smaller one."""
    if screen.get("w") and screen.get("h") and image["w"] >= SCREEN_SHARE * screen["w"] and image["h"] >= SCREEN_SHARE * screen["h"]:
        return "screen"
    return "region"


class ClipboardWatcher:
    """Looks every moment or two and reports when a picture has just been put on the clipboard (`screen.captured`)."""

    def __init__(self, report: Callable[[str, dict[str, Any]], Awaitable[Any]], source: Source, *, front: Callable[[], Awaitable[str | None]] | None = None,
                 wanted: Callable[[], bool] = lambda: True, interval: float = INTERVAL, clock: Callable[[], float] = time.monotonic) -> None:
        self._report, self._source, self._front, self._wanted, self.interval, self._clock = report, source, front, wanted, interval, clock
        self._seq: int | None = None
        self._last_sent = -1e9
        self._task: asyncio.Task[None] | None = None

    async def poll(self) -> dict[str, Any] | None:
        """One look: the signal's data if a picture just arrived, else None. The first look is only a baseline."""
        got = await self._source()
        if not got or not got.get("seq"):
            return None
        before, self._seq = self._seq, got["seq"]
        image = got.get("image")
        if before is None or before == got["seq"] or not image:
            return None
        now = self._clock()
        if now - self._last_sent < QUIET:
            return None
        self._last_sent = now
        data: dict[str, Any] = {"kind": kind_of(image, got.get("screen") or {}), "w": image["w"], "h": image["h"]}
        if self._front is not None:
            try:
                program = await self._front()
            except Exception:  # noqa: BLE001 -- what was in front is a nicety
                program = None
            if program:
                data["process"] = str(program)[:120]
        return data

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            if not self._wanted():
                self._seq = None                               # nobody asked: forget the baseline, so asking again starts clean
                continue
            try:
                data = await self.poll()
                if data:
                    await self._report("control.signal", {"type": "screen.captured", "data": data})
            except Exception as exc:  # noqa: BLE001
                log.debug("clipboard look failed: %s", exc)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
