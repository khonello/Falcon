"""First run: ask the Engine to register this machine, instead of typing its name and copying a key (ENGINE-GAPS #15).

    python -m worker_client --engine host:port --ca engine.crt --enroll [--department ID] [--level worker|admin]

The machine asks (`enroll.request`, before it has any key), shows a short code on its own screen, and waits. Whoever
confirms the request in an Operator Client types that code -- so a machine that is not really in front of someone cannot
finish. On confirmation the Engine hands this machine its client id and key, once; they are written into the Worker's
config and the Worker carries on as an ordinary one. Nothing registers itself: a refused or expired request ends here.

The Engine's certificate is pinned from `--ca` (the install package carries it), exactly as for a registered machine.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import socket
import uuid
from collections.abc import Callable
from typing import Any

from common.connection import ConnectionError_, EngineConnection, EngineError
from worker_client.config import WorkerConfig

log = logging.getLogger(__name__)

POLL_SECONDS = 3.0


class EnrollmentEnded(RuntimeError):
    """The request was refused, expired, or its key had already been collected."""


def spaced(code: str) -> str:
    """'4729' -> '4 7 2 9': easier to read across a desk."""
    return " ".join(code)


def _mac() -> str:
    n = uuid.getnode()
    return ":".join(f"{(n >> s) & 0xFF:02x}" for s in range(40, -1, -8))


async def enroll(cfg: WorkerConfig, *, department_id: int | None = None, level: str = "worker",
                 show: Callable[[str], None] = print, poll: float = POLL_SECONDS, window: Any = None,
                 hostname: str | None = None) -> dict[str, Any]:
    """Ask, show the code, wait for the answer, store the key. Returns what the Engine handed over.

    `window` is an optional async function `(text) -> handle` that puts the code on this person's screen (a Worker window);
    its handle's `close()` is called when the request is decided. Raises EnrollmentEnded when it was not confirmed."""
    conn = EngineConnection(cfg.engine_host, cfg.engine_port, client_id="", tls=cfg.tls, ca_cert=cfg.ca_cert)
    await conn.open()
    decided = asyncio.Event()

    async def on_push(type_: str, payload: dict[str, Any]) -> None:
        if type_ == "enroll.decided":
            decided.set()

    conn.on_push(on_push)
    handle = None
    try:
        asked = await conn.call("enroll.request", {
            "hostname": hostname or socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
            "mac": _mac(), "department_id": department_id, "level": level})
        message = f"Registering this machine. Code {spaced(asked['code'])}"
        show(message)
        show("Ask your Admin to confirm it, and give them this code. Waiting...")
        if window is not None:
            handle = await window(message + "\n\nGive this code to whoever is registering you, and wait.")
        while True:
            try:
                await asyncio.wait_for(decided.wait(), poll)       # the Engine nudges; polling covers a missed nudge
            except asyncio.TimeoutError:
                pass
            decided.clear()
            got = await conn.call("enroll.wait", {"token": asked["token"]})
            status = got["status"]
            if status == "pending":
                continue
            if status == "confirmed":
                cfg.client_id, cfg.client_key = got["client_id"], got["client_key"]
                cfg.save()
                show("Registered. This machine is set up; starting as a Worker.")
                return got
            reason = {"refused": "the request was refused" + (f" ({got.get('reason')})" if got.get("reason") else ""),
                      "expired": "the request expired before anyone confirmed it",
                      "collected": "the key for this request was already collected; ask an Admin to issue a new one"}.get(status, status)
            raise EnrollmentEnded(reason)
    except (EngineError, ConnectionError_) as exc:
        raise EnrollmentEnded(f"could not ask the Engine: {exc}") from exc
    finally:
        if handle is not None:
            handle.close()
        await conn.close()
