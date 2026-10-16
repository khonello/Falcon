"""A new machine asking to become the Super User's (the other half of `handover.*`, engine/hierarchy/handover.py).

    python -m operator_client --handover-join [--engine host:port --ca engine.crt] [--config operator.json]

Run on the dedicated machine while the current Super User has opened a handover. It asks the Engine (before it has any key), shows a short code on
its own screen, and waits. The person at the CURRENT Super User console types that code to confirm; only then does the Engine hand this machine its
client id and key -- once, ever -- which are written into this machine's console settings. A refused, expired or never-answered request ends here and
changes nothing. No UI dependencies.
"""

from __future__ import annotations

import asyncio
import platform
import socket
from collections.abc import Callable
from typing import Any

from common.connection import ConnectionError_, EngineConnection, EngineError
from operator_client.core.config import LocalConfig

POLL_SECONDS = 3.0
GIVE_UP_AFTER = 11 * 60            # the Engine closes a handover after ten minutes; a little longer than that, then stop waiting


class HandoverEnded(RuntimeError):
    """The request was refused, expired, or its key had already been collected."""


def spaced(code: str) -> str:
    return " ".join(code)


async def join(cfg: LocalConfig, *, show: Callable[[str], None] = print, poll: float = POLL_SECONDS, hostname: str | None = None,
               give_up_after: float = GIVE_UP_AFTER) -> dict[str, Any]:
    conn = EngineConnection(cfg.engine_host, cfg.engine_port, client_id="", tls=cfg.tls, ca_cert=cfg.ca_cert)
    try:
        await conn.open()
        decided = asyncio.Event()

        async def on_push(type_: str, payload: dict[str, Any]) -> None:
            if type_ == "enroll.decided":
                decided.set()

        conn.on_push(on_push)
        asked = await conn.call("enroll.request", {"hostname": hostname or socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
                                                   "level": "super_user"})
        show(f"This machine is asking to become the Super User's. Code {spaced(asked['code'])}")
        show("At the Super User's current console, type:  handover confirm <id> <code>   (the id is in `handover`). Waiting...")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + give_up_after
        while loop.time() < deadline:
            try:
                await asyncio.wait_for(decided.wait(), poll)
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
                show("Done. This machine is now the Super User's console.")
                return got
            reason = {"refused": "the request was refused" + (f" ({got.get('reason')})" if got.get("reason") else ""),
                      "expired": "the request expired before it was confirmed",
                      "collected": "the key for this request was already collected"}.get(status, status)
            raise HandoverEnded(reason)
        raise HandoverEnded("nobody confirmed it in time; open the handover again and retry")
    except (EngineError, ConnectionError_, OSError) as exc:
        raise HandoverEnded(f"could not ask the Engine: {exc}") from exc
    finally:
        await conn.close()
