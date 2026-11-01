"""Entry point: `python -m operator_client [--engine host:port] [--client-id ID] [--plaintext]
[--script "cmd; cmd"] [--gui]`. Without --script, starts the interactive TUI (or the QML GUI with --gui)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from operator_client.core.config import LocalConfig


def main() -> None:
    ap = argparse.ArgumentParser(prog="operator_client", description="Falcon Operator Client")
    ap.add_argument("--engine", help="host:port of the Engine (remembered)")
    ap.add_argument("--client-id", help="this client's provisioned id (remembered)")
    ap.add_argument("--client-key", help="this client's provisioned key, hex (remembered)")
    ap.add_argument("--plaintext", action="store_true", help="no TLS (development only)")
    ap.add_argument("--ca", help="pinned Engine certificate (PEM)")
    ap.add_argument("--config", help="config file path (default: per-user app config)")
    ap.add_argument("--connect", action="store_true", help="connect immediately with the remembered settings")
    ap.add_argument("--script", help="run these ';'-separated commands and exit (no TUI)")
    ap.add_argument("--gui", action="store_true", help="start the QML GUI instead of the TUI")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    from pathlib import Path

    cfg = LocalConfig.load(Path(args.config) if args.config else None)
    connect_args = []
    if args.engine:
        connect_args.append(args.engine)
    if args.client_id:
        connect_args.append(f"client={args.client_id}")
    if args.client_key:
        connect_args.append(f"key={args.client_key}")
    if args.plaintext:
        connect_args.append("plaintext")
    if args.ca:
        connect_args.append(f"ca={args.ca}")
    initial: list[str] = []
    if args.connect or args.engine or args.client_id or args.script:
        initial.append("connect " + " ".join(connect_args))

    if args.gui:
        if args.engine:
            host, _, port = args.engine.rpartition(":")
            cfg.engine_host, cfg.engine_port = (host or args.engine), int(port) if port.isdigit() else cfg.engine_port
        if args.client_id:
            cfg.client_id = args.client_id
        if args.client_key:
            cfg.client_key = args.client_key
        if args.plaintext:
            cfg.tls = False
        if args.ca:
            cfg.ca_cert = args.ca
        try:
            from operator_client.gui.app import run as run_gui
        except ImportError:
            sys.exit("PySide6/qasync are not installed: pip install -e '.[gui]'  (environ-operator)")
        run_gui(cfg, auto_connect=bool(initial))
        return

    if args.script:
        from operator_client.tui.shell import run_script

        lines = initial + [s.strip() for s in args.script.split(";") if s.strip()]
        for out in asyncio.run(run_script(cfg, lines)):
            if out:
                print(out)
        return

    try:
        from operator_client.tui.app import run_app
    except ImportError:
        sys.exit("prompt_toolkit is not installed: pip install -e '.[tui]'  (environ-operator)")
    asyncio.run(run_app(cfg, initial=initial))


if __name__ == "__main__":
    main()
