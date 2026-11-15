"""A machine that is not set up (the user, 5 Nov 2026; changed 15 Nov 2026, docs/SEATS-AND-SETUP.md): nothing joins from a first run any
more. The console and the Worker's program are told to run their setup, which is the only way a machine learns where its Engine is."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from common.connection import EngineError
from common.firstrun import keep_certificate, parse_address, plain_reason
from operator_client.core import firstrun as console
from operator_client.core.config import LocalConfig
from operator_client.tui.shell import run_script
from worker_client import firstrun as worker
from worker_client.config import WorkerConfig
from worker_client.localapp import read_info
from worker_client.program.client import LocalClient


def test_an_address_is_an_ip_or_a_name_with_the_port_if_it_is_not_the_usual_one():
    assert parse_address(" 192.168.1.20 ") == ("192.168.1.20", 7400)
    assert parse_address("falcon.internal:7500") == ("falcon.internal", 7500)
    for bad in ("", "   ", "host:notaport", ":7400", "host:99999"):
        with pytest.raises(ValueError):
            parse_address(bad)


def test_what_went_wrong_is_said_so_the_person_can_act_on_it():
    assert "Could not reach the Engine at 10.0.0.9" in plain_reason(OSError("no route"), "10.0.0.9")
    assert plain_reason(EngineError("forbidden", "that seat was taken back", "knock.hello"), "x") == "That seat was taken back."
    assert plain_reason(ValueError("Choose the Engine's certificate."), "x") == "Choose the Engine's certificate."


def test_the_certificate_is_kept_beside_the_settings(tmp_path: Path):
    src = tmp_path / "usb" / "engine.crt"
    src.parent.mkdir()
    src.write_text("PEM", encoding="utf-8")
    kept = Path(keep_certificate(str(src), tmp_path / "falcon"))
    assert kept.read_text(encoding="utf-8") == "PEM" and kept.parent.name == "falcon"
    with pytest.raises(ValueError):
        keep_certificate(str(tmp_path / "gone.crt"), tmp_path)


def test_who_is_asked(tmp_path: Path):
    fresh = tmp_path / "worker.json"
    assert console.needs_setup(LocalConfig(client_id=""))
    assert not console.needs_setup(LocalConfig(client_id="cid-a1"))
    assert not console.needs_setup(LocalConfig(client_id="", signer="pipe"))             # the Worker service here signs for it
    assert worker.needs_setup(WorkerConfig(client_id="", path=fresh))
    assert not worker.needs_setup(WorkerConfig(client_id="", engine_host="falcon.internal", path=fresh))   # the setup said where: it knocks
    assert not worker.needs_setup(WorkerConfig(client_id="", engine_port=7500, path=fresh))                # an Engine on this same machine
    fresh.write_text("{}", encoding="utf-8")
    assert not worker.needs_setup(WorkerConfig(client_id="", path=fresh))                                  # the setup wrote its settings
    assert console.needs_certificate(LocalConfig()) and not console.needs_certificate(LocalConfig(tls=False))


async def test_a_console_is_told_to_run_the_admin_setup_and_nothing_joins(tmp_path: Path):
    cfg = LocalConfig(engine_host="127.0.0.1", client_id="", tls=False, path=tmp_path / "operator.json")
    said = await console.set_up(cfg, "127.0.0.1:7400", "ANY-CODE", "")
    assert "Admin setup" in said and "signs in" in said and not cfg.client_id and not (tmp_path / "operator.json").exists()
    out = await run_script(cfg, ["setup 127.0.0.1:7400 ANY-CODE"])
    assert "Admin setup" in out[0] and not cfg.client_id


async def test_the_worker_s_program_is_told_to_run_the_worker_setup_and_nothing_joins(tmp_path: Path, monkeypatch):
    async def no_program() -> None:
        return None

    monkeypatch.setattr(worker.FirstRun, "_open_program", staticmethod(no_program))
    monkeypatch.setenv("FALCON_NO_ACL", "1")
    cfg = WorkerConfig(client_id="", tls=False, windows=False, path=tmp_path / "worker.json")
    stop = asyncio.Event()
    run = asyncio.create_task(worker.FirstRun(cfg).run(stop))
    try:
        for _ in range(100):
            if read_info(cfg.path):
                break
            await asyncio.sleep(0.02)
        client = LocalClient(cfg.path)
        view = await asyncio.to_thread(client.view)
        assert view["setup"]["error"] == "" and view["tasks"] == []
        await asyncio.to_thread(client.setup, "127.0.0.1:7400", "ANY-CODE", "")
        for _ in range(200):
            view = await asyncio.to_thread(client.view)
            if view["setup"]["error"]:
                break
            await asyncio.sleep(0.02)
        assert "Worker setup" in view["setup"]["error"] and "company's file" in view["setup"]["error"]
        assert not cfg.client_id and not cfg.path.exists()                                   # nothing was joined or written from here
    finally:
        stop.set()
        await asyncio.wait_for(run, 15)


def test_the_program_draws_the_setup_modal_with_no_qml_errors(tmp_path: Path):
    pytest.importorskip("PySide6")
    view = {"connected": False, "tasks": [], "announcements": [], "messages": [], "admins": [], "machine": {}, "toasts": [],
            "setup": {"address": "", "needs_cert": True, "busy": False, "error": worker.SET_UP_BY_THE_SETUP}}
    out = tmp_path / "setup.png"
    done = subprocess.run([sys.executable, "-m", "worker_client.program", "--shot", str(out), "--view", json.dumps(view)],
                          capture_output=True, text=True, timeout=60, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}, check=False)
    assert done.returncode == 0 and out.exists(), done.stderr
    assert "QML:" not in done.stderr, done.stderr
