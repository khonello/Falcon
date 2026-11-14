"""The Engine as a Windows service (the user, 14 Nov 2026: deployment is Windows; Linux keeps its systemd unit, installers/engine/).

    python -m engine service install   [--name FalconEngine] --env <falcon.env>   register it (starts with Windows, restarts itself if it fails)
    python -m engine service uninstall [--name FalconEngine]                      stop and remove it
    python -m engine service start|stop|status [--name FalconEngine]
    python -m engine service run       [--name ...] --env <falcon.env>            what Windows runs (not for typing)

The service runs as the system account, reads every setting from the one file it is given (`FALCON_ENV_FILE`: with absolute paths, so the
working folder Windows gives a service never matters), and logs to a `logs` folder beside it. Nothing here is imported on Linux: the
service-control code (common/winsvc.py) is loaded only when a service command is given, on Windows.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

log = logging.getLogger("engine.service")

DEFAULT_NAME = "FalconEngine"
DESCRIPTION = "The Falcon Engine: the server every Falcon machine and console connects to (its database, audit trail and keys)."


def log_dir(env_file: str | None) -> Path:
    return (Path(env_file).resolve().parent if env_file else Path.cwd()) / "logs"


def command_line(name: str, env_file: str) -> str:
    """What Windows runs: this interpreter, this module, the settings file."""
    return subprocess.list2cmdline([sys.executable, "-m", "engine", "service", "run", "--name", name, "--env", str(Path(env_file).resolve())])


def _logging(env_file: str | None) -> None:
    from logging.handlers import RotatingFileHandler

    folder = log_dir(env_file)
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "engine.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def _serve(stop_flag: threading.Event) -> None:
    from engine.config import Settings
    from engine.server import Engine

    async def serve() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        def watch() -> None:
            stop_flag.wait()
            loop.call_soon_threadsafe(stop.set)

        threading.Thread(target=watch, daemon=True).start()
        engine = Engine(Settings.from_env())
        await engine.start()
        try:
            await stop.wait()
        finally:
            await engine.stop()
        log.info("the Engine stopped")

    asyncio.run(serve())


def main(argv: list[str]) -> int:
    if sys.platform != "win32":
        print("the Engine's Windows service is for Windows; on Linux the Engine runs under systemd (installers/engine)", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser(prog="python -m engine service")
    ap.add_argument("action", choices=("install", "uninstall", "start", "stop", "status", "run"))
    ap.add_argument("--name", default=DEFAULT_NAME)
    ap.add_argument("--env", help="the settings file (falcon.env) the service reads")
    args = ap.parse_args(argv)
    from common import winsvc

    try:
        if args.action == "run":
            if args.env:
                os.environ["FALCON_ENV_FILE"] = str(Path(args.env).resolve())
                from common import dotenv

                dotenv.load(Path(args.env))
            _logging(args.env)
            return winsvc.ServiceRunner(args.name, _serve, what="the Engine service").run()
        if args.action == "install":
            if not args.env:
                print("install needs --env <falcon.env>: the service reads every setting from it", file=sys.stderr)
                return 2
            print(winsvc.install(args.name, "Falcon Engine", DESCRIPTION, command_line(args.name, args.env)))
            return 0
        if args.action == "status":
            print(f"{args.name}: {winsvc.state(args.name)}")
            return 0
        print({"uninstall": lambda: winsvc.uninstall(args.name), "start": lambda: winsvc.start(args.name, str(log_dir(args.env) / "engine.log"), 60),
               "stop": lambda: winsvc.stop(args.name, 60)}[args.action]())
        return 0
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
