"""Is the Engine well: system.health before any sign-in, and `python -m engine health` for a monitor (Phase 10, ops)."""

from __future__ import annotations

from common.connection import EngineConnection
from engine.config import Settings
from tests.conftest import requires_db

pytestmark = requires_db


async def test_the_engine_says_how_it_is_before_anyone_signs_in_and_nothing_more(engine, org, connect):
    await connect("cid-w1")
    stranger = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)          # no key at all
    await stranger.open()
    try:
        got = await stranger.call("system.health")
    finally:
        await stranger.close()
    assert got["ok"] is True and got["database"]["ok"] is True and got["database"]["ms"] is not None
    assert got["machines_connected"] == 1 and got["uptime_s"] >= 0
    assert set(got) == {"ok", "version", "uptime_s", "database", "machines_connected", "connections"}     # nothing about the organisation


async def test_the_health_command_answers_with_an_exit_code_a_monitor_can_read(engine, capsys):
    from engine.__main__ import health

    settings = Settings(host="127.0.0.1", port=engine.port, dev_plaintext=True)
    assert await health(settings, f"127.0.0.1:{engine.port}") == 0
    assert capsys.readouterr().out.startswith("well: version")
    assert await health(settings, "127.0.0.1:1") == 2                                         # nothing listening there
