"""First run, on either side: a machine that is not set up is given the Engine's address and a licence code, and joins.

The console and the Worker ask in their own way (`operator_client/core/firstrun.py`, `worker_client/firstrun.py`); what they
share is here: reading the address, keeping the certificate, and saying what went wrong so the person can act on it. The
Engine's certificate stays pinned: a machine with none is asked for it, never connected to unchecked, because the licence
code would go to whoever answered. Stdlib only.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import socket
import ssl
import uuid
from pathlib import Path
from typing import Any

from common.connection import ConnectionError_, EngineConnection, EngineError

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


async def join_with_licence(host: str, port: int, *, tls: bool, ca_cert: str | None, code: str, level: str) -> dict[str, Any]:
    """Join at once with a licence code; nobody confirms it. Answers {client_id, client_key}."""
    conn = EngineConnection(host, port, client_id="", tls=tls, ca_cert=ca_cert)
    await asyncio.wait_for(conn.open(), REACH_SECONDS)
    try:
        asked = await conn.call("enroll.request", {**about_this_machine(), "level": level, "licence_code": code})
        if asked.get("status") != "confirmed":
            raise ValueError("That licence code did not let this machine in.")
        return await conn.call("enroll.wait", {"token": asked["token"]})
    finally:
        await conn.close()
