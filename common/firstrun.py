"""First run, on either side: what the console and the Worker share when a machine is not set up (reading an address, keeping a
certificate, saying what went wrong in words). Since 15 Nov 2026 nothing joins from a first run: a machine is set up only by its setup
(docs/SEATS-AND-SETUP.md). Stdlib only.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import socket
import ssl
import uuid
from pathlib import Path

from common.connection import ConnectionError_, EngineError

DEFAULT_PORT = 7400
UNKNOWN_HOST = ("", "127.0.0.1")      # what a machine holds before anyone has told it where its Engine is
REACH_SECONDS = 20.0


def parse_address(text: str) -> tuple[str, int]:
    """'192.168.1.20' or 'falcon.internal:7400'. Raises ValueError with what to fix."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Type the Engine's address.")
    host, colon, port = text.rpartition(":")
    if not colon:
        return text, DEFAULT_PORT
    if not host or not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError("That address does not look right. It is an IP address or a name, like 192.168.1.20.")
    return host, int(port)


def plain_reason(exc: BaseException, address: str) -> str:
    """What went wrong, in words the person at the machine can act on."""
    cause = exc.__cause__ if exc.__cause__ is not None and not isinstance(exc, (EngineError, ValueError)) else exc
    if isinstance(cause, EngineError):
        message = cause.message or "The Engine refused."
        return message[0].upper() + message[1:].rstrip(".") + "."
    if isinstance(cause, ssl.SSLError):
        return "The Engine's certificate does not match the one on this machine."
    if isinstance(cause, (OSError, asyncio.TimeoutError, ConnectionError_)):
        return f"Could not reach the Engine at {address}. Check the address, and that the Engine is running."
    text = str(cause).strip()
    return (text[0].upper() + text[1:].rstrip(".") + ".") if text else "It could not be set up."


def keep_certificate(source: str, folder: Path) -> str:
    """The Engine's certificate beside this machine's settings, where it stays when the file it came from goes."""
    path = Path(str(source).strip().removeprefix("file:///"))
    if not path.is_file():
        raise ValueError("That certificate file could not be found.")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    kept = folder / "engine.crt"
    if path.resolve() != kept.resolve():
        shutil.copyfile(path, kept)
    return str(kept)


def about_this_machine() -> dict[str, str]:
    node = uuid.getnode()
    return {"hostname": socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
            "mac": ":".join(f"{(node >> s) & 0xFF:02x}" for s in range(40, -1, -8))}


