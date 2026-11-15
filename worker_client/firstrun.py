"""The Worker's first run, when nobody has told this machine where its Engine is.

Since 15 Nov 2026 (docs/SEATS-AND-SETUP.md) a machine is told only by the Worker setup, run with the store-signed company file beside it:
an address and a certificate typed or picked here would be a way in that nothing checks. So the Falcon program's setup modal is answered
with what to do instead (`join` says it), and nothing joins from here. `FirstRun` is what the service is meanwhile: it answers the program,
and does nothing else. `ask_in_tui` says the same for `--ui`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from common.firstrun import DEFAULT_PORT, UNKNOWN_HOST
from worker_client.config import WorkerConfig
from worker_client.localapp import LocalApp

log = logging.getLogger(__name__)

PROGRAM_AGAIN_SECONDS = 30.0
SET_UP_BY_THE_SETUP = "This machine is set up by the Worker setup, run with your company's file beside it (one zip, from the Machines page of your IT Admin's console). Ask your IT Admin for it."


def needs_setup(cfg: WorkerConfig) -> bool:
    """Nobody has told this machine where its Engine is: no settings yet, and still the built-in address. An install that did say
    goes on to ask the Engine by itself, even one pointed at an Engine on this same machine."""
    told = cfg.path.exists() or cfg.engine_host not in UNKNOWN_HOST or cfg.engine_port != DEFAULT_PORT
    return not cfg.client_id and not told


def needs_certificate(cfg: WorkerConfig) -> bool:
    return cfg.tls and not cfg.ca_cert


async def join(cfg: WorkerConfig, address: str, code: str, cert: str, window: Any = None) -> str:
    """What the setup modal is told: nothing joins from here (see the module's text)."""
    return SET_UP_BY_THE_SETUP


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
    """`--ui`: the person is told, in the middle of the terminal, how this machine is set up. Nothing joins from here."""
    from prompt_toolkit.shortcuts import message_dialog

    await message_dialog(title="Set up Falcon", text=SET_UP_BY_THE_SETUP).run_async()
