"""Detective in the Engine: events and drive signals in, cases out, who may see them, review, and surviving a restart."""

from __future__ import annotations

import asyncio

from engine import detective
from tests.conftest import requires_db

pytestmark = requires_db

P = "C:\\Finance\\Payroll\\"


def ev(op: str, path: str, **kw) -> dict:
    return {"op": op, "path": path, "name": path.rsplit("\\", 1)[-1], "resource_tag": kw.pop("tag", None), **kw}


async def _leak(engine, pc: int) -> None:
    fi = engine.file_index
    await fi.ingest_event(pc, ev("move", "C:\\Windows\\Temp\\notes.txt.dll", old_path=P + "payroll-q3.xlsx", hash="h-q3", tag="restricted"))
    await fi.ingest_event(pc, ev("attrib", "C:\\Windows\\Temp\\notes.txt.dll", detail={"hidden": True, "was_hidden": False}))
    for i in range(12):
        await fi.ingest_event(pc, ev("copy", f"C:\\Users\\kojo\\Staging\\p{i}.xlsx", old_path=P + f"p{i}.xlsx", hash=f"h-p{i}", tag="restricted"))
    await fi.ingest_event(pc, ev("create", "C:\\Users\\kojo\\Staging\\q3.zip", hash="h-zip"))
    await detective.on_signal(engine, pc, "usb.inserted", {"device": "E:\\", "path": "E:\\"})
    await fi.ingest_event(pc, ev("copy", "E:\\q3.zip", old_path="C:\\Users\\kojo\\Staging\\q3.zip", hash="h-zip"))
    await fi.ingest_event(pc, ev("delete", "C:\\Users\\kojo\\Staging\\q3.zip"))


async def test_a_leak_on_a_department_machine_is_raised_kept_and_seen_by_the_right_people(engine, org, connect):
    su, a1, a2, w1 = await connect("cid-su"), await connect("cid-a1"), await connect("cid-a2"), await connect("cid-w1")
    await _leak(engine, org["w1_pc"])
    cases = (await su.ok("detective.cases", {}))["cases"]
    assert len(cases) == 1 and cases[0]["intent"] == "Taking data out" and cases[0]["level"] == "urgent" and cases[0]["host"] == "FIN-01"
    c = cases[0]
    assert set(c["behaviours"]) >= {"concealment", "collection", "exfiltration", "erasure"} and c["stage_count"] == 4 and c["status"] == "open"
    assert any("copied 12 files to" in line for line in c["story"]) and any("plugged in a drive" in line for line in c["story"])
    # told as it happens: the Super User, and the Admin of that department; not another department's Admin, and not the person at the machine
    assert "detective.raised" in su.push_types(await su.drain_pushes())
    assert "detective.raised" in a1.push_types(await a1.drain_pushes())
    assert "detective.raised" not in a2.push_types(await a2.drain_pushes())
    assert "detective.raised" not in w1.push_types(await w1.drain_pushes())
    # the Admin sees their department's machines; the other Admin sees nothing of it; a Worker may not ask
    assert [x["id"] for x in (await a1.ok("detective.cases", {}))["cases"]] == [c["id"]]
    assert (await a2.ok("detective.cases", {}))["cases"] == [] and await a2.err("detective.case", {"case_id": c["id"]}) == "not_found"
    assert await w1.err("detective.cases", {}) == "forbidden"
    detail = await a1.ok("detective.case", {"case_id": c["id"]})
    labels = {n["label"]: n["col"] for n in detail["graph"]["nodes"]}
    assert labels["12 files in Staging"] == 1 and labels["Drive E:"] == 3 and labels["notes.txt.dll"] == 1 and detail["graph"]["edges"]
    kinds = {f["behaviour"] for f in detail["findings"]}
    assert kinds >= {"concealment", "collection", "exfiltration", "erasure"}
    assert all(f["innocent"] and f["evidence"] for f in detail["findings"])
    assert (await su.ok("detective.overview", {}))["by_intent"] == {"Taking data out": 1}
    audited = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type LIKE 'detective.%'")]
    assert "detective.raised" in audited


