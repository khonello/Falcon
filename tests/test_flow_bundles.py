"""Choosing and Bundling through the whole flow (engine/flow/sync.py, worker_client/flowsync.py): what a Choosing step does not take is never
read, and a bundling flow makes one file from the whole folder at each run, and none when nothing changed."""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

from tests.conftest import requires_db
from tests.test_worker_client import _admin, _start, _wait

pytestmark = requires_db

ZIP = {"step": {"kind": "bundling", "op": "zip", "settings": {"name": "pack", "dated": False}}}


def _flow(org, *stages, run_mode="manual", **extra) -> dict:
    chained = [{**s, "parent_index": i - 1 if i else None} for i, s in enumerate(stages)]
    return {"source_pc_id": org["a1_pc"], "source_path": "C:/out", "run_mode": run_mode, "stages": chained,
            "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in", "parent_index": len(chained) - 1 if chained else None}], **extra}


async def test_what_a_choosing_step_does_not_take_is_never_read_and_by_size_is_decided_when_it_arrives(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    flow = (await a1.ok("flow.create", _flow(org, {"step": {"kind": "choosing", "op": "by_type", "settings": {"types": ["txt"]}}},
                                             {"step": {"kind": "choosing", "op": "by_size", "settings": {"is": "under", "mb": 0.001}}}, run_mode="realtime")))["flow"]
    await a1.drain_pushes()
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/out/photo.jpg", "hash": "h1"}})
    assert "flow.read" not in a1.push_types(await a1.drain_pushes())
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/out/big.txt", "hash": "h2"}})
    read = next(p for p in await a1.drain_pushes() if p.type == "flow.read")
    await a1.ok("flow.content", {"transfer_id": read.payload["transfer_id"], "hash": "h2", "content_b64": base64.b64encode(b"x" * 2000).decode()})      # over 1000 bytes
    assert "flow.apply" not in w1.push_types(await w1.drain_pushes())
    given = await engine.db.flows.synced_source_hashes(flow["destinations"][0]["id"])
    assert given == {"big.txt": "h2"}                                                  # on the record, so it is not read again for nothing
    assert (await a1.ok("flow.status", {"flow_id": flow["id"]}))["flow"]["files_copied"]["total"] == 0


async def test_a_bundling_step_is_refused_where_a_run_has_no_folder_and_a_placing_step_is_refused(engine, org, connect):
    a1 = await connect("cid-a1")
    assert await a1.err("flow.create", _flow(org, ZIP, run_mode="realtime")) == "invalid"
    assert await a1.err("flow.create", _flow(org, ZIP, source_kind="file")) == "invalid"
    assert await a1.err("flow.create", _flow(org, {"stage_type": "categorization", "config": {"by": "month"}})) == "invalid"
    tree = await a1.ok("flow.steps")
    assert tree["order"] == ["choosing", "conversion", "renaming", "bundling"] and len(tree["tree"]) == 2


async def test_a_run_sends_the_whole_folder_into_one_bundle_and_nothing_when_nothing_changed(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    flow = (await a1.ok("flow.create", _flow(org, ZIP)))["flow"]
    dest = flow["destinations"][0]["id"]
    await a1.drain_pushes()

    async def run(entries):
        await a1.ok("flow.run", {"flow_id": flow["id"]})
        asked = next(p for p in await a1.drain_pushes() if p.type == "flow.list")
        await a1.ok("flow.listing", {"request_id": asked.payload["request_id"], "entries": entries, "done": True})

    entries = [{"relative_path": "a.txt", "hash": "ha"}, {"relative_path": "b.txt", "hash": "hb"}]
    await run(entries)
    for _ in range(50):
        reads = [p for p in await a1.drain_pushes() if p.type == "flow.read"]
        if reads:
            break
    seen = 0
    while seen < 2:
        for r in reads:
            await a1.ok("flow.content", {"transfer_id": r.payload["transfer_id"], "hash": "h", "content_b64": "QQ=="})
            ap = next(p for p in await w1.drain_pushes() if p.type == "flow.apply")
            assert ap.payload["bundle"] and all(s["stage_type"] != "bundling" for s in ap.payload["stages"])
            await w1.ok("flow.sync_result", {"transfer_id": r.payload["transfer_id"], "destination_id": dest, "status": "kept_aside"})
            seen += 1
        reads = [p for p in await a1.drain_pushes() if p.type == "flow.read"]
    close = next(p for p in await w1.drain_pushes() if p.type == "flow.bundle_close")
    assert close.payload["name"] == "pack.zip" and close.payload["op"] == "zip"
    await w1.ok("flow.bundle_result", {"bundle_id": close.payload["bundle_id"], "status": "success", "written_path": "C:/in/pack.zip", "written_hash": "hz",
                                       "files": 2, "size_after": 10})
    assert (await a1.ok("flow.status", {"flow_id": flow["id"]}))["flow"]["files_copied"]["total"] == 1      # one file: the bundle
    await run(entries)                                                                 # nothing changed: no bundle
    assert "flow.read" not in a1.push_types(await a1.drain_pushes())
    await run(entries + [{"relative_path": "c.txt", "hash": "hc"}])                    # one more file: the whole folder again
    for _ in range(50):
        if len(reads := [p for p in await a1.drain_pushes() if p.type == "flow.read"]):
            break
    assert reads


async def test_two_real_workers_make_one_zip_at_each_run_with_the_steps_before_it_done(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    (src / "a.txt").write_text("alpha", encoding="utf-8")
    (src / "sub").mkdir()
    (src / "sub" / "b.txt").write_text("beta", encoding="utf-8")
    (src / "skip.tmp").write_text("no", encoding="utf-8")
    w1 = await _start(engine, tmp_path, "cid-w1", [str(src)])
    w2 = await _start(engine, tmp_path, "cid-w2", [str(dst)])
    admin = await _admin(engine)
    try:
        steps = [{"step": {"kind": "choosing", "op": "by_type", "settings": {"types": ["tmp"], "keep": "leave"}}},
                 {"step": {"kind": "renaming", "op": "add_text", "settings": {"text": "FIN-"}}, "parent_index": 0},
                 {**ZIP, "parent_index": 1}]
        flow = (await admin.call("flow.create", {"source_pc_id": org["w1_pc"], "source_path": str(src), "run_mode": "manual", "stages": steps,
                                                 "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst), "parent_index": 2}]}))["flow"]
        await admin.call("flow.run", {"flow_id": flow["id"]})
        pack = dst / "pack.zip"
        assert await _wait(lambda: pack.exists(), timeout=15)
        with zipfile.ZipFile(io.BytesIO(pack.read_bytes())) as z:
            assert sorted(z.namelist()) == ["FIN-a.txt", "sub/FIN-b.txt"] and z.read("FIN-a.txt") == b"alpha"
        assert not (dst / "FIN-a.txt").exists()                                       # kept aside, never a copy of its own

        async def logged():
            return (await engine.db.flows.synced_source_hashes(flow["destinations"][0]["id"])).get("<bundle>") is not None
        assert await _wait(logged, timeout=10)
        (src / "c.txt").write_text("gamma", encoding="utf-8")
        await admin.call("flow.run", {"flow_id": flow["id"]})

        def has_c() -> bool:
            try:
                with zipfile.ZipFile(io.BytesIO(pack.read_bytes())) as z:
                    return "FIN-c.txt" in z.namelist()
            except (OSError, zipfile.BadZipFile):
                return False
        assert await _wait(has_c, timeout=15)                                         # the flow's own earlier bundle, replaced
        assert not list(dst.glob("pack-modified*"))
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_an_edited_file_under_add_a_date_leaves_only_the_newest_copy(engine, org, tmp_path: Path):
    import os

    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1 = await _start(engine, tmp_path, "cid-w1", [str(src)])
    w2 = await _start(engine, tmp_path, "cid-w2", [str(dst)])
    admin = await _admin(engine)
    try:
        flow = (await admin.call("flow.create", {"source_pc_id": org["w1_pc"], "source_path": str(src),
                                                 "stages": [{"step": {"kind": "renaming", "op": "add_date"}}],
                                                 "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst), "parent_index": 0}]}))["flow"]
        report = src / "report.txt"
        report.write_text("first", encoding="utf-8")
        os.utime(report, (1793000000, 1793000000))                                      # (a day of its own, so the edit below is another day)

        def copies() -> list[Path]:
            return [p for p in dst.iterdir() if p.is_file()]
        assert await _wait(lambda: any(p.read_text(encoding="utf-8") == "first" for p in copies()), timeout=15)

        async def logged():
            return bool((await engine.db.flows.synced_source_hashes(flow["destinations"][0]["id"])).get("report.txt"))
        assert await _wait(logged, timeout=10)
        report.write_text("second", encoding="utf-8")                                   # edited today: a new dated name
        assert await _wait(lambda: len(copies()) == 1 and copies()[0].read_text(encoding="utf-8") == "second", timeout=15)
        assert [p.read_text(encoding="utf-8") for p in (dst / ".falcon-removed").iterdir()] == ["first"]
        assert (await admin.call("flow.status", {"flow_id": flow["id"]}))["flow"]["files_copied"]["total"] == 2
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()
