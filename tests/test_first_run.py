"""A machine that is not set up is asked for the Engine's address and a licence code, and joins (the user, 5 Nov 2026)."""

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
from tests.conftest import requires_db
from worker_client import firstrun as worker
from worker_client.config import WorkerConfig
from worker_client.localapp import read_info
from worker_client.program.client import LocalClient

LICENCE = {"name": "Falcon", "reference": "ORD-1",
           "codes": [{"code": "ADMN-AAAA-BBBB-1111", "role": "admin", "seats": 3}, {"code": "WRKR-CCCC-DDDD-2222", "role": "worker", "seats": 3}]}


def test_an_address_is_an_ip_or_a_name_with_the_port_if_it_is_not_the_usual_one():
    assert parse_address(" 192.168.1.20 ") == ("192.168.1.20", 7400)
    assert parse_address("falcon.internal:7500") == ("falcon.internal", 7500)
    for bad in ("", "   ", "host:notaport", ":7400", "host:99999"):
        with pytest.raises(ValueError):
            parse_address(bad)


def test_what_went_wrong_is_said_so_the_person_can_act_on_it():
    assert "Could not reach the Engine at 10.0.0.9" in plain_reason(OSError("no route"), "10.0.0.9")
    assert plain_reason(EngineError("forbidden", "that licence code was withdrawn", "enroll.request"), "x") == "That licence code was withdrawn."
    assert plain_reason(ValueError("Type the licence code."), "x") == "Type the licence code."


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
    assert not console.needs_setup(LocalConfig(client_id="", signer="pipe"))             # the Worker service here does the joining
    assert worker.needs_setup(WorkerConfig(client_id="", path=fresh))
    assert not worker.needs_setup(WorkerConfig(client_id="", engine_host="falcon.internal", path=fresh))   # the install said where: it goes on by itself
    assert not worker.needs_setup(WorkerConfig(client_id="", engine_port=7500, path=fresh))                # an Engine on this same machine
    assert not worker.needs_setup(WorkerConfig(client_id="", enroll_code="WRKR", path=fresh))
    fresh.write_text("{}", encoding="utf-8")
    assert not worker.needs_setup(WorkerConfig(client_id="", path=fresh))                                  # the install wrote its settings
    assert console.needs_certificate(LocalConfig()) and not console.needs_certificate(LocalConfig(tls=False))


def test_a_machine_with_no_certificate_is_never_connected_to_unchecked():
    cfg = LocalConfig(client_id="", path=Path(os.devnull))
    why = asyncio.run(console.set_up(cfg, "127.0.0.1", "ADMN"))
    assert why == "Choose the Engine's certificate." and not cfg.client_id


async def _licence(connect) -> None:
    a1 = await connect("cid-a1")
    await a1.ok("licence.import", LICENCE)


@requires_db
@pytest.mark.organisation
async def test_a_console_joins_and_connects_with_an_admin_code(engine, org, connect, tmp_path: Path):
    await _licence(connect)
    cfg = LocalConfig(engine_host="127.0.0.1", client_id="", tls=False, path=tmp_path / "operator.json")
    address = f"127.0.0.1:{engine.port}"
    assert "not a licence code" in await console.set_up(cfg, address, "NOPE-NOPE")
    assert "worker code" in await console.set_up(cfg, address, "WRKR-CCCC-DDDD-2222")    # the Engine says it is the wrong kind
    assert not cfg.client_id
    out = await run_script(cfg, [f"setup {address} ADMN-AAAA-BBBB-1111", "status", "setup again now"])
    assert out[0].startswith("connected to 127.0.0.1") and "Admin" in out[0]
    assert out[2] == "This console is already set up."
    saved = json.loads((tmp_path / "operator.json").read_text(encoding="utf-8"))
    assert saved["client_id"] and saved["client_key"] and saved["engine_port"] == engine.port


@requires_db
@pytest.mark.organisation
async def test_a_console_that_cannot_reach_the_engine_is_told_and_stays_asked(tmp_path: Path):
    cfg = LocalConfig(client_id="", tls=False, path=tmp_path / "operator.json")
    assert "Could not reach the Engine at 127.0.0.1:9" in await console.set_up(cfg, "127.0.0.1:9", "ADMN-AAAA")
    assert console.needs_setup(cfg)


@requires_db
@pytest.mark.organisation
async def test_the_worker_is_asked_through_the_program_and_joins(engine, org, connect, tmp_path: Path, monkeypatch):
    await _licence(connect)

    async def no_program() -> None:
        return None

    monkeypatch.setattr(worker.FirstRun, "_open_program", staticmethod(no_program))
    monkeypatch.setenv("FALCON_NO_ACL", "1")
    cfg = WorkerConfig(client_id="", tls=False, windows=False, path=tmp_path / "worker.json")
    stop = asyncio.Event()
    run = asyncio.create_task(worker.FirstRun(cfg).run(stop))
    for _ in range(100):
        if read_info(cfg.path):
            break
        await asyncio.sleep(0.02)
    client = LocalClient(cfg.path)
    view = await asyncio.to_thread(client.view)
    assert view["setup"]["needs_cert"] is False and view["setup"]["error"] == "" and view["tasks"] == []

    await asyncio.to_thread(client.setup, f"127.0.0.1:{engine.port}", "NOPE", "")
    for _ in range(200):
        view = await asyncio.to_thread(client.view)
        if view["setup"]["error"]:
            break
        await asyncio.sleep(0.02)
    assert "not a licence code" in view["setup"]["error"] and not cfg.client_id          # told in the modal; it can try again

    await asyncio.to_thread(client.setup, f"127.0.0.1:{engine.port}", "WRKR-CCCC-DDDD-2222", "")
    await asyncio.wait_for(run, 15)                                                      # joined: the program's link goes with it
    assert cfg.client_id and cfg.client_key and read_info(cfg.path) is None
    assert json.loads(cfg.path.read_text(encoding="utf-8"))["engine_port"] == engine.port


def test_the_program_draws_the_setup_modal_with_no_qml_errors(tmp_path: Path):
    pytest.importorskip("PySide6")
    view = {"connected": False, "tasks": [], "announcements": [], "messages": [], "admins": [], "machine": {}, "toasts": [],
            "setup": {"address": "", "needs_cert": True, "busy": False, "error": "Could not reach the Engine at 10.0.0.9."}}
    out = tmp_path / "setup.png"
    done = subprocess.run([sys.executable, "-m", "worker_client.program", "--shot", str(out), "--view", json.dumps(view)],
                          capture_output=True, text=True, timeout=60, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}, check=False)
    assert done.returncode == 0 and out.exists(), done.stderr
    assert "QML:" not in done.stderr, done.stderr
