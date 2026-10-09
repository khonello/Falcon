"""The program in front of the person and its window title (usually the document) -- stdlib only.

Reported with `control.metrics` so a console can show what a machine is doing (level 4). Windows
only; elsewhere, or when there is no foreground window (a locked screen, a service's own desktop),
it returns None. When the Worker runs as a Windows service this is read by its helper in the
person's session, since a service sees no foreground window.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def foreground() -> dict[str, Any] | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    title = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title, length + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    program = None
    handle = kernel32.OpenProcess(0x1000, False, pid.value)          # PROCESS_QUERY_LIMITED_INFORMATION
    if handle:
        try:
            size = wintypes.DWORD(1024)
            path = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                program = os.path.basename(path.value)
        finally:
            kernel32.CloseHandle(handle)
    if not program:
        return None
    return {"program": program, "title": title.value}


if __name__ == "__main__":
    print(foreground())
