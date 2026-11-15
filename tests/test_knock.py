"""The Worker knocks until it is given a seat, and knocks again when the seat is taken back (worker_client/knock.py; docs/SEATS-AND-SETUP.md
section 6, steps 3, 5 and 6)."""

from __future__ import annotations

import asyncio

import pytest

from tests.conftest import requires_db

pytestmark = requires_db


def _cfg(engine, tmp_path):
    from worker_client.config import WorkerConfig

    return WorkerConfig(engine_host="127.0.0.1", engine_port=engine.port, tls=False, windows=False, watch_roots=[str(tmp_path)],
                        path=tmp_path / "worker.json")


async def _until(cond, seconds: float = 10.0) -> bool:
    for _ in range(int(seconds / 0.05)):
        if await cond():
            return True
        await asyncio.sleep(0.05)
    return False


async def test_a_worker_knocks_is_nudged_the_moment_it_is_seated_and_keeps_its_key(engine, org, connect, tmp_path):
    from worker_client.config import WorkerConfig
    from worker_client.knock import knock

    a1 = await connect("cid-a1")
    cfg = _cfg(engine, tmp_path)
    stop = asyncio.Event()
    task = asyncio.create_task(knock(cfg, stop, ladder=(30.0,)))           # it would wait 30 s between knocks: only the nudge brings it back sooner
    try:
        assert await _until(lambda: _knocking(a1))
        token = cfg.install_token
        assert token and WorkerConfig.load(cfg.path).install_token == token    # made once, kept in its settings
        k = (await a1.ok("knocks.list"))["knocks"][0]
        assert k["hostname"] and k["hardware_id"] and k["os"]                   # what tells it apart
        await a1.ok("seat.give", {"knock_id": k["id"], "department_id": org["fin"]})
        assert await asyncio.wait_for(task, 10) is True                        # nudged at once, not after 30 s
    finally:
        stop.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    saved = WorkerConfig.load(cfg.path)
    assert saved.client_id and saved.client_key and saved.install_token == token


async def _knocking(a1) -> bool:
    return bool((await a1.ok("knocks.list"))["knocks"])


async def test_when_its_seat_is_taken_back_the_worker_drops_its_key_and_knocks_again(engine, org, connect, tmp_path):
    from worker_client.config import WorkerConfig
    from worker_client.knock import knock
    from worker_client.service import SeatTaken, WorkerService

    a1 = await connect("cid-a1")
    cfg = _cfg(engine, tmp_path)
    stop = asyncio.Event()
    task = asyncio.create_task(knock(cfg, stop, ladder=(0.2,)))
    assert await _until(lambda: _knocking(a1))
    k = (await a1.ok("knocks.list"))["knocks"][0]
    given = await a1.ok("seat.give", {"knock_id": k["id"], "department_id": org["fin"]})
    assert await asyncio.wait_for(task, 10) is True
    await a1.ok("seat.take", {"pc_id": given["pc_id"]})
    svc = WorkerService(cfg, native_watch=False)
    with pytest.raises(SeatTaken):
        await svc._connect(forever=True)                                    # told no_seat: it does not keep retrying with a useless key
    assert svc.seat_taken.is_set()
    saved = WorkerConfig.load(cfg.path)
    assert saved.client_id == "" and saved.client_key == "" and saved.install_token == cfg.install_token
    again = asyncio.create_task(knock(saved, stop, ladder=(0.2,)))           # the same installed PC knocks again
    try:
        assert await _until(lambda: _knocking(a1))
        assert (await a1.ok("knocks.list"))["knocks"][0]["id"] == k["id"]   # one row: it is the same PC
    finally:
        stop.set()
        again.cancel()
        await asyncio.gather(again, return_exceptions=True)


async def test_an_installed_service_with_no_key_knocks_shows_nothing_and_carries_on_once_seated(engine, org, connect, tmp_path, monkeypatch):
    """What an installed Worker does on first start: no client id, so it knocks; no window, no code; seated, it keeps the key it is handed."""
    from worker_client import winservice
    from worker_client.config import WorkerConfig
    from worker_client.windows import spawn

    opened: list[str] = []

    async def no_window(kind, spec):
        opened.append(kind)

    monkeypatch.setattr(spawn, "open_window", no_window)
    a1 = await connect("cid-a1")
    cfg = WorkerConfig(windows=True, engine_host="127.0.0.1", engine_port=engine.port, tls=False,
                       path=tmp_path / "private" / "worker.json")
    stop = asyncio.Event()
    task = asyncio.create_task(winservice._wait_to_be_registered(cfg, stop))
    try:
        assert await _until(lambda: _knocking(a1))
        assert not cfg.client_id
        k = (await a1.ok("knocks.list"))["knocks"][0]
        await a1.ok("seat.give", {"knock_id": k["id"], "department_id": org["fin"]})
        await asyncio.wait_for(task, 20)
        saved = WorkerConfig.load(cfg.path)
        assert saved.client_id == cfg.client_id != "" and saved.client_key == cfg.client_key != ""
        assert opened == []                                                 # nothing was put on anybody's screen
    finally:
        stop.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_a_machine_installed_while_the_engine_is_off_keeps_knocking_until_it_answers(engine, org, connect, tmp_path, monkeypatch):
    """Found installing setup.exe for real (14 Nov 2026): the first refused connection must not end the service."""
    from common.connection import EngineConnection
    from worker_client.knock import knock

    real_open, refused = EngineConnection.open, []

    async def open_(self, *a, **kw):
        if len(refused) < 2:
            refused.append(1)
            raise ConnectionRefusedError(1225, "The remote computer refused the network connection")
        return await real_open(self, *a, **kw)

    a1 = await connect("cid-a1")                                           # (connected before the refusals start: only the knocking machine meets them)
    monkeypatch.setattr(EngineConnection, "open", open_)
    cfg = _cfg(engine, tmp_path)
    stop = asyncio.Event()
    task = asyncio.create_task(knock(cfg, stop, ladder=(0.05,)))
    try:
        assert await _until(lambda: _knocking(a1))
        assert len(refused) == 2 and not task.done()
    finally:
        stop.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
