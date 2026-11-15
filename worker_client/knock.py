"""Knocking: an installed PC tells its Engine it is here, until an Admin gives it a seat (docs/SEATS-AND-SETUP.md section 6, step 3).

    await knock(cfg, stop_event)    -> True once seated (its client id and key are saved in its settings), False if stopped first

The machine says who it is (its install token, name, Windows version, network card, hardware identity, who is signed in) and is told
"waiting", nothing more: knocking reaches nothing else on the Engine. It asks again after 5, 15, 30, 60 and 120 seconds, then every 2
minutes, for as long as it takes; the Engine nudges it on its open connection the moment it is given a seat. No code is shown or typed.

The install token is made once, the first time the machine knocks, and kept in its private settings: it is how one installed PC stays one
row on the Engine. A reinstall makes a new one.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import secrets
import socket
from typing import Any

from common.connection import ConnectionError_, EngineConnection, EngineError
from common.machine import hardware_id, mac
from worker_client.config import WorkerConfig

log = logging.getLogger(__name__)

LADDER = (5.0, 15.0, 30.0, 60.0, 120.0)             # then every 2 minutes


def facts(cfg: WorkerConfig) -> dict[str, Any]:
    from worker_client.privacy import signed_in_user

    return {"install_token": install_token(cfg), "hostname": socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
            "mac": mac(), "hardware_id": hardware_id(), "user": signed_in_user()}


def install_token(cfg: WorkerConfig) -> str:
    if not cfg.install_token:
        cfg.install_token = secrets.token_urlsafe(32)
        cfg.save()
    return cfg.install_token


async def knock(cfg: WorkerConfig, stop_event: asyncio.Event, *, ladder: tuple[float, ...] = LADDER) -> bool:
    """Knock until seated (True) or stopped (False)."""
    tries = 0
    while not stop_event.is_set():
        seated = asyncio.Event()
        conn = EngineConnection(cfg.engine_host, cfg.engine_port, client_id="", tls=cfg.tls, ca_cert=cfg.ca_cert)

        async def on_push(type_: str, payload: dict[str, Any], seated: asyncio.Event = seated) -> None:
            if type_ == "knock.seated":
                seated.set()

        conn.on_push(on_push)
        try:
            await conn.open()
            while not stop_event.is_set():
                got = await conn.call("knock.hello", {**facts(cfg), **_claim(cfg)})
                if got.get("status") == "seated":
                    cfg.client_id, cfg.client_key = str(got["client_id"]), str(got["client_key"])
                    _spend_claim(cfg)
                    cfg.save()
                    log.info("given a seat: this machine is pc %s", got.get("pc_id"))
                    return True
                if got.get("status") == "collected":
                    log.warning("this machine's key was handed over already, and this machine does not have it: an Admin takes its seat back "
                                "and gives it again")
                wait = ladder[min(tries, len(ladder) - 1)]
                tries += 1
                if tries == 1:
                    log.info("waiting for a seat from an Admin (knocking at %s)", cfg.engine_address)
                if await _wait(stop_event, seated, wait):
                    continue                                     # nudged: knock now, and collect the key
        except (OSError, ConnectionError_, EngineError, asyncio.TimeoutError) as exc:
            wait = ladder[min(tries, len(ladder) - 1)]
            tries += 1
            log.warning("could not knock at %s (%s); again in %.0f s", cfg.engine_address, exc, wait)
            await _wait(stop_event, None, wait)
        finally:
            await conn.close()
    return False


def _claim(cfg: WorkerConfig) -> dict[str, Any]:
    """An Admin's PC knocks with the claim the Admin setup wrote (docs/SEATS-AND-SETUP.md section 5): the Engine checks it and lets it in."""
    if not cfg.admin_claim:
        return {}
    try:
        with open(cfg.admin_claim, encoding="utf-8") as f:
            return {"admin_claim": json.load(f)}
    except (OSError, ValueError) as exc:
        log.warning("the Admin claim %s cannot be read (%s): run the Admin setup again", cfg.admin_claim, exc)
        return {}


def _spend_claim(cfg: WorkerConfig) -> None:
    """A claim works once: once in, it is of no use, so it is not kept."""
    if cfg.admin_claim:
        try:
            os.remove(cfg.admin_claim)
        except OSError:
            pass
        cfg.admin_claim = ""


async def _wait(stop_event: asyncio.Event, seated: asyncio.Event | None, seconds: float) -> bool:
    """Wait `seconds`, or less if stopped or nudged. True when nudged."""
    waiters = [asyncio.ensure_future(stop_event.wait())]
    if seated is not None:
        waiters.append(asyncio.ensure_future(seated.wait()))
    _done, pending = await asyncio.wait(waiters, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
    for w in pending:
        w.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    return seated is not None and seated.is_set()
