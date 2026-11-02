"""What the concept's Flows pages show that a flow could not be before 2 Nov 2026: its own name, when it copies (the moment a file changes,
every hour, or only when someone presses Run), several sources merged into one flow, carrying on from another flow, the files copied, and an
edit that retires the old steps (migration 047)."""

from __future__ import annotations

from engine.flow import sync
from tests.conftest import requires_db

pytestmark = requires_db


def _flow(src_pc: int, src: str, dest_pc: int, dest: str, **extra):
    return {"source_pc_id": src_pc, "source_path": src, "stages": [],
            "destinations": [{"destination_pc_id": dest_pc, "destination_path": dest}], **extra}


async def test_a_flow_set_to_run_only_when_asked_moves_nothing_until_run_and_an_hourly_one_on_the_hour(engine, org, connect):
    a1 = await connect("cid-a1")
    await connect("cid-w1")
    made = (await a1.ok("flow.create", {**_flow(org["a1_pc"], "C:/out", org["w1_pc"], "C:/in"), "name": "  month-end ", "run_mode": "manual",
                                        "stages": [{"stage_type": "categorization", "config": {"op": "Sort by month"}}],
                                        "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in", "parent_index": 0}]}))["flow"]
    assert made["name"] == "month-end" and made["run_mode"] == "manual" and made["files_copied"]["total"] == 0
    assert made["stages"][0]["config"]["by"] == "month"
    await a1.drain_pushes()
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/out/report.txt", "hash": "h1"}})
    assert "flow.read" not in a1.push_types(await a1.drain_pushes())                       # a run-only flow does not copy on a change
    assert (await a1.ok("flow.run", {"flow_id": made["id"]}))["sources_started"] == 1
    asked = next(p for p in await a1.drain_pushes() if p.type == "flow.list")              # Run lists the source and sends what changed
    assert asked.payload["flow_id"] == made["id"]
    assert (await engine.db.flows.get(made["id"]))["last_run_at"] is not None
    assert await a1.err("flow.create", {**_flow(org["a1_pc"], "C:/x", org["w1_pc"], "C:/y"), "run_mode": "weekly"}) == "invalid"
    assert await a1.err("flow.create", {**_flow(org["a1_pc"], "C:/x", org["w1_pc"], "C:/y"), "name": "x" * 81}) == "invalid"

    hourly = (await a1.ok("flow.create", {**_flow(org["a1_pc"], "C:/hourly", org["w1_pc"], "C:/hourly-in"), "run_mode": "hourly"}))["flow"]
    await a1.drain_pushes()
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/hourly/a.txt", "hash": "h2"}})
    assert "flow.read" not in a1.push_types(await a1.drain_pushes())
    await sync.heal(engine)                                                                # healing leaves hourly and run-only flows alone
    assert [p.payload["flow_id"] for p in await a1.drain_pushes() if p.type == "flow.list"] == []
    await sync.hourly(engine)
    assert [p.payload["flow_id"] for p in await a1.drain_pushes() if p.type == "flow.list"] == [hourly["id"]]


async def test_several_sources_merge_into_one_flow_that_pauses_runs_and_counts_as_one(engine, org, connect):
    a1 = await connect("cid-a1")
    w1, w2 = await connect("cid-w1"), await connect("cid-w2")
    res = await a1.ok("flow.create", {"name": "ops-pack", "stages": [], "confirm_collisions": True,
                                      "sources": [{"source_pc_id": org["a1_pc"], "source_path": "C:/reports"},
                                                  {"source_pc_id": org["w2_pc"], "source_path": "C:/exports"}],
                                      "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/packs"}]})
    flow = res["flow"]
    assert [s["source_path"] for s in flow["sources"]] == ["C:/reports", "C:/exports"]
    listed = (await a1.ok("flow.list"))["flows"]
    assert [f["id"] for f in listed] == [flow["id"]] and len(listed[0]["sources"]) == 2      # one flow, both sources
    other = await engine.db.pool.fetchrow("SELECT * FROM flows WHERE merged_into = $1", flow["id"])
    assert other["name"] == "ops-pack" and other["source_pc_id"] == org["w2_pc"]

    # a change at the second source is copied by the flow, and counted on it
    await w2.ok("index.event", {"event": {"op": "modify", "path": "C:/exports/q3.csv", "hash": "hq"}})
    read = next(p for p in await w2.drain_pushes() if p.type == "flow.read")
    await w2.ok("flow.content", {"transfer_id": read.payload["transfer_id"], "hash": "hq", "content_b64": "QUJD", "modified": "2026-10-14T09:30:00+00:00"})
    apply = next(p for p in await w1.drain_pushes() if p.type == "flow.apply")
    assert apply.payload["modified"] == "2026-10-14T09:30:00+00:00"                          # the steps date things by the source's own time
    await w1.ok("flow.sync_result", {"transfer_id": read.payload["transfer_id"], "destination_id": apply.payload["destination_id"],
                                     "status": "success", "written_hash": "hq", "written_path": "C:/packs/q3.csv"})
    counted = (await a1.ok("flow.status", {"flow_id": flow["id"]}))["flow"]["files_copied"]
    assert counted["total"] == 1 and counted["today"] == 1

    # pausing, running and retiring act on every source
    await a1.ok("flow.pause", {"flow_id": flow["id"]})
    assert {r["status"] for r in await engine.db.flows.group(flow["id"])} == {"paused"}
    await a1.ok("flow.resume", {"flow_id": flow["id"]})
    assert (await a1.ok("flow.run", {"flow_id": flow["id"]}))["sources_started"] == 2
    await a1.ok("flow.delete", {"flow_id": flow["id"]})
    assert await engine.db.pool.fetchval("SELECT count(*) FROM flows WHERE (id = $1 OR merged_into = $1) AND status <> 'inactive'", flow["id"]) == 0
    assert await a1.err("flow.create", {"stages": [], "sources": [{"source_pc_id": org["a1_pc"], "source_path": "C:/r"},
                                                                  {"source_pc_id": org["a1_pc"], "source_path": "C:/r/sub"}],
                                        "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/p"}]}) == "invalid"


