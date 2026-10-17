"""The witness stamp: was a person at the keyboard when a file changed, and what was in front -- taken by the Worker, carried to Detective as a weight."""

from __future__ import annotations

import asyncio

from tests.conftest import requires_db
from worker_client.witness import ALONE_SECONDS, HAND_SECONDS, Witness, classify


def test_a_change_is_by_hand_by_a_started_program_or_alone_by_how_long_since_anyone_touched_the_machine():
    assert classify(0.0) == "hand" and classify(HAND_SECONDS) == "hand"
    assert classify(HAND_SECONDS + 0.1) == "started" and classify(ALONE_SECONDS - 0.1) == "started"
    assert classify(ALONE_SECONDS) == "alone" and classify(3600) == "alone"
    assert classify(None) == "unknown"


async def test_the_program_in_front_is_claimed_only_for_a_person_s_own_hands():
    class Clock:
        t = 0.0

    looks = []

    async def source():
        looks.append(1)
        return state["idle"], "excel.exe"

    state = {"idle": 0.5}
    w = Witness(source, clock=lambda: Clock.t)
    assert await w.stamp() == {"by": "hand", "front": "excel.exe"}
    state["idle"] = 600
    assert await w.stamp() == {"by": "hand", "front": "excel.exe"} and len(looks) == 1             # the same second: one look serves a burst
    Clock.t = 5.0
    assert await w.stamp() == {"by": "alone"}                                                      # nobody there: the program in front is not theirs to claim
    assert len(looks) == 2


async def test_a_stamp_that_cannot_be_taken_is_unknown_not_a_failed_report():
    async def broken():
        raise OSError("no desktop")

    assert await Witness(broken).stamp() == {"by": "unknown"}


@requires_db
async def test_the_stamp_travels_with_the_event_and_changes_what_detective_makes_of_it(engine, org, connect):
    from tests.test_detective_engine import ev

    su = await connect("cid-su")

    async def run(pc, by):
        await engine.file_index.ingest_event(pc, ev("move", "C:\\Windows\\Temp\\n.docx.dll", old_path="C:\\Finance\\n.docx", hash=f"h-{by}", tag="restricted",
                                                    witness={"by": by, "front": "explorer.exe"}))

    await run(org["w1_pc"], "hand")
    await run(org["w2_pc"], "alone")
    cases = {c["host"]: c for c in (await su.ok("detective.cases", {"include_noted": True}))["cases"]}
    assert cases["FIN-02"]["weight"] > cases["FIN-01"]["weight"]                                    # a program on its own, doing it: more telling
    row = await engine.db.pool.fetchrow("SELECT detail FROM file_events WHERE content_hash = 'h-hand'")
    assert row["detail"] == {"by": "hand", "front": "explorer.exe"}                                # and it is kept as history
    # an unknown stamp, or nonsense, is just not claimed
    await engine.file_index.ingest_event(org["w1_pc"], ev("create", "C:\\x\\a.txt", hash="h-x", witness={"by": "root", "front": "x"}))
    assert (await engine.db.pool.fetchrow("SELECT detail FROM file_events WHERE content_hash = 'h-x'"))["detail"] is None


@requires_db
async def test_the_service_stamps_what_its_file_watcher_reports(engine, org, tmp_path):
    from tests.test_worker_client import _start, _wait

    docs = tmp_path / "docs"
    docs.mkdir()
    svc = await _start(engine, tmp_path, "cid-w1", [str(docs)])
    try:
        async def alone():
            return 600.0, None

        svc.witness = Witness(alone)
        (docs / "a.txt").write_text("x", encoding="utf-8")
        assert await _wait(lambda: svc.watcher.events_reported >= 1)
        await asyncio.sleep(0.5)
        row = await engine.db.pool.fetchrow("SELECT detail FROM file_events WHERE path ILIKE '%a.txt' ORDER BY id DESC")
        assert row is not None and (row["detail"] or {}).get("by") == "alone"
    finally:
        await svc.stop()


def test_the_desktop_helper_answers_a_witness_request():
    from worker_client.helper import handle
    from worker_client.screenstream import RemoteInput

    r = handle({"cmd": "witness"}, RemoteInput())
    assert r["ok"] is True and "idle_s" in r and "front" in r


def test_a_drive_is_known_by_its_own_serial_not_by_the_letter_it_got_this_time():
    from worker_client.ossignals import diff_drives, volume_identity

    out = diff_drives({}, {"E:\\": "E:\\"}, lambda mount: {"serial": "ABCD-1234", "label": "BACKUP"})
    assert out == [("usb.inserted", {"device": "E:\\", "path": "E:\\", "serial": "ABCD-1234", "label": "BACKUP"})]
    assert diff_drives({"E:\\": "E:\\"}, {}, lambda mount: {"serial": "x"}) == [("usb.removed", {"device": "E:\\", "path": "E:\\"})]       # nothing to read once it is gone
    import os

    got = volume_identity("C:\\") if os.name == "nt" else {}
    assert got == {} or (len(got["serial"]) == 9 and got["serial"][4] == "-")


@requires_db
async def test_the_same_drive_in_another_letter_is_still_a_familiar_drive(engine, org, connect):
    from engine import detective

    pc = org["w1_pc"]
    for letter in ("E:\\", "F:\\", "G:\\", "E:\\"):
        await detective.on_signal(engine, pc, "usb.inserted", {"device": letter, "path": letter, "serial": "ABCD-1234", "label": "BACKUP"})
        await detective.on_signal(engine, pc, "usb.removed", {"device": letter, "path": letter})
    assert await engine.db.detective.device_uses(pc, "ABCD-1234") == 4 and await engine.db.detective.device_uses(pc, "E:\\") == 0
    await detective.on_signal(engine, pc, "usb.inserted", {"device": "H:\\", "path": "H:\\", "serial": "ABCD-1234", "label": "BACKUP"})
    assert detective._detector().ctx.device_uses(pc, "H:\\") == 4                               # four times before: familiar, whatever its letter
    story = detective._detector().mem[pc].recent[-1].phrase()
    assert story == r"plugged in a drive (BACKUP, H:\)"


