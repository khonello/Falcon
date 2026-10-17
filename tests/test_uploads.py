"""What a program sends out over the network: counted by volume only, and read by Detective as the way out when it follows packing."""

from __future__ import annotations

import asyncio
import socket
import struct
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from detective_scenarios import SCENARIOS, play

from tests.conftest import requires_db
from worker_client import etw
from worker_client.etw import EVENT_TCP_SEND4, EVENT_TCP_SEND6, EtwWatcher, UploadMeter, tcp_send


def v4(pid: int, size: int, addr: str, port: int = 443) -> bytes:
    return struct.pack("<II", pid, size) + socket.inet_aton(addr) + socket.inet_aton("10.0.0.5") + struct.pack(">HH", port, 51000) + b"\x00" * 16


def v6(pid: int, size: int, addr: str, port: int = 443) -> bytes:
    return struct.pack("<II", pid, size) + socket.inet_pton(socket.AF_INET6, addr) + socket.inet_pton(socket.AF_INET6, "fd00::5") + struct.pack(">HH", port, 51000) + b"\x00" * 16


def test_a_send_event_is_read_for_the_program_the_size_and_where_to():
    assert tcp_send(EVENT_TCP_SEND4, v4(4688, 30303, "93.184.216.34")) == (4688, 30303, "93.184.216.34", 443)
    assert tcp_send(EVENT_TCP_SEND6, v6(12, 99, "2606:2800:220:1::1", 8443)) == (12, 99, "2606:2800:220:1::1", 8443)
    assert tcp_send(EVENT_TCP_SEND4, b"short") is None and tcp_send(99, v4(1, 1, "1.1.1.1")) is None


def test_a_lot_sent_out_in_a_minute_is_said_once_and_the_office_network_is_not_out():
    m = UploadMeter(threshold=100, window=60, cooldown=600)
    assert m.feed(50, 60, "93.184.216.34", 0.0) is None
    said = m.feed(50, 60, "93.184.216.34", 10.0)
    assert said == {"bytes": 120, "to": "93.184.216.34", "destinations": 1, "seconds": 60}
    assert m.feed(50, 500, "93.184.216.34", 20.0) is None                                          # told already: a long upload is one signal
    assert m.feed(50, 500, "93.184.216.34", 700.0) is not None                                     # ... until the cooldown has passed
    for private in ("10.1.2.3", "192.168.0.9", "172.16.4.4", "127.0.0.1", "169.254.1.1", "::1", "fd00::9"):
        assert UploadMeter(threshold=1).feed(60, 10_000, private, 0.0) is None, private
    assert UploadMeter(threshold=1).feed(4, 10_000, "93.184.216.34", 0.0) is None                  # pid 4 is the machine's file sharing
    slow = UploadMeter(threshold=100, window=60)
    assert slow.feed(70, 60, "93.184.216.34", 0.0) is None and slow.feed(70, 60, "93.184.216.34", 100.0) is None      # spread over more than a minute
    two = UploadMeter(threshold=100)
    assert two.feed(1, 60, "93.184.216.34", 0.0) is None and two.feed(2, 60, "93.184.216.35", 1.0) is None            # each program on its own


def test_the_watcher_names_the_program_and_never_itself():
    seen = []
    w = EtwWatcher(lambda kind, data: seen.append((kind, data)))
    w.meter = UploadMeter(threshold=100)
    w._names[777] = "python.exe"
    w._on_network(EVENT_TCP_SEND4, 4, v4(777, 150, "93.184.216.34"))
    w._on_network(EVENT_TCP_SEND4, 4, v4(w._me, 5000, "93.184.216.34"))
    w._on_network(11, 4, v4(777, 5000, "93.184.216.35"))                                           # received, not sent
    assert seen == [("network.upload", {"process": "python.exe", "bytes": 150, "to": "93.184.216.34", "destinations": 1, "seconds": 60})]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows' network trace")