async def test_a_flow_carries_on_from_another_and_an_edit_retires_the_old_steps(engine, org, connect):
    a1 = await connect("cid-a1")
    first = (await a1.ok("flow.create", {**_flow(org["a1_pc"], "C:/out", org["w1_pc"], "C:/in"),
                                         "stages": [{"stage_type": "transformation", "config": {"op": "Compress to ZIP"}}],
                                         "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in", "parent_index": 0}]}))["flow"]
    then = (await a1.ok("flow.create", {"stages": [], "from_flow": {"flow_id": first["id"], "destination_id": first["destinations"][0]["id"]},
                                        "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": "C:/archive"}]}))["flow"]
    assert (then["source_pc_id"], then["source_path"], then["source_flow_id"]) == (org["w1_pc"], "C:/in", first["id"])
    assert await a1.err("flow.create", {"stages": [], "from_flow": {"flow_id": first["id"], "destination_id": 99999},
                                        "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": "C:/a2"}]}) == "invalid"

    await a1.ok("flow.edit", {"flow_id": first["id"], "name": "zipped", "run_mode": "hourly",
                              "stages": [{"stage_type": "transformation", "config": {"op": "Rename by date"}}],
                              "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in", "parent_index": 0}]})
    now = (await a1.ok("flow.status", {"flow_id": first["id"]}))["flow"]
    assert [s["config"]["op"] for s in now["stages"]] == ["Rename by date"] and now["name"] == "zipped" and now["run_mode"] == "hourly"
    listed = next(f for f in (await a1.ok("flow.list"))["flows"] if f["id"] == first["id"])
    assert [s["config"]["op"] for s in listed["stages"]] == ["Rename by date"]
    assert await engine.db.pool.fetchval("SELECT count(*) FROM flow_stages WHERE flow_id = $1 AND retired_at IS NOT NULL", first["id"]) == 1


async def test_a_file_deleted_at_the_source_keeps_its_copies_and_the_issues_page_can_remove_them(engine, org, connect):
    """The user, 2 Nov 2026: a flow keeps its copies when a file is deleted at its source, and the Issues page offers to remove them."""
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    flow = (await a1.ok("flow.create", _flow(org["a1_pc"], "C:/out", org["w1_pc"], "C:/in")))["flow"]
    dest = flow["destinations"][0]["id"]
    for name in ("a.txt", "b.txt"):                                        # two files the flow had copied
        await engine.db.flows.log_sync(dest, f"h-{name}", "flow_sync", None, source_relative_path=name, written_path=f"C:/in/{name}", source_hash=f"h-{name}")
    await a1.ok("index.event", {"event": {"op": "delete", "path": "C:/out/a.txt"}})
    await a1.ok("index.event", {"event": {"op": "delete", "path": "C:/out/b.txt"}})
    await a1.ok("index.event", {"event": {"op": "delete", "path": "C:/out/never-copied.txt"}})     # nothing to say about a file it never carried
    assert "flow.remove" not in w1.push_types(await w1.drain_pushes())                         # kept, as the flow is set to
    found = [i for i in (await a1.ok("issues.list"))["issues"] if i["type"] == "flow"]
    assert len(found) == 1 and found[0]["title"] == "2 files were deleted at a flow's source"
    got = await a1.ok("issues.get", {"issue_id": found[0]["id"]})
    assert {o["key"] for o in got["options"]} == {"remove_copies", "keep_copies"}
    await a1.ok("issues.act", {"issue_id": found[0]["id"], "key": "remove_copies"})
    removed = [p for p in await w1.drain_pushes() if p.type == "flow.remove"]
    assert sorted(p.payload["relative_path"] for p in removed) == ["a.txt", "b.txt"]
    assert (await a1.ok("issues.get", {"issue_id": found[0]["id"]}))["issue"]["state"] == "resolved"
