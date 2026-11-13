"""What is written to an external drive (worker_client/drivewatch.py). Found on real hardware, 5 Nov 2026: a USB hard disk is not "removable" to Windows, and nothing followed a
drive's contents, so a file copied out was never seen by anyone. Only made-up events had ever reached Detective's "copied to a drive"."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import pytest

from engine import detective
from tests.conftest import requires_db
from worker_client import ossignals
from worker_client.drivewatch import DriveWatch


async def _watching(tmp_path: Path, sent: list[dict], **kw) -> DriveWatch:
    async def report(type_, payload):
        sent.append(payload["event"])

    w = DriveWatch(report, hash_limit=1 << 20, find=lambda: [str(tmp_path) + os.sep], look_every=0.1, settled=0.3, **kw)
    await w.start()
    for _ in range(50):
        if w.observers:
            break
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.3)
    return w


async def _until(cond, seconds: float = 5.0) -> bool:
    for _ in range(int(seconds / 0.05)):
        if cond():
            return True
        await asyncio.sleep(0.05)
    return False


async def test_a_file_written_to_a_drive_is_told_once_finished_with_its_hash_and_its_drive(tmp_path: Path):
    sent: list[dict] = []
    w = await _watching(tmp_path, sent)
    try:
        (tmp_path / "secrets.zip").write_bytes(b"first part")
        await asyncio.sleep(0.1)
        (tmp_path / "secrets.zip").write_bytes(b"first part and the rest")
        assert await _until(lambda: sent)
        await asyncio.sleep(0.6)
        assert len(sent) == 1 and sent[0]["op"] == "create" and sent[0]["name"] == "secrets.zip" and sent[0]["hash"]
        assert sent[0]["drive"] == str(tmp_path) + os.sep
    finally:
        await w.stop()


async def test_what_was_on_the_drive_already_is_never_read_or_told(tmp_path: Path):
    (tmp_path / "holiday.jpg").write_bytes(b"old")
    os.utime(tmp_path / "holiday.jpg", (time.time() - 86400, time.time() - 86400))
    sent: list[dict] = []
    w = await _watching(tmp_path, sent)
    try:
        await asyncio.sleep(0.7)
        assert sent == []
        w.touched("modified", str(tmp_path / "holiday.jpg"))           # Windows reports a read as a change: the file says it did not change
        await asyncio.sleep(0.6)
        assert sent == []
    finally:
        await w.stop()


async def test_a_copy_keeps_its_old_date_and_is_still_seen(tmp_path: Path):
    sent: list[dict] = []
    w = await _watching(tmp_path, sent)
    try:
        p = tmp_path / "payroll.xlsx"
        p.write_bytes(b"figures")
        os.utime(p, (time.time() - 86400 * 30, time.time() - 86400 * 30))            # Windows keeps a file's date when it copies it
        assert await _until(lambda: sent) and sent[0]["name"] == "payroll.xlsx"
    finally:
        await w.stop()


async def test_windows_own_bookkeeping_on_a_drive_is_left_alone(tmp_path: Path):
    sent: list[dict] = []
    w = await _watching(tmp_path, sent)
    try:
        w.touched("created", str(tmp_path / "System Volume Information" / "x.dat"))
        w.touched("created", str(tmp_path / "$RECYCLE.BIN" / "y.dat"))
        assert w.waiting == {}
    finally:
        await w.stop()


async def test_a_drive_pulled_out_is_let_go_and_a_file_gone_again_is_not_told(tmp_path: Path):
    sent: list[dict] = []
    there = [str(tmp_path) + os.sep]

    async def report(type_, payload):
        sent.append(payload["event"])

    w = DriveWatch(report, hash_limit=1 << 20, find=lambda: list(there), look_every=0.1, settled=0.2)
    await w.start()
    try:
        assert await _until(lambda: w.observers)
        p = tmp_path / "~temp.tmp"
        p.write_bytes(b"x")
        p.unlink()
        await asyncio.sleep(0.5)
        assert sent == []
        there.clear()
        assert await _until(lambda: not w.observers)
    finally:
        await w.stop()


@pytest.mark.parametrize("opts,bus,seen", [("rw,removable", None, True), ("rw,fixed", 7, True), ("rw,fixed", 11, False), ("rw,fixed", None, False), ("cdrom", None, False)])
def test_a_usb_hard_disk_counts_though_windows_calls_it_fixed(monkeypatch, opts, bus, seen):
    class Part:
        mountpoint, device = "K:\\", "K:\\"

    Part.opts = opts

    class Ps:
        @staticmethod
        def disk_partitions(all=False):
            return [Part]

    monkeypatch.setattr(ossignals, "_psutil", lambda: Ps)
    monkeypatch.setattr(ossignals, "bus_type", lambda mount: bus)
    assert ossignals.drives() == ({"K:\\": "K:\\"} if seen else {})


def test_the_drive_windows_runs_from_is_never_external(monkeypatch):
    class Part:
        mountpoint, device, opts = "C:\\", "C:\\", "rw,fixed"

    class Ps:
        @staticmethod
        def disk_partitions(all=False):
            return [Part]

    monkeypatch.setattr(ossignals, "_psutil", lambda: Ps)
    monkeypatch.setattr(ossignals, "bus_type", lambda mount: 7)
    monkeypatch.setenv("SystemDrive", "C:")
    assert ossignals.drives() == {}


@pytest.mark.skipif(os.name != "nt", reason="asks Windows")
def test_windows_says_how_its_own_disk_is_connected():
    assert ossignals.bus_type(os.environ.get("SystemDrive", "C:") + "\\") not in (None, 7)


@requires_db
async def test_a_file_put_on_a_drive_that_was_plugged_in_before_the_worker_started_is_seen_going_out(engine, org, connect):
    """No `usb.inserted` ever came for it: the event itself says which drive."""
    a1 = await connect("cid-a1")
    fi = engine.file_index
    for i in range(3):
        await fi.ingest_event(org["w1_pc"], {"op": "create", "path": f"K:\\out\\file{i}.zip", "hash": f"h-{i}", "drive": "K:\\", "witness": {"by": "unknown"}})
    await asyncio.sleep(0.2)
    mem = await detective.memory(org["w1_pc"])
    assert "K:\\" in mem.devices
    cases = (await a1.ok("detective.cases", {"include_noted": True}))["cases"]
    assert cases
    found = [await a1.ok("detective.case", {"case_id": c["id"]}) for c in cases]
    assert "to_drive" in str(found)


async def test_a_file_taken_off_a_drive_is_told_as_gone_so_the_index_does_not_keep_it(tmp_path: Path):
    """Found 9 Nov 2026: files deleted from a stick stayed in the index, and marking the original again raised issues for copies that no longer existed."""
    sent: list[dict] = []
    w = await _watching(tmp_path, sent)
    try:
        p = tmp_path / "pay.txt"
        p.write_bytes(b"figures")
        assert await _until(lambda: any(e["op"] == "create" for e in sent))
        p.unlink()
        assert await _until(lambda: any(e["op"] == "delete" for e in sent))
        gone = next(e for e in sent if e["op"] == "delete")
        assert gone["path"] == str(p) and gone["drive"] == str(tmp_path) + os.sep
    finally:
        await w.stop()


@requires_db
async def test_taking_a_file_off_a_drive_updates_the_index_and_is_not_read_as_covering_up(engine, org, connect):
    fi = engine.file_index
    await fi.ingest_event(org["w1_pc"], {"op": "create", "path": "K:\\out\\pay.txt", "hash": "h-pay", "drive": "K:\\"})
    await fi.ingest_event(org["w1_pc"], {"op": "delete", "path": "K:\\out\\pay.txt", "drive": "K:\\"})
    await asyncio.sleep(0.2)
    assert (await engine.db.file_index.by_path(org["w1_pc"], "K:\\out\\pay.txt", present_only=True)) is None
    assert not any(s.verb == "deleted" for s in (await detective.memory(org["w1_pc"])).since(0, "deleted"))


async def test_who_was_at_the_keyboard_is_asked_when_the_file_appears_not_when_it_is_told(tmp_path: Path):
    """Hands-on, 10 Nov 2026: a paste to a pendrive read as "a program the person started", because the stamp was taken after the file had been quiet."""
    sent: list[dict] = []
    hands = {"by": "hand", "front": "explorer.exe"}

    async def stamp(path: str) -> dict:
        return dict(hands)

    w = await _watching(tmp_path, sent, stamp=stamp)
    try:
        (tmp_path / "payroll.txt").write_bytes(b"salaries")
        await asyncio.sleep(0.1)
        hands.update(by="started", front="")           # the person lets go of the mouse while the copy settles
        assert await _until(lambda: sent)
        assert sent[0]["witness"] == {"by": "hand", "front": "explorer.exe"} and sent[0]["at"] <= time.time()
    finally:
        await w.stop()