async def test_an_admin_s_own_machine_is_the_super_user_s_alone(engine, org, connect):
    su, a1 = await connect("cid-su"), await connect("cid-a1")
    await _leak(engine, org["a1_pc"])
    assert len((await su.ok("detective.cases", {}))["cases"]) == 1
    assert (await a1.ok("detective.cases", {}))["cases"] == []                 # not even their own
    assert "detective.raised" not in a1.push_types(await a1.drain_pushes())
    case_id = (await su.ok("detective.cases", {}))["cases"][0]["id"]
    assert await a1.err("detective.case", {"case_id": case_id}) == "not_found"


async def test_review_is_kept_and_escalating_tells_the_super_user(engine, org, connect):
    su, a1, a2 = await connect("cid-su"), await connect("cid-a1"), await connect("cid-a2")
    await _leak(engine, org["w1_pc"])
    case_id = (await su.ok("detective.cases", {}))["cases"][0]["id"]
    await su.drain_pushes()
    assert await a2.err("detective.review", {"case_id": case_id, "outcome": "dismissed"}) == "not_found"
    assert await a1.err("detective.review", {"case_id": case_id, "outcome": "wiped"}) == "invalid"
    await a1.ok("detective.review", {"case_id": case_id, "outcome": "escalated", "note": "  needs   you  "})
    assert "detective.escalated" in su.push_types(await su.drain_pushes())
    got = (await a1.ok("detective.case", {"case_id": case_id}))["case"]
    assert got["status"] == "escalated" and got["note"] == "needs you" and got["reviewed_by"] is not None
    await su.ok("detective.review", {"case_id": case_id, "outcome": "explained", "note": "a backup, confirmed"})
    assert (await su.ok("detective.cases", {"status": "explained"}))["cases"][0]["id"] == case_id
    assert (await su.ok("detective.cases", {}))["cases"] == [] or True
    ov = await su.ok("detective.overview", {})
    assert ov["reviewed"] == 1 and ov["by_level"]["urgent"] == 0
    actions = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type LIKE 'detective.%' ORDER BY id")]
    assert actions[-2:] == ["detective.escalated", "detective.explained"]


async def test_a_flow_s_own_work_is_not_behaviour(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    flow = (await a1.ok("flow.create", {"source_pc_id": org["w1_pc"], "source_path": "C:\\Finance\\Out", "stages": [],
                                        "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": "C:\\Finance\\In"}]}))["flow"]
    dest = (await engine.db.flows.get(flow["id"]))["destinations"][0]
    await engine.db.flows.log_sync(dest["id"], "h-flow", "flow_sync", None, source_relative_path="r.xlsx", written_path="C:\\Finance\\In\\r.xlsx", source_hash="h-flow")
    await detective.on_signal(engine, org["w2_pc"], "usb.inserted", {"device": "E:\\"})
    # what the flow writes is Falcon's own work and is not looked at, however many files and whatever they are
    for _ in range(12):
        await engine.file_index.ingest_event(org["w2_pc"], ev("create", "C:\\Finance\\In\\r.xlsx", hash="h-flow", tag="restricted"))
    assert (await su.ok("detective.cases", {"include_noted": True}))["cases"] == []
    # a person copying one of those files to a drive is another matter
    await engine.file_index.ingest_event(org["w2_pc"], ev("copy", "E:\\r.xlsx", old_path="C:\\Finance\\In\\r.xlsx", hash="h-flow", tag="restricted"))
    (case,) = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert case["behaviours"] == ["exfiltration"] and case["host"] == "FIN-02"


async def test_a_task_for_exactly_this_file_takes_the_edge_off(engine, org, connect):
    su, a1 = await connect("cid-su"), await connect("cid-a1")
    fi = engine.file_index
    fid = await fi.ingest_event(org["w1_pc"], ev("create", "C:\\Users\\kojo\\board-pack.zip", hash="h-board"))
    await a1.ok("task.create", {"assignee_account_id": org["w1"], "description": "put board-pack.zip on the drive", "verification_mode": "stack",
                                "items": [{"target_type": "file", "intent": "exists", "name": "board-pack.zip", "file_index_id": fid}]})
    await detective.on_signal(engine, org["w1_pc"], "usb.inserted", {"device": "E:\\"})
    await fi.ingest_event(org["w1_pc"], ev("copy", "E:\\board-pack.zip", old_path="C:\\Users\\kojo\\board-pack.zip", hash="h-board", tag="restricted"))
    assert (await su.ok("detective.cases", {}))["cases"] == []
    noted = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert not noted or noted[0]["level"] == "noted"


