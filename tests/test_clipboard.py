"""A picture put on the clipboard (PrintScreen, the Snipping Tool) is a screenshot without a tool: seen by its shape, read by Detective as capture."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from detective_scenarios import SCENARIOS, play

from tests.conftest import requires_db
from worker_client import clipboard
from worker_client.clipboard import ClipboardWatcher, kind_of

SCREEN = {"w": 1920, "h": 1080}


def test_a_picture_the_size_of_the_screen_is_the_screen_and_a_smaller_one_is_a_region():
    assert kind_of({"w": 1920, "h": 1080}, SCREEN) == "screen"
    assert kind_of({"w": 1800, "h": 1000}, SCREEN) == "screen"
    assert kind_of({"w": 640, "h": 480}, SCREEN) == "region"
    assert kind_of({"w": 1920, "h": 200}, SCREEN) == "region"                                      # as wide as the screen is not the screen
    assert kind_of({"w": 100, "h": 100}, {}) == "region"                                           # no screen size known: never claimed to be the screen


async def test_the_watcher_reports_a_picture_once_and_only_when_the_clipboard_changed():
    looks = iter([
        {"seq": 10, "image": None, "screen": SCREEN},                                              # the baseline
        {"seq": 10, "image": None, "screen": SCREEN},                                              # nothing new
        {"seq": 11, "image": None, "screen": SCREEN},                                              # text copied: not a picture
        {"seq": 12, "image": {"w": 1920, "h": 1080}, "screen": SCREEN},                            # PrintScreen
        {"seq": 12, "image": {"w": 1920, "h": 1080}, "screen": SCREEN},                            # the same picture still there
        {"seq": 13, "image": {"w": 300, "h": 200}, "screen": SCREEN},                              # another, straight away: the same moment
        None,                                                                                      # a locked desktop
    ])
    now = [100.0]

    async def source():
        return next(looks)

    async def front():
        return "excel.exe"

    w = ClipboardWatcher(None, source, front=front, clock=lambda: now[0])
    assert await w.poll() is None and await w.poll() is None and await w.poll() is None
    assert await w.poll() == {"kind": "screen", "w": 1920, "h": 1080, "process": "excel.exe"}
    assert await w.poll() is None
    assert await w.poll() is None                                                                  # (3 s have not passed)
    assert await w.poll() is None


async def test_the_watcher_forgets_its_baseline_when_nobody_asks_and_only_reports_while_asked():
    sent = []

    async def report(kind, payload):
        sent.append(payload["data"]["kind"])

    seqs = iter(range(1, 100))

    async def source():
        n = next(seqs)
        return {"seq": n, "image": {"w": 1920, "h": 1080}, "screen": SCREEN}

    asked = [False]
    w = ClipboardWatcher(report, source, wanted=lambda: asked[0], interval=0.01)
    w.start()
    import asyncio

    await asyncio.sleep(0.15)
    assert sent == []                                                                              # nobody wants it: nothing is even looked at
    asked[0] = True
    await asyncio.sleep(0.2)
    await w.stop()
    assert sent and set(sent) == {"screen"}


@pytest.mark.skipif(sys.platform != "win32", reason="the clipboard is Windows' here")
def test_the_real_clipboard_can_be_looked_at_and_a_picture_on_it_is_seen_by_its_shape():
    got = clipboard.look()
    assert got is not None and got["screen"]["w"] > 0 and got["screen"]["h"] > 0 and "image" in got
    import ctypes
    import struct
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    w, h = 64, 32
    header = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, 0, 0, 0, 0, 0)
    pixels = b"\x00" * (((w * 3 + 3) & ~3) * h)
    data = header + pixels
    if not user32.OpenClipboard(None):
        pytest.skip("the clipboard is in use")
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(0x0042, len(data))                                           # GHND
        ptr = kernel32.GlobalLock(handle)
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(handle)
        user32.SetClipboardData(clipboard.CF_DIB, handle)
    finally:
        user32.CloseClipboard()
    after = clipboard.look()
    if after["seq"] == 0:
        pytest.skip("this desktop cannot be asked (no interactive session)")
    assert after["seq"] != got["seq"] and after["image"] == {"w": w, "h": h}                       # its shape, nothing more


def test_the_desktop_helper_answers_a_clipboard_request():
    from worker_client.helper import handle
    from worker_client.screenstream import RemoteInput

    r = handle({"cmd": "clipboard"}, RemoteInput())
    assert (r["ok"] is True and "seq" in r and "front" in r and "image" in r) or r["ok"] is False


def test_pressing_print_screen_over_restricted_files_is_capture_and_a_picture_over_nothing_is_not():
    det, updates = play(SCENARIOS["printscreens"]())
    (case,) = det.open_cases()
    assert case.behaviours == {"capture"} and case.intent == "Copying what is on screen" and case.level in ("case", "urgent")
    assert any("picture of the whole screen" in line for line in case.story())
    assert any(u.raised for u in updates)
    labels = {n["label"] for n in case.graph()["nodes"]}
    assert any("picture of the screen" in x for x in labels)
    det2, _ = play(SCENARIOS["printscreen_of_nothing"]())
    assert all(c.level == "quiet" for c in det2.cases)


def test_a_picture_taken_by_a_tool_that_was_just_started_is_one_reading_not_two():
    from common.detective import Context, Detective, Sig

    det = Detective(Context())
    t = 1_800_000_000.0
    det.feed(Sig(t, 1, "opened", "C:\\Finance\\p.xlsx", thing="h", by="hand", program="excel.exe", tags=frozenset({"restricted"})))
    det.feed(Sig(t + 10, 1, "launched", program="snippingtool.exe", by="hand"))
    det.feed(Sig(t + 20, 1, "captured", by="hand", program="snippingtool.exe", info={"kind": "region"}))
    graphs = [f.graph for c in det.cases for f in c.findings]
    assert graphs.count("capture_tool") == 1 and "clipboard_picture" not in graphs


@requires_db
async def test_the_engine_always_asks_for_pictures_and_reads_one_as_capture(engine, org, connect):
    from engine.control.events import interest_for_pc

    assert "screen.captured" in await interest_for_pc(engine, org["w1_pc"])
    su, w1 = await connect("cid-su"), await connect("cid-w1")
    from engine import detective

    fi = engine.file_index
    await fi.ingest_event(org["w1_pc"], {"op": "create", "path": "C:\\Finance\\Payroll\\p.xlsx", "name": "p.xlsx", "hash": "h-p", "resource_tag": "restricted"})
    for _ in range(3):
        await detective.on_signal(engine, org["w1_pc"], "screen.captured", {"kind": "screen", "process": "excel.exe"})
    await w1.ok("control.signal", {"type": "screen.captured", "data": {"kind": "screen", "process": "excel.exe"}})
    cases = (await su.ok("detective.cases", {"include_noted": True}))["cases"]
    assert cases and "capture" in cases[0]["behaviours"]


@requires_db
async def test_a_connected_worker_looks_at_the_clipboard_only_because_the_engine_asked_and_tells_the_engine_when_a_picture_arrives(engine, org, tmp_path, monkeypatch):
    import asyncio

    from engine import detective
    from tests.test_worker_client import _start

    heard = []
    real = detective.on_signal

    async def spy(eng, pc, etype, data):
        heard.append((etype, data))
        await real(eng, pc, etype, data)

    monkeypatch.setattr(detective, "on_signal", spy)
    svc = await _start(engine, tmp_path, "cid-w1", [str(tmp_path)])
    try:
        assert svc.ossignals.interest.get("screen.captured") and svc._wants_clipboard()                  # the Engine asked, on connect
        looks = iter([{"seq": 5, "image": None, "screen": SCREEN}, {"seq": 6, "image": {"w": 1920, "h": 1080}, "screen": SCREEN}] + [{"seq": 6, "image": None, "screen": SCREEN}] * 400)

        async def source():
            return next(looks)

        await svc._clipboard_watch().stop()
        svc._clipboard = ClipboardWatcher(svc.call, source, wanted=svc._wants_clipboard, interval=0.05)
        svc._clipboard.start()
        for _ in range(60):
            if any(t == "screen.captured" for t, _ in heard):
                break
            await asyncio.sleep(0.1)
        assert [d for t, d in heard if t == "screen.captured"] == [{"kind": "screen", "w": 1920, "h": 1080}]
    finally:
        await svc.stop()
