"""A Windows service, with nothing but the standard library and Windows' own service API (ctypes): the part the Worker's and the Engine's services share.

    install(name, display, description, command_line)    register it: starts with Windows, restarts itself after 5 s, 30 s, then every minute
    start(name) / stop(name) / uninstall(name) / state(name)
    ServiceRunner(name, main).run()                       what the service's own process calls: tells Windows it is running, and turns Windows'
                                                          Stop (and shutdown) into `main`'s stop event

Moved here from worker_client/winservice.py (14 Nov 2026) when the Engine became a Windows service too. Import it only on Windows.
"""

from __future__ import annotations

import ctypes
import logging
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

log = logging.getLogger(__name__)

SERVICE_OWN_PROCESS, AUTO_START, ERROR_NORMAL = 0x10, 2, 1
STOPPED, START_PENDING, STOP_PENDING, RUNNING = 1, 2, 3, 4
ACCEPT_STOP, ACCEPT_SHUTDOWN = 0x1, 0x4
CONTROL_STOP, CONTROL_SHUTDOWN, CONTROL_INTERROGATE = 1, 5, 4
ALL_ACCESS, SC_MANAGER_ALL = 0xF01FF, 0xF003F
STATES = {1: "stopped", 2: "starting", 3: "stopping", 4: "running", 5: "continuing", 6: "pausing", 7: "paused"}


class Status(ctypes.Structure):
    _fields_ = [("dwServiceType", wintypes.DWORD), ("dwCurrentState", wintypes.DWORD), ("dwControlsAccepted", wintypes.DWORD),
                ("dwWin32ExitCode", wintypes.DWORD), ("dwServiceSpecificExitCode", wintypes.DWORD), ("dwCheckPoint", wintypes.DWORD),
                ("dwWaitHint", wintypes.DWORD)]


def advapi() -> Any:
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    for fn in (adv.OpenSCManagerW, adv.OpenServiceW, adv.CreateServiceW, adv.RegisterServiceCtrlHandlerExW):
        fn.restype = ctypes.c_void_p
    return adv


class Manager:
    def __init__(self) -> None:
        self.adv = advapi()
        self.scm = self.adv.OpenSCManagerW(None, None, SC_MANAGER_ALL)
        if not self.scm:
            raise OSError(f"could not open the service manager ({ctypes.get_last_error()}); run this from an elevated prompt")

    def close(self) -> None:
        self.adv.CloseServiceHandle(ctypes.c_void_p(self.scm))

    def exists(self, name: str) -> bool:
        h = self.open(name, 0x4)
        if h:
            self.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return bool(h)

    def open(self, name: str, access: int = ALL_ACCESS) -> int | None:
        h = self.adv.OpenServiceW(ctypes.c_void_p(self.scm), name, access)
        return h or None

    def state(self, name: str) -> str:
        h = self.open(name, 0x4)
        if not h:
            return "not installed"
        st = Status()
        self.adv.QueryServiceStatus(ctypes.c_void_p(h), ctypes.byref(st))
        self.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return STATES.get(st.dwCurrentState, str(st.dwCurrentState))


def install(name: str, display: str, description: str, command_line: str) -> str:
    m = Manager()
    try:
        adv = m.adv
        if m.exists(name):
            return f"{name} is already installed"
        adv.CreateServiceW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR]
        h = adv.CreateServiceW(ctypes.c_void_p(m.scm), name, display, ALL_ACCESS, SERVICE_OWN_PROCESS, AUTO_START, ERROR_NORMAL,
                               command_line, None, None, None, None, None)
        if not h:
            raise OSError(f"could not create the service ({ctypes.get_last_error()})")

        class Desc(ctypes.Structure):
            _fields_ = [("lpDescription", wintypes.LPWSTR)]

        class Action(ctypes.Structure):
            _fields_ = [("Type", wintypes.DWORD), ("Delay", wintypes.DWORD)]

        class Failure(ctypes.Structure):
            _fields_ = [("dwResetPeriod", wintypes.DWORD), ("lpRebootMsg", wintypes.LPWSTR), ("lpCommand", wintypes.LPWSTR), ("cActions", wintypes.DWORD),
                        ("lpsaActions", ctypes.POINTER(Action))]

        desc = Desc(description)
        adv.ChangeServiceConfig2W(ctypes.c_void_p(h), 1, ctypes.byref(desc))                       # SERVICE_CONFIG_DESCRIPTION
        actions = (Action * 3)(Action(1, 5000), Action(1, 30000), Action(1, 60000))                 # restart after 5 s, 30 s, then every minute
        failure = Failure(86400, None, None, 3, actions)
        adv.ChangeServiceConfig2W(ctypes.c_void_p(h), 2, ctypes.byref(failure))                    # SERVICE_CONFIG_FAILURE_ACTIONS
        adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} installed (starts with Windows, restarts itself if it stops unexpectedly)"
    finally:
        m.close()