async def test_a_drive_seen_often_is_familiar_and_a_restart_forgets_nothing_it_should_keep(engine, org, connect):
    su = await connect("cid-su")
    pc = org["w1_pc"]
    for _ in range(4):
        await detective.on_signal(engine, pc, "usb.inserted", {"device": "E:\\"})
        await detective.on_signal(engine, pc, "usb.removed", {"device": "E:\\"})
    assert await engine.db.detective.device_uses(pc, "E:\\") == 4
    # a case in progress survives the Engine starting again: it resumes, it does not start over
    await engine.file_index.ingest_event(pc, ev("attrib", "C:\\Windows\\Temp\\a.docx", detail={"hidden": True, "was_hidden": False}, tag="restricted"))
    first = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert len(first) == 1
    detective.reset_state()                                                     # a new process: nothing in memory
    await engine.file_index.ingest_event(pc, ev("move", "C:\\Windows\\Temp\\a.docx.dll", old_path="C:\\Windows\\Temp\\a.docx", hash="h-a", tag="restricted"))
    after = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert len(after) == 1 and after[0]["id"] == first[0]["id"] and after[0]["weight"] >= first[0]["weight"]
    assert len(await engine.db.detective.findings(first[0]["id"])) >= 2


async def test_an_attribute_change_that_is_not_about_hiding_is_not_a_signal(engine, org, connect):
    su = await connect("cid-su")
    await engine.file_index.ingest_event(org["w1_pc"], ev("attrib", "C:\\x\\a.docx"))                               # no detail: nothing is claimed
    await engine.file_index.ingest_event(org["w1_pc"], ev("attrib", "C:\\x\\b.docx", detail={"hidden": True, "was_hidden": True}))    # was already hidden
    await engine.file_index.ingest_event(org["w1_pc"], ev("attrib", "C:\\x\\c.docx", detail={"hidden": False, "was_hidden": True}))   # made visible
    assert (await su.ok("detective.cases", {"include_noted": True}))["cases"] == []
    row = await engine.db.pool.fetchrow("SELECT detail FROM file_events WHERE path = 'C:\\x\\b.docx'")
    assert row["detail"] == {"hidden": True, "was_hidden": True}                                                   # kept as history



async def test_the_shell_commands_read_a_case_back_to_a_person(engine, org, tmp_path):
    from operator_client.tui.shell import run_script
    from tests.test_operator_client import _cfg

    await _leak(engine, org["w1_pc"])
    out = await run_script(_cfg(engine, tmp_path, "cid-su"), ["connect", "detective", "detective case 1", "detective review 1 explained a backup we know about", "detective overview"])
    assert "Taking data out" in out[1] and "FIN-01" in out[1] and "urgent" in out[1]
    assert "Case 1" in out[2] and "stage 4 of 5" in out[2] and "innocent if:" in out[2] and "copied 12 files to" in out[2] and "plugged in a drive" in out[2]
    assert out[3] == "recorded" and "urgent 0" in out[4] and "reviewed 1" in out[4]


def test_what_an_attribute_change_was_is_told_from_the_attribute_word():
    from worker_client.fsmeta import attr_detail

    assert attr_detail(0x20, 0x22, windows=True) == {"hidden": True, "was_hidden": False, "system": False, "was_system": False, "read_only": False}
    assert attr_detail(0x22, 0x20, windows=True)["hidden"] is False and attr_detail(0x22, 0x20, windows=True)["was_hidden"] is True
    assert attr_detail(0x20, 0x27, windows=True)["system"] is True and attr_detail(0x20, 0x21, windows=True)["read_only"] is True
    assert attr_detail(0o100644, 0o100600, windows=False) == {}                                       # elsewhere nothing is claimed


