"""Flow end-to-end over the socket (skipped without FALCON_TEST_DATABASE_URL).

Pins flow-natural-combo.md: consent by authority, pre-flight collision surfaced, cycles
refused, resource folders excluded, one-directional propagation relayed through the Engine,
write attribution distinguishing own writes from external ones, branch-scoped failure with a
reactive suggestion, and resume.
"""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


def flow_payload(src_pc: int, dests: list[tuple[int | None, str]], **extra):
    return {"source_pc_id": src_pc, "source_path": "C:/out",
            "destinations": [{"destination_pc_id": pc, "destination_path": path} for pc, path in dests],
            "stages": [], **extra}


async def test_creation_checks(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    # Workers cannot create flows; Admin's source must be in their department.
    assert await w1.err("flow.create", flow_payload(org["w1_pc"], [(org["w2_pc"], "C:/in")])) == "forbidden"
    assert await a1.err("flow.create", flow_payload(org["a2_pc"], [(org["w1_pc"], "C:/in")])) == "forbidden"
    # Resource folders are never endpoints.
    assert await a1.err("flow.create", flow_payload(org["a1_pc"], [(org["w1_pc"], "C:/resources/common")])) == "invalid"
    # Destination inside its own source is a cycle.
    assert await a1.err("flow.create", flow_payload(org["a1_pc"], [(org["a1_pc"], "C:/out/sub")])) == "conflict"
    # Collision: existing indexed content under the destination path must be confirmed.
    await engine.db.file_index.upsert(org["w1_pc"], "C:/in/old.txt", "old.txt", "h", None, None, "event")
    assert await a1.err("flow.create", flow_payload(org["a1_pc"], [(org["w1_pc"], "C:/in")])) == "conflict"
    res = await a1.ok("flow.create", flow_payload(org["a1_pc"], [(org["w1_pc"], "C:/in")], confirm_collisions=True))
    assert res["collisions_confirmed"][0]["existing"] == ["C:/in/old.txt"]
    assert res["flow"]["status"] == "active" and res["flow"]["consent_status"] == "not_required"
    f1 = res["flow"]["id"]
    # Chaining W1 -> W2 is fine; W2 -> A1's C:/out would close the loop.
    res2 = await a1.ok("flow.create", {**flow_payload(org["w1_pc"], [(org["w2_pc"], "C:/mirror")]), "source_path": "C:/in"})
    assert await a1.err("flow.create", {**flow_payload(org["w2_pc"], [(org["a1_pc"], "C:/out/deep")]),
                                        "source_path": "C:/mirror"}) == "conflict"
    # Lateral (Admin -> other department's Admin) needs consent: created paused, owner is asked.
    res3 = await a1.ok("flow.create", flow_payload(org["a1_pc"], [(org["a2_pc"], "C:/from-finance")]))
    assert res3["consent_pending"] is True and res3["flow"]["status"] == "paused"
    assert res3["flow"]["pause_reason"] == "consent:pending"
    req = next(p for p in await a2.drain_pushes() if p.type == "flow.consent_request")
    assert req.payload["flow_id"] == res3["flow"]["id"]
    assert await w1.err("flow.consent", {"flow_id": res3["flow"]["id"], "granted": True}) == "forbidden"
    assert await a1.err("flow.resume", {"flow_id": res3["flow"]["id"]}) == "conflict"   # still awaiting consent
    await a2.ok("flow.consent", {"flow_id": res3["flow"]["id"], "granted": True})
    assert "flow.consent_answered" in a1.push_types(await a1.drain_pushes())
    st = (await a1.ok("flow.status", {"flow_id": res3["flow"]["id"]}))["flow"]
    assert st["status"] == "active" and st["consent_status"] == "granted"
    # Visibility: creator, destination owner, Super User; W2 sees flows into its department.
    assert {f["id"] for f in (await a1.ok("flow.list"))["flows"]} == {f1, res2["flow"]["id"], res3["flow"]["id"]}
    assert await a2.ok("flow.status", {"flow_id": res3["flow"]["id"]})
    assert await w1.err("flow.status", {"flow_id": res3["flow"]["id"]}) == "forbidden"


async def test_propagation_attribution_conflict_and_failure(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    res = await a1.ok("flow.create", {
        "source_pc_id": org["a1_pc"], "source_path": "C:/out",
        "stages": [{"stage_type": "transformation", "config": {"to": "pdf"}},
                   {"stage_type": "branch", "parent_index": 0},
                   {"stage_type": "categorization", "parent_index": 1, "config": {"by": "extension"}}],
        "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in", "parent_index": 1},
                         {"destination_pc_id": org["w2_pc"], "destination_path": "C:/in", "parent_index": 2}]})
    flow = res["flow"]
    d1, d2 = flow["destinations"]

    # 1. A change at the source triggers flow.read to the source PC only.
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/out/docs/report.docx", "hash": "h1"}})
    read = next(p for p in await a1.drain_pushes() if p.type == "flow.read")
    assert read.payload["path"] == "C:/out/docs/report.docx"
    assert w1.push_types(await w1.drain_pushes()) == []
    # 2. Source delivers content; each destination gets flow.apply with ITS stage chain.
    await a1.ok("flow.content", {"transfer_id": read.payload["transfer_id"], "hash": "h1", "content_b64": "QUJD"})
    apply1 = next(p for p in await w1.drain_pushes() if p.type == "flow.apply")
    apply2 = next(p for p in await w2.drain_pushes() if p.type == "flow.apply")
    assert apply1.payload["relative_path"] == "docs/report.docx" and apply1.payload["content_b64"] == "QUJD"
    assert [s["stage_type"] for s in apply1.payload["stages"]] == ["transformation"]
    assert [s["stage_type"] for s in apply2.payload["stages"]] == ["transformation", "categorization"]
    # 3. W1 succeeds; W2 fails in its Categorization stage -> only W2's branch pauses.
    await w1.ok("flow.sync_result", {"transfer_id": read.payload["transfer_id"], "destination_id": d1["id"],
                                     "status": "success", "written_hash": "h1-pdf"})
    await w2.ok("flow.sync_result", {"transfer_id": read.payload["transfer_id"], "destination_id": d2["id"],
                                     "status": "failed", "failure": {"stage_type": "categorization", "kind": "place_failed"}})
    failed = next(p for p in await a1.drain_pushes() if p.type == "flow.failed")
    assert failed.payload["destination_id"] == d2["id"] and "fallback category" in failed.payload["suggestion"]
    assert "flow.failed" in w2.push_types(await w2.drain_pushes())
    st = (await a1.ok("flow.status", {"flow_id": flow["id"]}))["flow"]
    assert st["status"] == "active"
    assert st["destinations"][0]["paused_reason"] is None and st["destinations"][0]["last_sync"]["written_by"] == "flow_sync"
    assert st["destinations"][1]["paused_reason"] == "categorization:place_failed"
    assert (await engine.db.reports.all())[0]["category"] == "flow_failure"

    # 4. Attribution: the flow's own write landing at W1 (same hash) is NOT a conflict.
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/in/docs/report.pdf", "hash": "h1-pdf"}})
    assert w1.push_types(await w1.drain_pushes()) == []
    # An external edit at W1 (different hash) is: preserved as -modified, and re-synced.
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/in/docs/report.pdf", "hash": "external"}})
    resolve = next(p for p in await w1.drain_pushes() if p.type == "flow.resolve_conflict")
    assert resolve.payload["rename_to"] == "C:/in/docs/report-modified.pdf"
    reread = next(p for p in await a1.drain_pushes() if p.type == "flow.read")
    assert reread.payload["path"].replace("\\", "/") == "C:/out/docs/report.pdf"
    hist = (await a1.ok("flow.history", {"flow_id": flow["id"]}))["history"]
    assert [h["written_by"] for h in hist] == ["external", "flow_sync"]

    # 5. Resume the failed branch; a paused branch received no apply meanwhile.
    assert w2.push_types(await w2.drain_pushes()) == []
    await a1.ok("flow.resume", {"flow_id": flow["id"], "destination_id": d2["id"]})
    st = (await a1.ok("flow.status", {"flow_id": flow["id"]}))["flow"]
    assert st["destinations"][1]["paused_reason"] is None
    # Delete keeps the row and history.
    await a1.ok("flow.delete", {"flow_id": flow["id"]})
    assert (await a1.ok("flow.list"))["flows"] == []
    assert await engine.db.pool.fetchval("SELECT count(*) FROM flow_sync_log") == 2