async def test_a_real_program_sending_a_lot_is_named_by_windows_own_trace():
    seen = []
    watcher = EtwWatcher(lambda kind, data: seen.append((kind, data)))
    watcher.meter = UploadMeter(threshold=2_000_000, public_only=False, cooldown=1)                  # (this machine talking to itself stands in for "out")
    watcher._me = -1                                                                                # (this test is the program doing the sending)
    if not await asyncio.to_thread(watcher.want_network, True):
        pytest.skip(f"this process may not start a trace session here: {watcher.errors.get('network')}")
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def serve():
        c, _ = srv.accept()
        while c.recv(1 << 20):
            pass

    threading.Thread(target=serve, daemon=True).start()
    try:
        c = socket.create_connection(("127.0.0.1", srv.getsockname()[1]))
        c.sendall(b"x" * 6_000_000)
        c.close()
        for _ in range(40):
            if seen:
                break
            await asyncio.sleep(0.25)
        assert seen and seen[0][0] == "network.upload" and seen[0][1]["process"].lower().startswith("python") and seen[0][1]["bytes"] >= 2_000_000
    finally:
        await asyncio.to_thread(watcher.stop)
    assert etw.NETWORK_PROVIDER


def test_sending_out_after_packing_restricted_files_is_the_way_out_and_a_sync_client_is_not():
    det, updates = play(SCENARIOS["upload_after_packing"]())
    (case,) = det.open_cases()
    assert "exfiltration" in case.behaviours and case.level in ("case", "urgent") and any(u.raised for u in updates)
    assert any("180 MB out over the network" in line for line in case.story())
    labels = {n["label"] for n in case.graph()["nodes"]}
    assert any("180 MB sent out by python.exe" in x for x in labels)
    det2, up2 = play(SCENARIOS["sync_client_upload"]())
    assert all(c.level in ("quiet", "noted") for c in det2.cases) and not any(u.raised for u in up2)       # a sync client "moves files for a living": lowered out of sight


def test_a_big_upload_with_nothing_before_it_is_remembered_but_is_not_a_case():
    from common.detective import Context, Detective, Sig

    det = Detective(Context())
    det.feed(Sig(1_800_000_000.0, 1, "uploaded", program="python.exe", info={"bytes": 80_000_000, "to": "203.0.113.9", "destinations": 1, "seconds": 60}))
    assert all(c.level in ("quiet", "noted") for c in det.cases)


@requires_db
async def test_the_engine_always_asks_for_uploads_and_reads_one_after_packing_as_taking_out(engine, org, connect):
    from engine import detective
    from engine.control.events import interest_for_pc

    assert "network.upload" in await interest_for_pc(engine, org["w1_pc"])
    su = await connect("cid-su")
    pc = org["w1_pc"]
    fi = engine.file_index
    for i in range(10):
        await fi.ingest_event(pc, {"op": "create", "path": f"C:\\Finance\\Payroll\\p{i}.xlsx", "name": f"p{i}.xlsx", "hash": f"h-{i}", "resource_tag": "restricted"})
        await fi.ingest_event(pc, {"op": "copy", "path": f"C:\\Users\\kojo\\Staging\\p{i}.xlsx", "old_path": f"C:\\Finance\\Payroll\\p{i}.xlsx", "name": f"p{i}.xlsx",
                                   "hash": f"h-{i}", "resource_tag": "restricted"})
    await fi.ingest_event(pc, {"op": "create", "path": "C:\\Users\\kojo\\Staging\\q3.zip", "name": "q3.zip", "hash": "h-zip"})
    await detective.on_signal(engine, pc, "network.upload", {"process": "python.exe", "bytes": 180_000_000, "to": "203.0.113.9", "destinations": 1, "seconds": 60})
    case = (await su.ok("detective.cases", {"include_noted": True}))["cases"][0]
    assert "exfiltration" in case["behaviours"] and any("180 MB" in line for line in case["story"])