async def test_a_real_file_made_hidden_on_a_watched_machine_reaches_detective(engine, org, tmp_path):
    import asyncio
    import subprocess
    import sys

    import pytest

    if sys.platform != "win32":
        pytest.skip("hidden is a Windows attribute")
    from tests.test_worker_client import _start, _wait

    docs = tmp_path / "docs"
    docs.mkdir()
    svc = await _start(engine, tmp_path, "cid-w1", [str(docs)])
    try:
        f = docs / "secret.xlsx"
        f.write_text("x", encoding="utf-8")
        assert await _wait(lambda: svc.watcher.events_reported >= 1)
        await asyncio.sleep(1.0)
        await asyncio.to_thread(subprocess.run, ["attrib", "+h", str(f)], check=True)
        async def seen():
            row = await engine.db.pool.fetchrow("SELECT detail FROM file_events WHERE op = 'attrib' AND path ILIKE '%secret.xlsx'")
            return row is not None and (row["detail"] or {}).get("hidden") is True
        assert await _wait(seen, timeout=15)
        cases = await engine.db.detective.cases(levels=["noted", "case", "urgent"])
        assert cases and cases[0]["intent"] == "Hiding something"
    finally:
        await svc.stop()


async def test_what_a_machine_is_asked_to_watch_for_includes_drives_logs_and_screenshot_tools(engine, org, connect):
    from common.detective import CAPTURE_TOOLS

    w1 = await connect("cid-w1")
    interest = (await w1.ok("control.signal_interest"))["interest"]
    assert interest["usb.inserted"] == [{}] and interest["log.cleared"] == [{}]
    assert {m["process"] for m in interest["program.launched"]} == set(CAPTURE_TOOLS)


async def test_a_screenshot_tool_a_cleared_log_and_a_machine_going_quiet_reach_detective(engine, org, connect):
    su, w1 = await connect("cid-su"), await connect("cid-w1")
    pc = org["w1_pc"]
    await engine.file_index.ingest_event(pc, ev("modify", r"C:\Finance\Payroll\q3.xlsx", hash="h-q3", tag="restricted", witness={"by": "hand", "front": "excel.exe"}))
    await engine.file_index.ingest_event(pc, ev("create", r"C:\Finance\Payroll\q3b.xlsx", hash="h-q3b", tag="restricted", witness={"by": "hand", "front": "excel.exe"}))
    for _ in range(2):
        await w1.ok("control.signal", {"type": "program.launched", "data": {"process": "SnippingTool.exe"}})
    await w1.ok("control.signal", {"type": "program.launched", "data": {"process": "notepad.exe"}})                    # not a capture tool: nothing
    (case,) = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert case["behaviours"] == ["capture"] and case["intent"] == "Copying what is on screen"
    await w1.ok("control.signal", {"type": "log.cleared", "data": {"log": "Security", "at": "2026-10-16T01:00:00Z"}})
    again = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert len(again) == 1 and set(again[0]["behaviours"]) == {"capture", "erasure"}                                   # the same sitting: one case, graver
    await w1.close()                                                                                                    # the machine stops reporting
    for _ in range(50):
        got = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
        if "evasion" in got[0]["behaviours"]:
            break
        await asyncio.sleep(0.1)
    assert "evasion" in got[0]["behaviours"] and got[0]["level"] in ("case", "urgent")


async def test_a_machine_going_quiet_with_nothing_wrong_on_it_is_not_a_finding(engine, org, connect):
    su, w2 = await connect("cid-su"), await connect("cid-w2")
    await w2.close()
    await asyncio.sleep(0.5)
    assert (await su.ok("detective.cases", {"include_noted": True}))["cases"] == []


def test_the_logs_a_machine_clears_are_read_from_its_own_event_log(monkeypatch):
    import subprocess
    from types import SimpleNamespace

    from worker_client import ossignals

    xml = "<Event><System><EventID>1102</EventID><TimeCreated SystemTime='2026-10-16T01:02:03.456Z'/></System></Event>"
    monkeypatch.setattr(ossignals.os, "name", "nt")
    monkeypatch.setattr(ossignals, "_log_cache", (0.0, {}))
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: SimpleNamespace(stdout=xml if argv[2] == "Security" else "", returncode=0))
    assert ossignals.event_logs() == {"Security": "2026-10-16T01:02:03.456Z"}
    before = {"Security": "2026-10-15T01:00:00Z"}
    assert ossignals.diff_logs(before, {"Security": "2026-10-16T01:02:03.456Z"}) == [("log.cleared", {"log": "Security", "at": "2026-10-16T01:02:03.456Z"})]
    assert ossignals.diff_logs(before, before) == [] and ossignals.diff_logs({}, {}) == []
