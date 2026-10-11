"""The console's fleet, a machine's page, and the audit trail as events (ENGINE-CONCEPT-NEEDS WP1)."""

from __future__ import annotations

import asyncio
import csv
import io
from datetime import datetime, timedelta, timezone

from tests.conftest import requires_db

pytestmark = requires_db


async def test_the_fleet_shows_each_machine_with_what_it_said_and_who_is_in_it(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    await engine.db.updates.approve_version("1.4.2", org["su"])
    w1 = await connect("cid-w1", hello={"version": "1.4.2", "os": "Windows 11 Pro", "started_at": "2026-10-05T07:00:00+00:00"})
    await connect("cid-w2", hello={"version": "1.4.1", "os": "Windows 10"})
    await w1.ok("control.metrics", {"cpu": 31, "memory": 52, "idle_s": 4, "disk": 88.5, "net_kbps": 120.0,
                                    "foreground": {"program": "EXCEL.EXE", "title": "budget.xlsx - Excel"}})

    fleet = await a1.ok("machines.list")
    by = {m["hostname"]: m for m in fleet["machines"]}
    assert set(by) == {"FIN-ADM", "FIN-01", "FIN-02"}                      # an Admin sees only their department
    assert fleet["current_version"] == "1.4.2" and fleet["summary"]["behind"] == 1 and fleet["summary"]["machines"] == 3
    m = by["FIN-01"]
    assert m["online"] and m["version"] == "1.4.2" and m["os"] == "Windows 11 Pro" and m["ip"] == "127.0.0.1"
    assert m["health"] == "healthy" and m["behind"] is False and m["user"]            # its own person is in it
    assert (m["cpu"], m["disk"]) == (31.0, 88.5) and m["foreground"]["program"] == "EXCEL.EXE"
    assert by["FIN-02"]["behind"] is True and by["FIN-ADM"]["held_by"] is None
    assert len((await su.ok("machines.list"))["machines"]) == 5                       # the Super User sees every machine
    assert [x["hostname"] for x in (await su.ok("machines.list", {"department_id": org["hr"]}))["machines"]] == ["HR-ADM"]
    assert [x["hostname"] for x in (await a2.ok("machines.list"))["machines"]] == ["HR-ADM"]

    # a machine that is not connected is offline, whatever else is true of it
    await engine.db.pool.execute("UPDATE pcs SET last_seen_at = now() - interval '3 hours' WHERE id = $1", org["w2_pc"])
    await (await connect("cid-w2")).close()
    await asyncio.sleep(0.2)

    # an Admin inside a machine: it is held, and by whom, and the owner is not "using" it
    entered = (await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True}))["session"]
    held = {x["hostname"]: x for x in (await a1.ok("machines.list"))["machines"]}["FIN-01"]
    assert held["held_via"] == "admin" and held["held_by_you"] is True and held["held_by"] and held["user"] is None
    assert held["held_since"] and held["session_id"] == entered["session_id"]
    assert {x["hostname"]: x for x in (await su.ok("machines.list"))["machines"]}["FIN-01"]["held_by_you"] is False


async def test_a_machines_page_has_its_series_processes_sessions_files_and_events(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    now = datetime.now(timezone.utc)
    for i, (cpu, disk) in enumerate([(10, 70), (30, 71), (50, 72)]):
        await engine.db.pool.execute(
            "INSERT INTO metric_samples (pc_id, sampled_at, cpu, memory, idle_s, disk, net_kbps) VALUES ($1, $2, $3, 40, 1, $4, $5)",
            org["w1_pc"], now - timedelta(minutes=50 - i * 10), cpu, disk, 5.0 * i)
    await w1.ok("control.inventory", {"processes": [{"pid": 4408, "name": "explorer.exe", "cpu": 1.1, "memory_mb": 96, "user": "Ama"},
                                                    {"pid": 6120, "name": "EXCEL.EXE", "cpu": 18.2, "memory_mb": 412, "user": "Ama"},
                                                    {"pid": "x", "name": "junk"}, {"name": "nopid"}]})
    await w1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/a.docx", "hash": "H"}})
    await w1.ok("index.event", {"event": {"op": "create", "path": "C:/Users/ama/notes.txt", "hash": "N"}})
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})

    page = await a1.ok("machines.get", {"pc_id": org["w1_pc"], "range": "1h"})
    assert page["machine"]["hostname"] == "FIN-01" and page["range"] == "1h"
    assert [p["v"] for p in page["series"]["cpu"]] == [10.0, 30.0, 50.0] and page["series"]["disk"][0]["v"] == 70.0
    assert [p["v"] for p in page["series"]["net_kbps"]] == [0.0, 5.0, 10.0]
    assert [p["name"] for p in page["processes"]["items"]] == ["explorer.exe", "EXCEL.EXE"]       # junk dropped, order kept
    assert {s["type"] for s in page["sessions"]} >= {"you"} and page["sessions"][0]["ended_at"] is None
    assert page["files"]["indexed"] == 2 and sum(page["files"]["by_tag"].values()) == 2 and page["files"]["last_indexed_at"]
    assert any(e["kind"] == "session" and "Entered FIN-01" in e["what"] for e in page["events"])
    assert await a1.err("machines.get", {"pc_id": org["w1_pc"], "range": "3d"}) == "invalid"
    assert await a2.err("machines.get", {"pc_id": org["w1_pc"]}) == "forbidden"                # another department's machine
    assert await a1.err("machines.get", {"pc_id": 999}) == "not_found"
    assert await w1.err("machines.get", {"pc_id": org["w1_pc"]}) == "forbidden"


