"""Hot and cold: what is being worked on goes first, and nothing cold is ever skipped."""

from __future__ import annotations

import os
from pathlib import Path

from common.heat import Heat
from worker_client import watcher as watcher_module
from worker_client.watcher import Watcher


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_a_thing_is_hot_when_something_happens_to_it_and_cools_by_itself():
    c = Clock()
    h = Heat(ttl=100, clock=c)
    assert h.temperature(r"C:\Work\a.docx") == 0.0 and not h.hot(r"C:\Work\a.docx")
    h.touch(r"C:\Work\a.docx")
    assert h.temperature("c:/work/A.DOCX") == 1.0 and h.hot(r"C:\Work\a.docx")                  # one spelling per file
    c.t += 50
    assert 0.45 < h.temperature(r"C:\Work\a.docx") < 0.55
    c.t += 100
    assert h.temperature(r"C:\Work\a.docx") == 0.0 and not h.hot(r"C:\Work\a.docx")
    assert h.forget_cold() >= 1


def test_the_folders_above_a_hot_file_are_warm_so_a_walk_finds_it_first():
    c = Clock()
    h = Heat(ttl=100, clock=c)
    h.touch(r"C:\Data\projects\atlas\specs\v2\plan.docx")
    for folder in (r"C:\Data\projects\atlas\specs\v2", r"C:\Data\projects\atlas", r"C:\Data", "C:"):
        assert 0.4 < h.temperature(folder) < 0.6, folder
    assert h.temperature(r"C:\Data\projects\other") == 0.0


def test_hottest_first_and_the_cold_keep_their_order():
    c = Clock()
    h = Heat(ttl=100, clock=c)
    h.touch("pc:3")
    c.t += 10
    h.touch("pc:9")
    got = h.hottest(["pc:1", "pc:3", "pc:2", "pc:9", "pc:4"])
    assert got == ["pc:9", "pc:3", "pc:1", "pc:2", "pc:4"]                                         # cold ones: nobody skipped, nobody reordered


def test_it_cannot_grow_without_bound():
    h = Heat(ttl=1000, cap=500)
    for i in range(20000):
        h.touch(f"C:/x/{i % 400}/f{i}.txt")
    assert len(h) <= 500
    assert h.hot_keys(10)


async def _sweep(tmp_path: Path, hot: str | None, *, hashes: dict[str, str] | None = None):
    root = tmp_path / "tree"
    for d in range(12):
        for f in range(20):
            p = root / f"dir{d:02d}" / "sub" / f"f{f}.txt"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"{d}-{f}", encoding="utf-8")
    sent: list[list[str]] = []

    async def report(kind, payload):
        if kind == "index.sweep_batch":
            sent.append([e["path"] for e in payload["entries"]])
        return {}

    w = Watcher([str(root)], report, state_path=tmp_path / "snap.db")
    if hot:
        w.touch(str(root / hot))
    n = await w.sweep(force=True)
    return w, sent, n, root


async def test_a_sweep_reaches_the_file_in_use_first_wherever_it_is_and_still_reaches_everything(tmp_path: Path):
    w, sent, n, _root = await _sweep(tmp_path, os.path.join("dir11", "sub", "f19.txt"))
    try:
        flat = [p for batch in sent for p in batch]
        assert flat[0].endswith(os.path.join("dir11", "sub", "f19.txt"))                           # the last folder and last file on disk, first in the order
        assert len(flat) == len(set(flat)) == n == 12 * 20                                         # ... and nobody cold was left out or repeated
    finally:
        await w.stop()


async def test_a_sweep_does_not_read_every_cold_file_again_to_find_nothing_changed(tmp_path: Path, monkeypatch):
    w, sent, _n, root = await _sweep(tmp_path, None)
    try:
        # the Engine took everything: the snapshot knows each file, with its hash
        for batch in sent:
            await __import__("asyncio").to_thread(w._remember_swept, [{"path": p, "hash": "h-" + os.path.basename(p)} for p in batch], 1)
        reads: list[str] = []
        real = watcher_module.hash_file
        monkeypatch.setattr(watcher_module, "hash_file", lambda p, limit: reads.append(str(p)) or real(p, limit))
        changed = root / "dir03" / "sub" / "f4.txt"
        changed.write_text("different and longer", encoding="utf-8")                              # one file changes
        sent.clear()
        again = await w.sweep(force=True)
        assert again == 12 * 20 and len(reads) == 1 and reads[0].endswith(os.path.join("dir03", "sub", "f4.txt"))
    finally:
        await w.stop()


async def test_programs_in_use_lead_what_is_reported_and_an_unknown_one_brings_the_installed_list_forward():
    import asyncio

    from worker_client import inventory

    sent: list[dict] = []

    async def report(kind, payload):
        sent.append(payload)
        return {}

    inv = inventory.Inventory(report)
    rows = [{"name": f"App{i:03d}"} for i in range(700)]
    await inv.send("running", lambda: rows)
    assert len(sent[-1]["running"]) == inventory.MAX_RUNNING                                         # a worst case is clamped
    inv.touch("App650.exe")
    inv.touch("App333")
    await inv.send("running", lambda: rows)
    assert [r["name"] for r in sent[-1]["running"][:2]] == ["App333", "App650"] or [r["name"] for r in sent[-1]["running"][:2]] == ["App650", "App333"]
    # a program the installed list has never heard of just ran: it is read again soon, not in six hours
    await inv.send("installed", lambda: [{"name": "Known", "command": None}])
    assert not inv._again.is_set()
    inv.touch("known.exe")
    assert not inv._again.is_set()
    inv.touch("StrangerProgram.exe")
    assert inv._again.is_set()
    inv._again.clear()
    inv.touch("AnotherStranger.exe")
    assert not inv._again.is_set()                                                                   # (not again within the minute and a half: a flood of new programs is one look)
    await asyncio.sleep(0)
