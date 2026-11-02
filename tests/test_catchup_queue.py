"""What a machine missed waits in a queue of its own, taken hottest first; its live events are never stuck behind it (the spine's worst case, docs/design/the-spine.md)."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


async def test_a_catch_up_is_taken_hottest_first_and_a_live_event_goes_ahead_of_it(engine, org, connect):
    w1 = await connect("cid-w1")
    pc = org["w1_pc"]
    seen: list[str] = []

    async def note(event):
        seen.append(event["path"])
    engine.file_index.subscribe(note, every_op=True, stage="act", name="test")
    engine.heat.touch(f"file:{pc}:C:/work/hot.txt")                          # someone is working on this one right now
    missed = [{"op": "modify", "path": f"C:/work/cold-{i}.txt", "name": f"cold-{i}.txt", "hash": f"c{i}"} for i in range(5)]
    missed.insert(3, {"op": "modify", "path": "C:/work/hot.txt", "name": "hot.txt", "hash": "old"})
    missed.append({"op": "modify", "path": "C:/work/later.txt", "name": "later.txt", "hash": "stale"})
    assert (await w1.ok("index.catchup", {"events": missed}))["accepted"] == 7
    # the machine says what changed just now while the catch-up is waiting: it goes straight through, and the stale one for that file is dropped
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/work/later.txt", "name": "later.txt", "hash": "fresh"}})
    assert await engine.file_index.catchup_settled(pc)
    assert seen.count("C:/work/later.txt") == 1                               # the live one; the stale missed one for that file was dropped
    assert next(p for p in seen if p != "C:/work/later.txt") == "C:/work/hot.txt"     # the hottest of what was missed is taken first
    assert sorted(seen) == sorted(["C:/work/later.txt", "C:/work/hot.txt"] + [f"C:/work/cold-{i}.txt" for i in range(5)])
    assert engine.file_index.catchup_superseded == 1
    row = await engine.db.file_index.by_path(pc, "C:/work/later.txt")
    assert row["content_hash"] == "fresh"                                     # the stale missed event never overwrote the live one


async def test_a_report_written_is_heard_at_the_tell_stage(engine, org):
    from engine.hierarchy import reports

    heard = []

    async def tell(event):
        heard.append((event.kind, event.data["category"], event.source))
    engine.bus.on("report.written", tell, stage="tell", name="test.tell")
    rid = await reports.emit(engine, "flow_failure", source_table="flows", source_id=1, summary="A flow stopped")
    assert rid and heard == [("report.written", "flow_failure", "system")]
