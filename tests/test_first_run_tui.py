"""The first-run dialogs, run as a terminal runs them: real keys into prompt_toolkit's own dialogs. Since 15 Nov 2026 nothing joins from a
first run (docs/SEATS-AND-SETUP.md): the console and the Worker's `--ui` say how the machine is set up, and wait for the person's Enter."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest

pytest.importorskip("prompt_toolkit")
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output.plain_text import PlainTextOutput

from operator_client.core.config import LocalConfig
from worker_client.config import WorkerConfig

ENTER = "\r"


async def _run(ask, cfg) -> tuple[object, str]:
    screen = io.StringIO()
    with create_pipe_input() as inp, create_app_session(input=inp, output=PlainTextOutput(screen)):
        async def press() -> None:
            await asyncio.sleep(0.6)                              # drawn and listening
            inp.send_text(ENTER)

        typing = asyncio.create_task(press())
        result = await asyncio.wait_for(ask(cfg), 30)
        await typing
    return result, screen.getvalue()


async def test_the_console_tui_says_to_run_the_admin_setup(tmp_path: Path):
    from operator_client.tui.app import _ask_setup

    cfg = LocalConfig(client_id="", tls=False, path=tmp_path / "operator.json")
    joined, screen = await _run(_ask_setup, cfg)
    assert joined is False and not cfg.client_id and not cfg.path.exists()
    assert "Set up Falcon" in screen and "Admin setup" in " ".join(screen.split())


async def test_the_worker_tui_says_to_run_the_worker_setup(tmp_path: Path):
    from worker_client.firstrun import ask_in_tui

    cfg = WorkerConfig(client_id="", tls=False, windows=False, path=tmp_path / "worker.json")
    _, screen = await _run(ask_in_tui, cfg)
    assert not cfg.client_id and "Worker setup" in " ".join(screen.split())