async def test_the_audit_trail_is_events_with_a_kind_a_sentence_a_machine_and_a_scope(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    await connect("cid-w1")
    await su.drain_pushes()
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
    await a2.ok("assistance.my_admins")
    await su.ok("reports.routing_set", {"category": "flow_failure", "department_ids": [org["fin"]]})

    evs = (await su.ok("audit.events", {"kinds": ["session"]}))["events"]
    entered = next(e for e in evs if "Entered FIN-01" in e["what"])
    assert entered["kind"] == "session" and entered["host"] == "FIN-01" and entered["pc_id"] == org["w1_pc"] and entered["actor"]
    assert {e["kind"] for e in (await su.ok("audit.events", {"kinds": ["report"]}))["events"]} == {"report"}
    assert await su.err("audit.events", {"kinds": ["nonsense"]}) == "invalid"
    on_machine = (await su.ok("audit.events", {"pc_id": org["w1_pc"]}))["events"]
    assert on_machine and all(e["pc_id"] == org["w1_pc"] for e in on_machine)

    # an Admin reads only what concerns their own department
    fin = (await a1.ok("audit.events", {}))["events"]
    assert any("Entered FIN-01" in e["what"] for e in fin)
    assert all(e["host"] in (None, "FIN-ADM", "FIN-01", "FIN-02") for e in fin)
    assert not any(e["action_type"].startswith("report_routing") for e in await _only(a2, "report"))   # routed to Finance, not HR
    page = await su.ok("audit.events", {"limit": 2})
    assert len(page["events"]) == 2 and page["more"] is True
    older = await su.ok("audit.events", {"limit": 2, "before_id": page["events"][-1]["id"]})
    assert older["events"][0]["id"] < page["events"][-1]["id"]

    # counts, per kind and over time
    summary = await su.ok("audit.summary", {"bucket_minutes": 60})
    assert summary["total"] >= 4 and summary["by_kind"]["session"] >= 1 and summary["kept_days"] == 90
    assert summary["actors"] >= 2 and sum(sum(b["counts"].values()) for b in summary["series"]) == summary["total"]
    assert (await a2.ok("audit.summary"))["by_kind"].get("report", 0) == 0

    # export: the same rows as CSV, and exporting is itself recorded
    out = await su.ok("audit.export", {"kinds": ["session"]})
    rows_ = list(csv.reader(io.StringIO(out["csv"])))
    assert rows_[0] == ["when", "kind", "who", "what", "machine"] and out["rows"] == len(rows_) - 1 >= 1
    assert out["filename"].startswith("falcon-audit-") and any("FIN-01" in r[4] for r in rows_[1:])
    assert any(e["action_type"] == "audit.exported" for e in (await su.ok("audit.events", {"kinds": ["admin"]}))["events"])


async def _only(client, kind):
    return (await client.ok("audit.events", {"kinds": [kind]}))["events"]


async def test_each_event_is_pushed_live_to_those_who_may_see_it_named_their_way(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    await a1.ok("hierarchy.set_display_name", {"account_id": org["w1"], "label": "Ama"})
    w1 = await connect("cid-w1")
    for c in (su, a1, a2):
        await c.drain_pushes()
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
    await w1.ok("assistance.ping", {"to_account_id": org["a1"]})
    sent = {}
    for who, c in (("su", su), ("a1", a1), ("a2", a2)):
        sent[who] = [p.payload for p in await c.drain_pushes() if p.type == "audit.event"]
    assert any("Entered FIN-01" in e["what"] and e["kind"] == "session" for e in sent["su"])
    assert any("Entered FIN-01" in e["what"] for e in sent["a1"])
    assert sent["a2"] == []                                                      # HR's Admin does not hear Finance's events
    # names are the viewer's own: Finance's Admin called the worker "Ama"; the Super User never did
    ping_a1 = next(e for e in sent["a1"] if e["action_type"] == "assistance.ping")
    ping_su = next(e for e in sent["su"] if e["action_type"] == "assistance.ping")
    assert ping_a1["actor"] == "Ama" and ping_su["actor"] != "Ama" and ping_a1["host"] == "FIN-01"
