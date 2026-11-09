"""The first-run dialogs, run as a terminal runs them: real keys typed into prompt_toolkit's own dialogs, against a real Engine.

The keys go in one at a time, as a person types them, and what the dialogs draw is captured as text, so a dialog that never
waits, asks the wrong thing or swallows an answer fails here.
"""

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
from tests.conftest import requires_db
from worker_client.config import WorkerConfig

pytestmark = [requires_db, pytest.mark.organisation]

LICENCE = {"name": "Falcon", "reference": "ORD-T",
           "codes": [{"code": "ADMN-TUIT-ESTS-1111", "role": "admin", "seats": 2}, {"code": "WRKR-TUIT-ESTS-2222", "role": "worker", "seats": 2}]}
ENTER = "\r"


async def _type(inp, answers: list[str]) -> None:
    """Each answer typed into its own dialog: the text, Enter to leave the box, Enter on OK."""
    for answer in answers:
        await asyncio.sleep(0.6)                                   # the next dialog is up and waiting
        for ch in answer:
            inp.send_text(ch)
            await asyncio.sleep(0.005)
        inp.send_text(ENTER)
        await asyncio.sleep(0.15)
        inp.send_text(ENTER)


async def _run(ask, cfg, answers: list[str]) -> tuple[object, str]:
    screen = io.StringIO()
    with create_pipe_input() as inp, create_app_session(input=inp, output=PlainTextOutput(screen)):
        typing = asyncio.create_task(_type(inp, answers))
        result = await asyncio.wait_for(ask(cfg), 60)
        await typing
    return result, screen.getvalue()


async def _licence(connect) -> None:
    a1 = await connect("cid-a1")
    await a1.ok("licence.import", LICENCE)


async def test_the_console_tui_asks_says_what_was_wrong_and_joins(engine, org, connect, tmp_path: Path):
    from operator_client.tui.app import _ask_setup

    await _licence(connect)
    cfg = LocalConfig(client_id="", tls=False, path=tmp_path / "operator.json")
    address = f"127.0.0.1:{engine.port}"
    # a wrong code first: told so, asked again; then the right one
    joined, screen = await _run(_ask_setup, cfg, [address, "NOPE-NOPE", "", address, "ADMN-TUIT-ESTS-1111"])
    assert joined is True and cfg.client_id and cfg.client_key
    assert "Set up Falcon" in screen and "The Engine's IP address" in screen and "The licence code" in screen
    assert "That is not a licence code this organisation has." in screen
    assert "certificate" not in screen                                                  # this Engine needs none: not asked


async def test_the_console_tui_left_with_cancel_stays_not_set_up(engine, tmp_path: Path):
    from operator_client.tui.app import _ask_setup

    cfg = LocalConfig(client_id="", tls=False, path=tmp_path / "operator.json")
    screen = io.StringIO()
    with create_pipe_input() as inp, create_app_session(input=inp, output=PlainTextOutput(screen)):
        async def cancel() -> None:
            await asyncio.sleep(0.6)
            inp.send_text("\t")                                    # from the box to OK
            await asyncio.sleep(0.1)
            inp.send_text("\t")                                    # ... to Cancel
            await asyncio.sleep(0.1)
            inp.send_text(ENTER)

        typing = asyncio.create_task(cancel())
        assert await asyncio.wait_for(_ask_setup(cfg), 30) is False
        await typing
    assert not cfg.client_id and not cfg.path.exists()


async def test_the_worker_tui_asks_and_joins_with_a_worker_code(engine, org, connect, tmp_path: Path):
    from worker_client.firstrun import ask_in_tui

    await _licence(connect)
    cfg = WorkerConfig(client_id="", tls=False, windows=False, path=tmp_path / "worker.json")
    _, screen = await _run(ask_in_tui, cfg, [f"127.0.0.1:{engine.port}", "WRKR-TUIT-ESTS-2222"])
    assert cfg.client_id and cfg.client_key
    assert "Leave it empty to have an IT Admin let it in instead." in screen