def wait_state(m: Manager, name: str, want: str, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if m.state(name) == want:
            return True
        time.sleep(0.3)
    return m.state(name) == want


def start(name: str, log_hint: str = "", seconds: float = 20.0) -> str:
    m = Manager()
    try:
        h = m.open(name)
        if not h:
            return f"{name} is not installed"
        m.adv.StartServiceW(ctypes.c_void_p(h), 0, None)
        m.adv.CloseServiceHandle(ctypes.c_void_p(h))
        if wait_state(m, name, "running", seconds):
            return f"{name} {m.state(name)}"
        return f"{name} did not reach running ({m.state(name)})" + (f"; see {log_hint}" if log_hint else "")
    finally:
        m.close()


def stop(name: str, seconds: float = 30.0) -> str:
    m = Manager()
    try:
        h = m.open(name)
        if not h:
            return f"{name} is not installed"
        st = Status()
        m.adv.ControlService(ctypes.c_void_p(h), CONTROL_STOP, ctypes.byref(st))
        m.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} stopped" if wait_state(m, name, "stopped", seconds) else f"{name} is still {m.state(name)}"
    finally:
        m.close()


def uninstall(name: str) -> str:
    m = Manager()
    try:
        if not m.exists(name):
            return f"{name} is not installed"
    finally:
        m.close()
    if state(name) != "stopped":
        stop(name)
    m = Manager()
    try:
        h = m.open(name)
        ok = bool(h) and bool(m.adv.DeleteService(ctypes.c_void_p(h)))
        if h:
            m.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} removed" if ok else f"could not remove {name} ({ctypes.get_last_error()})"
    finally:
        m.close()


def state(name: str) -> str:
    m = Manager()
    try:
        return m.state(name)
    finally:
        m.close()


class ServiceRunner:
    """The service-control side: report status to Windows, and turn its Stop into `main`'s. `main(stop_flag)` runs on the service's thread and
    returns when the service should end (it is given a threading.Event that is set when Windows says stop)."""

    def __init__(self, name: str, main: Callable[[threading.Event], None], *, what: str = "the service") -> None:
        self.name, self.main, self.what = name, main, what
        self.adv = advapi()
        self.handle: int = 0
        self.status = Status(SERVICE_OWN_PROCESS, START_PENDING, 0, 0, 0, 0, 10000)
        self.stop_flag = threading.Event()
        self._handler_type = ctypes.WINFUNCTYPE(wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p)
        self._main_type = ctypes.WINFUNCTYPE(None, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR))
        self._handler = self._handler_type(self._on_control)
        self._main = self._main_type(self._service_main)

    def _report(self, st: int, exit_code: int = 0, hint: int = 0) -> None:
        self.status.dwCurrentState = st
        self.status.dwControlsAccepted = ACCEPT_STOP | ACCEPT_SHUTDOWN if st == RUNNING else 0
        self.status.dwWin32ExitCode = exit_code
        self.status.dwWaitHint = hint
        self.status.dwCheckPoint = 0 if st in (RUNNING, STOPPED) else self.status.dwCheckPoint + 1
        self.adv.SetServiceStatus(ctypes.c_void_p(self.handle), ctypes.byref(self.status))

    def _on_control(self, control: int, event_type: int, data: Any, context: Any) -> int:
        if control in (CONTROL_STOP, CONTROL_SHUTDOWN):
            self._report(STOP_PENDING, hint=20000)
            self.stop_flag.set()
        return 0

    def _service_main(self, argc: int, argv: Any) -> None:
        self.handle = self.adv.RegisterServiceCtrlHandlerExW(self.name, self._handler, None) or 0
        if not self.handle:
            return
        self._report(START_PENDING, hint=15000)
        code = 0
        try:
            self._report(RUNNING)
            self.main(self.stop_flag)
        except BaseException:
            log.exception("%s failed", self.what)
            code = 1
        finally:
            self._report(STOPPED, code)

    def run(self) -> int:
        name_buf = ctypes.create_unicode_buffer(self.name)
        # SERVICE_TABLE_ENTRYW {name, main}, then the NULL entry that ends the table
        table = (ctypes.c_void_p * 4)(ctypes.cast(name_buf, ctypes.c_void_p), ctypes.cast(self._main, ctypes.c_void_p), None, None)
        if not self.adv.StartServiceCtrlDispatcherW(table):
            log.error("not started by Windows' service manager (%s)", ctypes.get_last_error())
            return 1
        return 0
