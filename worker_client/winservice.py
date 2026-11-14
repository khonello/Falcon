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
import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("worker_client.service")

DEFAULT_NAME = "FalconWorker"


def data_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Falcon"


def command_line(name: str, config: str | None, probe: bool = False) -> str:
    """What Windows runs for the service: this interpreter, this module, the same settings."""
    argv = [sys.executable, "-m", "worker_client", "service", "run", "--name", name]
    if config:
        argv += ["--config", str(Path(config).resolve())]
    if probe:
        argv.append("--probe")
    return subprocess.list2cmdline(argv)


def install(name: str, config: str | None, probe: bool = False) -> str:
    from common import winsvc

    return winsvc.install(name, "Falcon Worker", "Falcon's agent on this machine: reports to the Falcon Engine and carries out what it is asked.",
                          command_line(name, config, probe))


def start(name: str) -> str:
    from common import winsvc

    return winsvc.start(name, str(data_dir() / "worker.log"))


def stop(name: str) -> str:
    from common import winsvc

    return winsvc.stop(name)


def uninstall(name: str) -> str:
    from common import winsvc

    return winsvc.uninstall(name)


def _state(name: str) -> str:
    from common import winsvc

    return winsvc.state(name)


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


REGISTER_AGAIN_SECONDS = 600.0
UNREACHABLE_AGAIN = (5.0, 15.0, 30.0, 60.0, 120.0)        # the Engine not answering yet (off, or the network not up): asked again soon, then every 2 minutes


async def _wait_to_be_registered(cfg: Any, stop_event: asyncio.Event) -> None:
    """A machine installed with no key of its own: ask the Engine to register it (it waits on probation, shows a code in the
    person's session, and an Admin confirms), then carry on with the key it is handed. A refused or expired
    request is asked again after a while: the service never gives up and never registers itself."""
    from worker_client.enroll import EnrollmentEnded, enroll
    from worker_client.windows.spawn import open_window

    async def show(spec: dict[str, Any]) -> Any:
        return await open_window("message", {**spec, "from": ""})

    from worker_client.firstrun import FirstRun, needs_setup

    if needs_setup(cfg) and cfg.windows:
        await FirstRun(cfg).run(stop_event)         # nobody has said where the Engine is: the Falcon program asks
    tries = 0
    while not cfg.client_id and not stop_event.is_set():
        task = asyncio.create_task(enroll(cfg, department_id=cfg.enroll_department, level=cfg.enroll_level,
                                          show=lambda m: log.info("%s", m), window=show if cfg.windows else None))
        stopped = asyncio.create_task(stop_event.wait())
        await asyncio.wait({task, stopped}, return_when=asyncio.FIRST_COMPLETED)
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            return
        stopped.cancel()
        wait = 0.0
        try:
            task.result()
            tries = 0
        except EnrollmentEnded as exc:
            log.warning("not registered: %s; asking again in %.0f minutes", exc, REGISTER_AGAIN_SECONDS / 60)
            wait = REGISTER_AGAIN_SECONDS
        except (OSError, ConnectionError, asyncio.TimeoutError) as exc:
            # The Engine cannot be reached yet. This used to end the service, and after three restarts Windows stopped starting it: a PC
            # installed while the Engine was off stayed off it until someone restarted the PC (found installing setup.exe, 14 Nov 2026).
            wait = UNREACHABLE_AGAIN[min(tries, len(UNREACHABLE_AGAIN) - 1)]
            tries += 1
            log.warning("the Engine at %s:%s does not answer (%s); asking again in %.0f s", cfg.engine_host, cfg.engine_port, exc, wait)
        if wait:
            try:
                await asyncio.wait_for(stop_event.wait(), wait)
            except asyncio.TimeoutError:
                pass


async def _run_worker(config: str | None, stop_event: asyncio.Event) -> None:
    from worker_client.config import WorkerConfig
    from worker_client.service import WorkerService

    cfg = WorkerConfig.load(Path(config) if config else None)
    if not cfg.client_id:
        await _wait_to_be_registered(cfg, stop_event)
        if not cfg.client_id:
            return                                  # stopped while waiting
    cfg.separate_programs = True            # as a service the indexer and the event tracker are their own supervised programs
    svc = WorkerService(cfg, native_watch=True, allow_power=False)
    await svc.start()
    try:
        await stop_event.wait()
    finally:
        await svc.stop()


class _Run:
    """What Windows runs: the shared service runner (common/winsvc.py) around the Worker, or around the probe."""

    def __init__(self, name: str, config: str | None, probe_only: bool) -> None:
        self.name, self.config, self.probe_only = name, config, probe_only

    def _main(self, stop_flag: threading.Event) -> None:
        if self.probe_only:
            data_dir().mkdir(parents=True, exist_ok=True)
            (data_dir() / "service-probe.json").write_text(json.dumps(probe(), indent=2), encoding="utf-8")
            stop_flag.wait()
            return

        async def worker() -> None:
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()

            def watch() -> None:
                stop_flag.wait()
                loop.call_soon_threadsafe(stop.set)

            threading.Thread(target=watch, daemon=True).start()
            await _run_worker(self.config, stop)

        asyncio.run(worker())

    def run(self) -> int:
        from common import winsvc

        return winsvc.ServiceRunner(self.name, self._main, what="the Worker service").run()


def log_dir(config: str | None = None) -> Path:
    """The log sits beside the settings (an installed machine keeps both in a folder only the system and administrators can read)."""
    return Path(config).resolve().parent if config else data_dir()


def _logging(config: str | None = None) -> None:
    from logging.handlers import RotatingFileHandler

    folder = log_dir(config)
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "worker.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
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
            _logging(args.config)
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
