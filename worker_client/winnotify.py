"""Windows tells us when something changed -- so the Worker looks at once instead of every few seconds.

Two native sources, both stdlib ctypes, both only a *nudge*: the watcher compares its snapshots when nudged
(ossignals.OsSignals.nudge), so a missed notification costs at most one polling interval and never a wrong signal.

  * A hidden message-only window on its own thread. Windows sends it WM_DEVICECHANGE when a drive or a volume
    arrives or leaves (drives), and WM_WTSSESSION_CHANGE when someone signs in, out, locks or unlocks
    (sessions).
  * NotifyIpInterfaceChange (iphlpapi), a callback when a network interface changes state (network).

Not available off Windows, or when Windows refuses; `start()` then returns False and the caller keeps polling.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)

Nudge = Callable[[str], None]            # called from a Windows thread with "drives", "sessions" or "network"

WM_DEVICECHANGE = 0x0219
WM_WTSSESSION_CHANGE = 0x02B1
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVNODES_CHANGED = 0x0007
NOTIFY_FOR_ALL_SESSIONS = 1
HWND_MESSAGE = -3


class WindowsNotifier:
    """Starts the hidden window and the network callback; `stop()` closes both."""

    def __init__(self, nudge: Nudge) -> None:
        self.nudge = nudge
        self._thread: threading.Thread | None = None
        self._hwnd = 0
        self._ready = threading.Event()
        self._ok = False
        self._net_handle = None
        self._net_callback = None            # kept alive for as long as Windows may call it

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        self._thread = threading.Thread(target=self._window_thread, name="falcon-winnotify", daemon=True)
        self._thread.start()
        self._ready.wait(5)
        net = self._start_network()
        return self._ok or net

    def stop(self) -> None:
        if sys.platform != "win32":
            return
        import ctypes

        if self._net_handle is not None:
            ctypes.windll.iphlpapi.CancelMibChangeNotify2(self._net_handle)
            self._net_handle = None
        if self._hwnd:
            ctypes.windll.user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(3)

    # --- the hidden window -------------------------------------------------------------------------

    def _window_thread(self) -> None:
        import ctypes
        from ctypes import wintypes

        user32, kernel32, wtsapi = ctypes.windll.user32, ctypes.windll.kernel32, ctypes.windll.wtsapi32
        lresult = ctypes.c_ssize_t
        proc_type = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = lresult

        def on_message(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_DEVICECHANGE and wparam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE, DBT_DEVNODES_CHANGED):
                    self.nudge("drives")
                elif msg == WM_WTSSESSION_CHANGE:
                    self.nudge("sessions")
                elif msg == WM_CLOSE:
                    user32.DestroyWindow(hwnd)
                    return 0
                elif msg == WM_DESTROY:
                    user32.PostQuitMessage(0)
                    return 0
            except Exception:      # never let an exception cross back into Windows
                log.exception("window message %s failed", msg)
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        callback = proc_type(on_message)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", proc_type), ("cbClsExtra", ctypes.c_int),
                        ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HANDLE),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        name = "FalconNotify"
        cls = WNDCLASS()
        cls.lpfnWndProc = callback
        cls.hInstance = kernel32.GetModuleHandleW(None)
        cls.lpszClassName = name
        user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
        if not user32.RegisterClassW(ctypes.byref(cls)):
            log.warning("native notifications: could not register the window class")
            self._ready.set()
            return
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                           wintypes.HANDLE, wintypes.HINSTANCE, wintypes.LPVOID]
        hwnd = user32.CreateWindowExW(0, name, name, 0, 0, 0, 0, 0, HWND_MESSAGE, None, cls.hInstance, None)
        if not hwnd:
            log.warning("native notifications: could not create the window")
            self._ready.set()
            return
        self._hwnd = hwnd
        wtsapi.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_ALL_SESSIONS)
        self._ok = True
        self._ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        wtsapi.WTSUnRegisterSessionNotification(hwnd)
        self._hwnd = 0

    # --- the network callback ----------------------------------------------------------------------

    def _start_network(self) -> bool:
        import ctypes
        from ctypes import wintypes

        cb_type = ctypes.WINFUNCTYPE(None, wintypes.LPVOID, wintypes.LPVOID, ctypes.c_int)

        def changed(_ctx, _row, _kind):
            self.nudge("network")

        self._net_callback = cb_type(changed)
        handle = wintypes.HANDLE()
        # AF_UNSPEC (0), no context, notify at once = False
        rc = ctypes.windll.iphlpapi.NotifyIpInterfaceChange(0, self._net_callback, None, False, ctypes.byref(handle))
        if rc != 0:
            log.warning("native notifications: the network callback was refused (code %s)", rc)
            self._net_callback = None
            return False
        self._net_handle = handle
        return True
