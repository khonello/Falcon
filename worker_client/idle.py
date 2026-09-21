"""User-idle detection: the "notice when idle, act then, back off the moment the user resumes"
pattern used by the index sweep and update retries (spec 6.2, 9.4).

Windows: GetLastInputInfo (no dependencies). Elsewhere: no reliable session-wide signal
without X11/Wayland hooks, so `idle_seconds()` returns None and callers treat the machine as
never idle unless FALCON_WORKER_ASSUME_IDLE is set (tests/dev).
"""

from __future__ import annotations

import ctypes
import os
import sys


def idle_seconds() -> float | None:
    forced = os.environ.get("FALCON_WORKER_ASSUME_IDLE")
    if forced:
        try:
            return float(forced)
        except ValueError:
            return None
    if sys.platform != "win32":
        return None
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
            return None
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime  # type: ignore[attr-defined]
        return max(0.0, millis / 1000.0)
    except (AttributeError, OSError):
        return None


def is_idle(threshold_seconds: float) -> bool:
    idle = idle_seconds()
    return idle is not None and idle >= threshold_seconds
