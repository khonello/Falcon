"""Entry point: `python -m worker_client [--engine host:port] [--client-id ID] [--plaintext]
[--watch DIR ...] [--ui] [--allow-power] [--no-native-watch]`

Runs the headless service; `--ui` also opens the narrow Worker TUI in the same process.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from worker_client.config import WorkerConfig
from worker_client.service import WorkerService


async def _main(cfg: WorkerConfig, *, ui: bool, native: bool, allow_power: bool) -> None:
    service = WorkerService(cfg, native_watch=native, allow_power=allow_power)
    stop = asyncio.Event()
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
    except (NotImplementedError, AttributeError):
        pass  # Windows: Ctrl+C raises KeyboardInterrupt instead
    await service.start()
    try:
        if ui:
            from worker_client.ui import run_ui

            await run_ui(service)
        else:
            await stop.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await service.stop()


def main() -> None:
    ap = argparse.ArgumentParser(prog="worker_client", description="Falcon Worker Client")
    ap.add_argument("--engine", help="host:port of the Engine (remembered)")
    ap.add_argument("--client-id", help="this PC's provisioned client id (remembered)")
    ap.add_argument("--client-key", help="this PC's provisioned client key, hex (remembered)")
    ap.add_argument("--plaintext", action="store_true", help="no TLS (development only)")
    ap.add_argument("--ca", help="pinned Engine certificate (PEM)")
    ap.add_argument("--config", help="config file path (default: %PROGRAMDATA%/Falcon/worker.json)")
    ap.add_argument("--watch", action="append", help="directory to watch (repeatable; remembered)")
    ap.add_argument("--ui", action="store_true", help="also run the narrow Worker TUI")
    ap.add_argument("--allow-power", action="store_true", help="allow shutdown/reboot/lock_session actions")
    ap.add_argument("--no-native-watch", action="store_true", help="force the polling watcher")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    cfg = WorkerConfig.load(Path(args.config) if args.config else None)
    if args.engine:
        host, _, port = args.engine.partition(":")
        cfg.engine_host = host or cfg.engine_host
        if port:
            cfg.engine_port = int(port)
    if args.client_id:
        cfg.client_id = args.client_id
    if args.client_key:
        cfg.client_key = args.client_key
    if args.plaintext:
        cfg.tls = False
    if args.ca:
        cfg.ca_cert = args.ca
    if args.watch:
        cfg.watch_roots = args.watch
    if not cfg.client_id:
        sys.exit("no client id: pass --client-id once (it is remembered)")
    cfg.save()
    try:
        asyncio.run(_main(cfg, ui=args.ui, native=not args.no_native_watch, allow_power=args.allow_power))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
