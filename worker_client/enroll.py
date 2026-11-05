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
RESHOW_SECONDS = 30.0


def loop_time() -> float:
    return asyncio.get_running_loop().time()


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

    `window` is an optional async function `({text, host, expires_at}) -> handle` that puts the code on this person's screen (a Worker window);
    its handle's `close()` is called when the request is decided, and its answer `{cancel: true}` takes the request back. Raises EnrollmentEnded when it was not confirmed."""
    conn = EngineConnection(cfg.engine_host, cfg.engine_port, client_id="", tls=cfg.tls, ca_cert=cfg.ca_cert)
    await conn.open()
    decided = asyncio.Event()
    cancelled = asyncio.Event()
    watching: list[asyncio.Future[None]] = []

    async def hear(shown: Any) -> None:
        answer = await shown.answer()
        if answer and answer.get("cancel"):
            cancelled.set()
            decided.set()

    async def on_push(type_: str, payload: dict[str, Any]) -> None:
        if type_ == "enroll.decided":
            decided.set()

    conn.on_push(on_push)
    handle = None
    try:
        request = {"hostname": hostname or socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
                   "mac": _mac(), "department_id": department_id, "level": level}
        if getattr(cfg, "enroll_code", ""):
            request["licence_code"] = cfg.enroll_code           # the licence code given at setup: the machine joins at once, nobody confirms
        asked = await conn.call("enroll.request", request)
        licensed = asked.get("status") == "confirmed"
        message = "Joining with the licence code." if licensed else f"Registering this machine. Code {spaced(asked['code'])}"
        show(message)
        if not licensed:
            show("Ask your Admin to confirm it, and give them this code. Waiting...")
        spec = {"text": message + "\n\nGive this code to whoever is registering you, and wait.", "host": request["hostname"], "expires_at": asked.get("expires_at")}
        if window is not None and not licensed:
            handle = await window(spec)
            if handle is not None:
                watching.append(asyncio.ensure_future(hear(handle)))
        if licensed:
            decided.set()                                        # already in: collect the key at once
        shown_at = loop_time()
        while True:
            if window is not None and not licensed and handle is None and loop_time() - shown_at >= RESHOW_SECONDS:
                handle = await window(spec)                    # nobody was signed in to see it the first time
                shown_at = loop_time()
                if handle is not None:
                    watching.append(asyncio.ensure_future(hear(handle)))
            try:
                await asyncio.wait_for(decided.wait(), poll)       # the Engine nudges; polling covers a missed nudge
            except asyncio.TimeoutError:
                pass
            decided.clear()
            if cancelled.is_set():
                await conn.call("enroll.cancel", {"token": asked["token"]})
                raise EnrollmentEnded("the request was cancelled on this machine")
            got = await conn.call("enroll.wait", {"token": asked["token"]})
            status = got["status"]
            if status == "pending":
                continue
            if status == "confirmed":
                cfg.client_id, cfg.client_key = got["client_id"], got["client_key"]
                if getattr(cfg, "enroll_code", ""):
                    cfg.enroll_code = ""                         # used: it is the licence's, not this machine's, and is not kept here
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
        for w in watching:
            w.cancel()
        if handle is not None:
            handle.close()
        await conn.close()
