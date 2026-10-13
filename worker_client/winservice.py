"""The Worker as a Windows service -- the small, necessary part of packaging, with nothing but the standard library and Windows' own service API.

    python -m worker_client service install   [--name FalconWorker] [--config PATH]   register it (starts with Windows, restarts itself if it fails)
    python -m worker_client service uninstall [--name FalconWorker]                   stop and remove it
    python -m worker_client service start|stop|status [--name FalconWorker]
    python -m worker_client service run       [--name ...] [--config PATH] [--probe]  what Windows runs (not for typing)

Run once from an elevated prompt, `install` is the whole setup: the service runs as the system account, so the Worker can trace programs and file opens,
start its windows on the signed-in person's desktop (worker_client/winsession.py), and restart on its own. Nobody using the machine needs to be an administrator.

The service speaks the service-control protocol itself (`StartServiceCtrlDispatcherW`, `RegisterServiceCtrlHandlerExW`, `SetServiceStatus`) through ctypes, so no
extra library is bundled. Settings come from the Worker's usual file (`%PROGRAMDATA%\\Falcon\\worker.json`); its log is `%PROGRAMDATA%\\Falcon\\worker.log`.

`--probe` runs no Worker at all: it records what a service on this machine can do (who it runs as, which session, whether it may trace, whether it can start a
program on the person's desktop) in `%PROGRAMDATA%\\Falcon\\service-probe.json`, then waits to be stopped. It is how the service route is tested without an Engine.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

log = logging.getLogger("worker_client.service")

DEFAULT_NAME = "FalconWorker"
SERVICE_OWN_PROCESS, AUTO_START, ERROR_NORMAL = 0x10, 2, 1
STOPPED, START_PENDING, STOP_PENDING, RUNNING = 1, 2, 3, 4
ACCEPT_STOP, ACCEPT_SHUTDOWN = 0x1, 0x4
CONTROL_STOP, CONTROL_SHUTDOWN, CONTROL_INTERROGATE = 1, 5, 4
ALL_ACCESS, SC_MANAGER_ALL = 0xF01FF, 0xF003F
STATES = {1: "stopped", 2: "starting", 3: "stopping", 4: "running", 5: "continuing", 6: "pausing", 7: "paused"}


def data_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Falcon"


class _Status(ctypes.Structure):
    _fields_ = [("dwServiceType", wintypes.DWORD), ("dwCurrentState", wintypes.DWORD), ("dwControlsAccepted", wintypes.DWORD),
                ("dwWin32ExitCode", wintypes.DWORD), ("dwServiceSpecificExitCode", wintypes.DWORD), ("dwCheckPoint", wintypes.DWORD),
                ("dwWaitHint", wintypes.DWORD)]


def _adv() -> Any:
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    for fn in (adv.OpenSCManagerW, adv.OpenServiceW, adv.CreateServiceW, adv.RegisterServiceCtrlHandlerExW):
        fn.restype = ctypes.c_void_p
    return adv


# --- install / control -------------------------------------------------------------------------------------------------------


class _Manager:
    def __init__(self) -> None:
        self.adv = _adv()
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
        st = _Status()
        self.adv.QueryServiceStatus(ctypes.c_void_p(h), ctypes.byref(st))
        self.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return STATES.get(st.dwCurrentState, str(st.dwCurrentState))


def command_line(name: str, config: str | None, probe: bool = False) -> str:
    """What Windows runs for the service: this interpreter, this module, the same settings."""
    argv = [sys.executable, "-m", "worker_client", "service", "run", "--name", name]
    if config:
        argv += ["--config", str(Path(config).resolve())]
    if probe:
        argv.append("--probe")
    return subprocess.list2cmdline(argv)


def install(name: str, config: str | None, probe: bool = False) -> str:
    m = _Manager()
    try:
        adv = m.adv
        if m.exists(name):
            return f"{name} is already installed"
        adv.CreateServiceW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR]
        h = adv.CreateServiceW(ctypes.c_void_p(m.scm), name, "Falcon Worker", ALL_ACCESS, SERVICE_OWN_PROCESS, AUTO_START, ERROR_NORMAL,
                               command_line(name, config, probe), None, None, None, None, None)
        if not h:
            raise OSError(f"could not create the service ({ctypes.get_last_error()})")

        class Desc(ctypes.Structure):
            _fields_ = [("lpDescription", wintypes.LPWSTR)]

        class Action(ctypes.Structure):
            _fields_ = [("Type", wintypes.DWORD), ("Delay", wintypes.DWORD)]

        class Failure(ctypes.Structure):
            _fields_ = [("dwResetPeriod", wintypes.DWORD), ("lpRebootMsg", wintypes.LPWSTR), ("lpCommand", wintypes.LPWSTR), ("cActions", wintypes.DWORD),
                        ("lpsaActions", ctypes.POINTER(Action))]

        desc = Desc("Falcon's agent on this machine: reports to the Falcon Engine and carries out what it is asked.")
        adv.ChangeServiceConfig2W(ctypes.c_void_p(h), 1, ctypes.byref(desc))                       # SERVICE_CONFIG_DESCRIPTION
        actions = (Action * 3)(Action(1, 5000), Action(1, 30000), Action(1, 60000))                 # restart after 5 s, 30 s, then every minute
        failure = Failure(86400, None, None, 3, actions)
        adv.ChangeServiceConfig2W(ctypes.c_void_p(h), 2, ctypes.byref(failure))                    # SERVICE_CONFIG_FAILURE_ACTIONS
        adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} installed (starts with Windows, restarts itself if it stops unexpectedly)"
    finally:
        m.close()


def _wait_state(m: _Manager, name: str, want: str, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if m.state(name) == want:
            return True
        time.sleep(0.3)
    return m.state(name) == want


def start(name: str) -> str:
    m = _Manager()
    try:
        h = m.open(name)
        if not h:
            return f"{name} is not installed"
        m.adv.StartServiceW(ctypes.c_void_p(h), 0, None)
        m.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} {m.state(name)}" if _wait_state(m, name, "running", 20) else f"{name} did not reach running ({m.state(name)}); see {data_dir() / 'worker.log'}"
    finally:
        m.close()


def stop(name: str) -> str:
    m = _Manager()
    try:
        h = m.open(name)
        if not h:
            return f"{name} is not installed"
        st = _Status()
        m.adv.ControlService(ctypes.c_void_p(h), CONTROL_STOP, ctypes.byref(st))
        m.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} stopped" if _wait_state(m, name, "stopped", 30) else f"{name} is still {m.state(name)}"
    finally:
        m.close()


def uninstall(name: str) -> str:
    m = _Manager()
    try:
        if not m.exists(name):
            return f"{name} is not installed"
    finally:
        m.close()
    if _state(name) != "stopped":
        stop(name)
    m = _Manager()
    try:
        h = m.open(name)
        ok = bool(h) and bool(m.adv.DeleteService(ctypes.c_void_p(h)))
        if h:
            m.adv.CloseServiceHandle(ctypes.c_void_p(h))
        return f"{name} removed" if ok else f"could not remove {name} ({ctypes.get_last_error()})"
    finally:
        m.close()


def _state(name: str) -> str:
    m = _Manager()
    try:
        return m.state(name)
    finally:
        m.close()


# --- what Windows runs ------------------------------------------------------------------------------------------------------


def probe() -> dict[str, Any]:
    """What a service on this machine can do. Written for people to read and for the test to check."""
    from worker_client import winsession
    from worker_client.etw import EtwWatcher

    out: dict[str, Any] = {"user": os.environ.get("USERNAME", ""), "in_service_session": winsession.in_service_session(),
                           "console_session": winsession.active_session(), "pid": os.getpid()}
    watcher = EtwWatcher(lambda t, d: None)
    out["may_trace_programs"] = watcher.want_programs(True)
    out["may_trace_files"] = watcher.want_files([{"path_prefix": "C:/Users"}])
    out["trace_errors"] = watcher.errors
    watcher.stop()
    proc = winsession.spawn_in_user_session([sys.executable, "-c", "import os;print(os.environ.get('USERNAME'))"])
    if proc is None:
        out["desktop_program"] = None
    else:
        line = asyncio.run(proc.stdout.readline())
        out["desktop_program"] = line.decode(errors="replace").strip()
    return out


async def _run_worker(config: str | None, stop_event: asyncio.Event) -> None:
    from worker_client.config import WorkerConfig
    from worker_client.service import WorkerService

    cfg = WorkerConfig.load(Path(config) if config else None)
    if not cfg.client_id:
        raise SystemExit("the Worker has no client id yet: run `python -m worker_client --enroll` (or pass --client-id) once, then start the service")
    svc = WorkerService(cfg, native_watch=True, allow_power=False)
    await svc.start()
    try:
        await stop_event.wait()
    finally:
        await svc.stop()


class _Run:
    """The service-control side: report status to Windows, and turn its Stop into the Worker's."""

    def __init__(self, name: str, config: str | None, probe_only: bool) -> None:
        self.name, self.config, self.probe_only = name, config, probe_only
        self.adv = _adv()
        self.handle: int = 0
        self.status = _Status(SERVICE_OWN_PROCESS, START_PENDING, 0, 0, 0, 0, 10000)
        self.stop_flag = threading.Event()
        self._handler_type = ctypes.WINFUNCTYPE(wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p)
        self._main_type = ctypes.WINFUNCTYPE(None, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR))
        self._handler = self._handler_type(self._on_control)
        self._main = self._main_type(self._service_main)

    def _report(self, state: int, exit_code: int = 0, hint: int = 0) -> None:
        self.status.dwCurrentState = state
        self.status.dwControlsAccepted = ACCEPT_STOP | ACCEPT_SHUTDOWN if state == RUNNING else 0
        self.status.dwWin32ExitCode = exit_code
        self.status.dwWaitHint = hint
        self.status.dwCheckPoint = 0 if state in (RUNNING, STOPPED) else self.status.dwCheckPoint + 1
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
            if self.probe_only:
                data_dir().mkdir(parents=True, exist_ok=True)
                (data_dir() / "service-probe.json").write_text(json.dumps(probe(), indent=2), encoding="utf-8")
                self.stop_flag.wait()
            else:
                asyncio.run(self._worker())
        except BaseException:
            log.exception("the Worker service failed")
            code = 1
        finally:
            self._report(STOPPED, code)

    async def _worker(self) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        def watch() -> None:
            self.stop_flag.wait()
            loop.call_soon_threadsafe(stop.set)

        threading.Thread(target=watch, daemon=True).start()
        await _run_worker(self.config, stop)

    def run(self) -> int:
        name_buf = ctypes.create_unicode_buffer(self.name)
        # SERVICE_TABLE_ENTRYW {name, main}, then the NULL entry that ends the table
        table = (ctypes.c_void_p * 4)(ctypes.cast(name_buf, ctypes.c_void_p), ctypes.cast(self._main, ctypes.c_void_p), None, None)
        if not self.adv.StartServiceCtrlDispatcherW(table):
            log.error("not started by Windows' service manager (%s)", ctypes.get_last_error())
            return 1
        return 0


def _logging() -> None:
    from logging.handlers import RotatingFileHandler

    data_dir().mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(data_dir() / "worker.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def main(argv: list[str]) -> int:
    if sys.platform != "win32":
        print("the Worker service is for Windows", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser(prog="worker_client service")
    ap.add_argument("action", choices=("install", "uninstall", "start", "stop", "status", "run"))
    ap.add_argument("--name", default=DEFAULT_NAME)
    ap.add_argument("--config")
    ap.add_argument("--probe", action="store_true", help="record what a service here can do instead of running the Worker")
    args = ap.parse_args(argv)
    try:
        if args.action == "run":
            _logging()
            return _Run(args.name, args.config, args.probe).run()
        if args.action == "status":
            print(f"{args.name}: {_state(args.name)}")
            return 0
        print({"install": lambda: install(args.name, args.config, args.probe), "uninstall": lambda: uninstall(args.name),
               "start": lambda: start(args.name), "stop": lambda: stop(args.name)}[args.action]())
        return 0
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
