"""The spine: events through stages in a stated order, carrying what each stage finds out."""

from __future__ import annotations

import pytest

from engine.bus import MAX_DEPTH, STAGES, Bus
from tests.conftest import requires_db


async def test_stages_run_in_their_order_whatever_order_they_were_registered_in():
    bus, seen = Bus(), []

    async def make(name):
        async def h(event):
            seen.append(name)
        return h

    for stage in ("judge", "tell", "act", "guard", "heat"):
        bus.on("file.*", await make(stage), stage=stage, name=stage)
    await bus.publish("file.move", {"path": "C:/a"})
    assert seen == list(STAGES)
    with pytest.raises(ValueError):
        bus.on("x", await make("?"), stage="whenever")


async def test_what_one_stage_finds_out_travels_with_the_event_to_the_next():
    bus = Bus()

    async def guard(event):
        event.facts["restricted"] = "the folder Payroll is marked restricted"

    async def judge(event):
        event.facts["verdict"] = "weighed heavier" if event.facts.get("restricted") else "ordinary"

    bus.on("file.*", judge, stage="judge", name="judge")
    bus.on("file.*", guard, stage="guard", name="guard")
    ev = await bus.publish("file.copy", {"path": "E:/x"}, source="os", pc=7)
    assert ev.facts == {"restricted": "the folder Payroll is marked restricted", "verdict": "weighed heavier"}
    assert ev.source == "os" and ev.pc == 7 and ev.chain() == ["file.copy"]


async def test_a_handler_that_fails_costs_no_other_handler_the_event():
    bus, seen = Bus(), []

    async def bad(event):
        raise RuntimeError("a bug in one feature")

    async def good(event):
        seen.append(event.kind)

    bus.on("usb.*", bad, stage="guard", name="bad")
    bus.on("usb.*", good, stage="judge", name="good")
    await bus.publish("usb.inserted", {})
    assert seen == ["usb.inserted"] and bus.failures["bad"] == 1 and bus.counts["usb.inserted"] == 1


async def test_kinds_are_matched_exactly_or_by_prefix_and_only_what_is_asked_for_is_heard():
    bus, seen = Bus(), []

    async def h(event):
        seen.append(event.kind)

    bus.on(("task.assigned", "flow.*"), h)
    for kind in ("task.assigned", "task.done", "flow.synced", "flow.failed", "file.move"):
        await bus.publish(kind, {})
    assert seen == ["task.assigned", "flow.synced", "flow.failed"]


async def test_an_event_that_causes_events_is_followed_and_a_loop_between_features_cannot_run_away():
    bus, seen = Bus(), []

    async def echo(event):
        seen.append((event.kind, event.depth))
        await bus.publish("case.raised", {}, cause=event)                  # two features that keep answering each other

    bus.on("case.raised", echo, stage="judge", name="echo")
    first = await bus.publish("case.raised", {})
    assert first.chain() == ["case.raised"] and len(seen) == MAX_DEPTH + 1
    assert bus.dropped == 1 and [d for _, d in seen] == list(range(MAX_DEPTH + 1))


@requires_db
async def test_a_file_event_goes_heat_then_guard_then_act_then_judge_and_arrives_with_the_facts(engine, org):
    handlers = engine.bus.handlers()
    assert any(h.startswith("heat:") for h in handlers["heat"])
    assert [h.split(":")[0] for h in handlers["guard"]][:3] == ["resource", "facts", "marks"] or {"resource", "facts", "marks"} <= {h.split(":")[0] for h in handlers["guard"]}
    assert {"flow", "task", "automations", "issues"} <= {h.split(":")[0] for h in handlers["act"]}
    assert any(h.startswith("detective:") for h in handlers["judge"])

    caught = []

    async def look(event):
        caught.append(event)

    engine.bus.on("file.*", look, stage="tell", name="test")
    pc = org["w1_pc"]
    mark = await engine.db.marks.create("folder", "Payroll", pc, r"C:\Finance\Payroll", "path", org["a1"], None)
    await engine.db.marks.add_hash(mark, "h-secret", r"C:\Finance\Payroll\p.xlsx")
    engine.marked.invalidate()
    await engine.file_index.ingest_event(pc, {"op": "copy", "path": r"C:\Temp\copy-of-p.xlsx", "name": "copy-of-p.xlsx", "hash": "h-secret", "old_path": r"C:\Finance\Payroll\p.xlsx"})
    await engine.file_index.ingest_event(pc, {"op": "create", "path": r"C:\Work\plain.txt", "name": "plain.txt", "hash": "h-plain"})
    secret, plain = caught[-2], caught[-1]
    assert secret.facts["restricted"] and "copy of Payroll" in secret.facts["restricted"].replace("a copy of", "copy of") or "marked restricted" in secret.facts["restricted"]
    assert secret.facts["flow_wrote"] is False and secret.facts["entry"]["path"] == r"C:\Temp\copy-of-p.xlsx" and secret.source == "os" and secret.kind == "file.copy"
    assert plain.facts["restricted"] is None
    assert engine.heat.hot(f"file:{pc}:C:\\Work\\plain.txt")                                          # first of all, the heat stage


@requires_db
async def test_the_in_memory_index_of_marks_follows_the_marks_and_never_decides_for_a_flow(engine, org):
    pc = org["w1_pc"]
    assert await engine.marked.reason(pc, r"C:\x\a.txt", "h-1") is None
    mark = await engine.db.marks.create("file", "A", pc, r"C:\x\a.txt", "path", org["a1"], None)
    await engine.db.marks.add_hash(mark, "h-1", r"C:\x\a.txt")
    assert await engine.marked.reason(pc, r"C:\x\a.txt") is None                                       # not yet told: the index is a speed-up, refreshed within a minute
    engine.marked.invalidate()
    assert "A is marked restricted" in (await engine.marked.reason(pc, r"C:\x\a.txt") or "")
    assert "copy of A" in (await engine.marked.reason(org["w2_pc"], r"D:\elsewhere\b.txt", "h-1") or "")
    await engine.db.marks.unmark(mark, org["a1"])
    from engine.flow import guard

    assert "marked restricted" not in (await guard.restricted_reason(engine, pc, r"C:\x\a.txt") or "")   # the flow's check reads the database, so unmarking is seen at once
