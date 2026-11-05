"""The Worker's first run: not set up yet, so the person is asked for the Engine's address and a licence code.

The asking is a modal in the Falcon program's own window. The program runs as the person and may not write the Worker's settings,
and only talks to the service over `localapp.py`, so until this machine has its id the service answers there through `FirstRun`:
the view says `setup`, and `app_setup` hands the answer to `enroll()`, the one way a machine joins. With no licence code it joins
as it always has, with a code on its screen for an IT Admin to type. `ask_in_tui` is the same thing for `--ui`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from common.firstrun import (
    DEFAULT_PORT,
    UNKNOWN_HOST,
    keep_certificate,
    parse_address,
    plain_reason,
)
from worker_client.config import WorkerConfig
from worker_client.enroll import enroll
from worker_client.localapp import LocalApp

log = logging.getLogger(__name__)

PROGRAM_AGAIN_SECONDS = 30.0


def needs_setup(cfg: WorkerConfig) -> bool:
    """Nobody has told this machine where its Engine is: no settings yet, and still the built-in address. An install that did say
    goes on to ask the Engine by itself, even one pointed at an Engine on this same machine."""
    told = cfg.path.exists() or cfg.enroll_code or cfg.engine_host not in UNKNOWN_HOST or cfg.engine_port != DEFAULT_PORT
    return not cfg.client_id and not told


def needs_certificate(cfg: WorkerConfig) -> bool:
    return cfg.tls and not cfg.ca_cert


async def join(cfg: WorkerConfig, address: str, code: str, cert: str, window: Any = None) -> str:
    """Join with what the person gave. Answers what went wrong, or "" when this machine is set up."""
    try:
        host, port = parse_address(address)
        if cert.strip():
            cfg.ca_cert = keep_certificate(cert, cfg.path.parent)
        if needs_certificate(cfg):
            raise ValueError("Choose the Engine's certificate.")
        cfg.engine_host, cfg.engine_port, cfg.enroll_code = host, port, code.strip()
        await enroll(cfg, department_id=cfg.enroll_department, level=cfg.enroll_level, show=lambda m: log.info("%s", m), window=window)
    except Exception as exc:  # noqa: BLE001 -- everything here ends as words on the modal
        cfg.enroll_code = ""
        return plain_reason(exc, address.strip())
    return ""


class FirstRun:
    """What the service is until this machine has joined: it answers the program, and does nothing else."""

    def __init__(self, cfg: WorkerConfig) -> None:
        self.cfg = cfg
        self.busy = False
        self.error = ""
        self._task: asyncio.Task[None] | None = None

    async def run(self, stop: asyncio.Event) -> None:
        app = LocalApp(self, self.cfg.path)
        await app.start()
        program, asked_at = None, None
        loop = asyncio.get_running_loop()
        try:
            while not self.cfg.client_id and not stop.is_set():
                if program is None and (asked_at is None or loop.time() - asked_at >= PROGRAM_AGAIN_SECONDS):
                    program, asked_at = await self._open_program(), loop.time()   # none yet: nobody is signed in
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(stop.wait(), 1.0)
        finally:
            if self._task is not None and not self._task.done():
                self._task.cancel()
                await asyncio.gather(self._task, return_exceptions=True)
            await app.stop()

    @staticmethod
    async def _open_program() -> Any:
        from worker_client.windows.spawn import open_program

        return await open_program()

    async def app_view(self) -> dict[str, Any]:
        cfg = self.cfg
        return {"setup": {"address": "" if cfg.engine_host in UNKNOWN_HOST else cfg.engine_address, "needs_cert": needs_certificate(cfg),
                          "busy": self.busy, "error": self.error},
                "connected": False, "tasks": [], "closed": [], "announcements": [], "messages": [], "admins": [], "machine": {}, "toasts": []}

    async def app_setup(self, address: str, code: str, cert: str) -> None:
        if not self.busy:
            self.busy, self.error = True, ""
            self._task = asyncio.create_task(self._join(address, code, cert))

    async def _join(self, address: str, code: str, cert: str) -> None:
        from worker_client.windows.spawn import open_window

        async def show(spec: dict[str, Any]) -> Any:
            return await open_window("message", {**spec, "from": ""})

        self.error = await join(self.cfg, address, code, cert, window=show if self.cfg.windows else None)
        self.busy = False

    async def _not_yet(self, *_: Any) -> Any:
        raise RuntimeError("this machine is not set up yet")

    app_start_task = app_ack = app_talk = app_conversation = app_reply = app_send_file = app_save_file = _not_yet


async def ask_in_tui(cfg: WorkerConfig) -> None:
    """`--ui`: the same questions as dialogs in the middle of the terminal. Cancel leaves it not set up."""
    from prompt_toolkit.shortcuts import input_dialog, message_dialog

    error = ""
    while not cfg.client_id:
        if error:
            await message_dialog(title="Set up Falcon", text=error).run_async()
        address = await input_dialog(title="Set up Falcon", text="The Engine's IP address").run_async()
        if address is None:
            return
        code = await input_dialog(title="Set up Falcon", text="The licence code. Leave it empty to have an IT Admin let it in instead.").run_async()
        if code is None:
            return
        cert = ""
        if needs_certificate(cfg):
            cert = await input_dialog(title="Set up Falcon", text="Where the Engine's certificate is on this machine (engine.crt)").run_async()
            if cert is None:
                return
        error = await join(cfg, address, code, cert)