async def test_the_program_that_touched_a_file_is_named_and_a_script_a_person_started_is_not_by_hand():
    async def hand():
        return 0.2, "explorer.exe"

    touched = {r"C:\Finance\q3.xlsx": "excel.exe", r"C:\Finance\a.zip": "powershell.exe"}
    w = Witness(hand, toucher=lambda path: touched.get(path, ""))
    assert await w.stamp(r"C:\Finance\q3.xlsx") == {"by": "hand", "front": "explorer.exe", "program": "excel.exe"}      # a person working in Excel
    assert await w.stamp(r"C:\Finance\a.zip") == {"by": "started", "program": "powershell.exe"}                          # a person's script did this one
    assert await w.stamp(r"C:\Finance\unseen.txt") == {"by": "hand", "front": "explorer.exe"}                            # nothing known about who: not claimed
    assert await w.stamp() == {"by": "hand", "front": "explorer.exe"}


def test_who_last_opened_a_file_is_remembered_from_the_file_trace_for_a_few_seconds(monkeypatch):
    from worker_client import etw

    watcher = etw.EtwWatcher(lambda kind, data: None)
    watcher.set_touch_roots([r"C:\Finance", "C:/Users/kojo/Documents"])
    monkeypatch.setattr(etw, "file_open", lambda data: (data.decode(), 0))
    monkeypatch.setattr(etw, "drive_path", lambda p, devices: p)
    names = {10: "Excel.exe", 11: "SearchIndexer.exe", 12: "powershell.exe"}
    monkeypatch.setattr(watcher, "_name_of", lambda pid: names.get(pid, ""))
    watcher._names.update(names)
    for pid, path in ((10, r"C:\Finance\q3.xlsx"), (11, r"C:\Finance\q3.xlsx"), (12, r"C:\Users\kojo\Documents\a.txt"), (10, r"D:\elsewhere\x.txt")):
        watcher._on_file(etw.EVENT_FILE_CREATE, pid, path.encode())
    assert watcher.who(r"C:\Finance\q3.xlsx") == "Excel.exe"                       # the indexer opens everything and says nothing about who made a change
    assert watcher.who("C:/Users/kojo/Documents/a.txt") == "powershell.exe"          # slashes and case do not matter
    assert watcher.who(r"D:\elsewhere\x.txt") == "" and watcher.who(r"C:\Finance\never.txt") == ""     # outside the watched folders, or never opened
    watcher.touches[r"c:\finance\q3.xlsx"] = ("Excel.exe", watcher.touches[r"c:\finance\q3.xlsx"][1] - 60)
    assert watcher.who(r"C:\Finance\q3.xlsx") == ""                                # a minute ago is not "what it did"
    for i in range(20500):
        watcher._on_file(etw.EVENT_FILE_CREATE, 10, rf"C:\Finance\f{i}.txt".encode())
    assert len(watcher.touches) <= 20000


async def test_a_real_program_that_writes_a_file_is_named_by_windows_own_trace(tmp_path):
    import os
    import subprocess
    import sys

    import pytest

    if sys.platform != "win32":
        pytest.skip("Windows' file trace")
    from worker_client.etw import EtwWatcher

    watcher = EtwWatcher(lambda kind, data: None)
    watcher.set_touch_roots([str(tmp_path)])
    await asyncio.to_thread(watcher.want_programs, True)                      # a short-lived program is named because it was seen starting
    started = await asyncio.to_thread(watcher.want_files, [])
    if not started:
        pytest.skip(f"this process may not start a trace session here: {watcher.errors.get('files')}")
    try:
        target = tmp_path / "made-by-cmd.txt"
        await asyncio.to_thread(subprocess.run, ["cmd.exe", "/c", f"echo hello> {target}"], check=True, env={**os.environ})
        for _ in range(40):
            if watcher.who(str(target)):
                break
            await asyncio.sleep(0.25)
        assert watcher.who(str(target)).lower() == "cmd.exe"
    finally:
        await asyncio.to_thread(watcher.stop)


@requires_db
async def test_the_program_that_made_a_change_travels_with_it_and_a_backup_program_is_taken_for_what_it_is(engine, org, connect):
    from tests.test_detective_engine import ev

    su = await connect("cid-su")

    async def drive_copy(pc, program):
        from engine import detective

        await detective.on_signal(engine, pc, "usb.inserted", {"device": "E:\\", "path": "E:\\", "serial": "AAAA-0001"})
        await engine.file_index.ingest_event(pc, ev("copy", r"E:\q3.zip", old_path=r"C:\Finance\q3.zip", hash=f"h-{program}", tag="restricted",
                                                    witness={"by": "alone", "program": program}))

    await drive_copy(org["w1_pc"], "robocopy.exe")
    await drive_copy(org["w2_pc"], "unknown-tool.exe")
    cases = {c["host"]: c for c in (await su.ok("detective.cases", {"include_noted": True}))["cases"]}
    assert cases["FIN-02"]["weight"] > cases["FIN-01"]["weight"] + 0.2                       # the same copy: a backup program is not what an unknown tool is
    row = await engine.db.pool.fetchrow("SELECT detail FROM file_events WHERE content_hash = 'h-robocopy.exe'")
    assert row["detail"] == {"by": "alone", "program": "robocopy.exe"}
