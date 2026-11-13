"""Detective's matcher in its own process (engine/detective/host.py, brain.py; the user, 12 Nov 2026): the Engine's loop never waits on its thinking, and if the
process dies a new one starts and is given the last days back from the database, as after a restart."""

from __future__ import annotations

import asyncio
import time

import pytest

from common.detective import Sig
from engine import detective
from engine.detective.brain import Brain
from engine.detective.host import ProcessMatcher
from tests.conftest import requires_db
from tests.test_detective_engine import _leak


async def test_the_process_answers_as_the_matcher_inside_the_engine_would():
    m = ProcessMatcher()
    try:
        here = Brain()
        t = 1_700_000_000.0
        sigs = [Sig(t, 1, "moved", "C:\\Windows\\Temp\\notes.txt.dll", "C:\\Finance\\payroll.xlsx", "h1", tags=frozenset({"restricted"})),
                Sig(t + 5, 1, "hid", "C:\\Windows\\Temp\\notes.txt.dll", thing="h1"),
                *[Sig(t + 10 + i, 1, "copied", f"C:\\Users\\kojo\\Staging\\p{i}.xlsx", f"C:\\Finance\\p{i}.xlsx", f"h-p{i}", tags=frozenset({"restricted"})) for i in range(12)]]
        for s in sigs:
            got, _ = await m.call("feed", s, {"tasks": set(), "uses": {}, "rules": []})
            want, _ = here.feed(s, {"tasks": set(), "uses": {}, "rules": []})
            assert [(u.case.key, u.case.level, round(u.case.weight, 9), u.case.intent, u.case.total, u.raised) for u in got] == \
                   [(u.case.key, u.case.level, round(u.case.weight, 9), u.case.intent, u.case.total, u.raised) for u in want]
        assert m.generation == 1 and await m.call("ping") == "pong"
    finally:
        await m.stop()
    assert m.proc is None


async def test_the_engine_s_loop_keeps_answering_while_the_process_works():
    """A thousand events sent at once: the loop is free the whole time (a timer that should tick every 10 ms is never late by much)."""
    m = ProcessMatcher()
    try:
        await m.ready()
        late = []

        async def tick():
            while True:
                t0 = time.perf_counter()
                await asyncio.sleep(0.01)
                late.append(time.perf_counter() - t0 - 0.01)

        ticker = asyncio.ensure_future(tick())
        t = 1_700_000_000.0
        await asyncio.gather(*(m.call("feed", Sig(t + i, 1, "copied", f"C:\\a\\f{i}.docx", f"C:\\b\\f{i}.docx", f"h{i % 50}"), None) for i in range(1000)))
        ticker.cancel()
        assert late and max(late) < 0.25, f"the loop was held for {max(late) * 1000:.0f} ms"
    finally:
        await m.stop()


@requires_db
async def test_a_matcher_that_dies_is_started_again_with_the_last_days_put_back(engine, org, connect):
    pc = org["w1_pc"]
    await _leak(engine, pc)
    m = detective._match(engine)
    if not isinstance(m, ProcessMatcher):
        pytest.skip("FALCON_DETECTIVE_PROCESS=0: the matcher is inside the Engine")
    before = await detective.memory(pc)
    assert before is not None and len(before.recent) > 10
    first = m.generation
    assert m.proc is not None
    m.proc.kill()
    for _ in range(100):
        if m.proc is None or m.proc.poll() is not None:
            break
        await asyncio.sleep(0.05)
    await engine.file_index.ingest_event(pc, {"op": "create", "path": "C:\\Users\\kojo\\after.txt", "name": "after.txt", "hash": "h-after"})
    await asyncio.sleep(0.2)
    assert m.generation == first + 1
    after = await detective.memory(pc)
    paths = {s.path for s in after.recent}
    assert "C:\\Users\\kojo\\after.txt" in paths and "E:\\q3.zip" in paths            # the new event, and what came before it, from the database
    su = await connect("cid-su")
    cases = (await su.ok("detective.cases", {}))["cases"]
    assert len(cases) == 1                                                            # the open case carried on: not raised a second time
