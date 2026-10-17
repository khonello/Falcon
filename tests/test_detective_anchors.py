"""Anchors are areas an intent covers, not steps: any event that belongs to an area counts by its own weight, whatever the route, and nothing needs to be complete."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from detective_scenarios import SCENARIOS, play

from common.anchors import ANCHORS, INCLUDES, coverage
from tests.conftest import requires_db


def top(name: str):
    det, updates = play(SCENARIOS[name]())
    cases = sorted(det.cases, key=lambda c: c.weight, reverse=True)
    return cases[0] if cases else None, updates


def test_every_behaviour_has_areas_and_intents_can_contain_intents():
    assert set(ANCHORS) == {"concealment", "collection", "exfiltration", "capture", "erasure", "evasion", "sabotage", "reach"}
    assert all(len(v) >= 3 for v in ANCHORS.values())
    assert set(INCLUDES["exfiltration"]) == {"collection", "concealment", "capture"} and INCLUDES["sabotage"] == ("erasure",)
    assert all(c in ANCHORS for kids in INCLUDES.values() for c in kids)


def test_coverage_needs_no_area_to_be_complete_and_one_heavy_event_is_enough():
    one, areas = coverage("sabotage", {"Destroy": [0.5]})
    assert 0.45 < one <= 0.5 and areas == ["Destroy"]
    many_light, _ = coverage("sabotage", {"Destroy": [0.1] * 200})
    assert many_light < 0.35                                                                       # a number of light ones alone never reaches "noted"
    two, covered = coverage("exfiltration", {"Gather": [0.15], "Transfer": [0.3]})
    assert two > max(0.15, 0.3) and covered == ["Gather", "Transfer"]                              # more kinds of thing is more evidence, with no order
    swapped, _ = coverage("exfiltration", {"Transfer": [0.3], "Gather": [0.15]})
    assert swapped == two
    child, areas = coverage("exfiltration", {}, {"collection/Access": [0.3]})
    assert child < 0.3 and areas == ["collection/Access"]                                          # a child's evidence counts toward the parent at a discount
    assert coverage("reach", {"Find": [0.9], "Return": [0.9]})[0] <= 0.55                          # looking around is noted until it comes back... (ceiling)


def test_one_file_zipped_and_sent_by_the_browser_is_taking_out_whatever_the_route():
    case, updates = top("zip_one_file_then_upload")
    assert case.intent == "Taking data out" and case.level in ("case", "urgent") and any(u.raised for u in updates)
    areas = {a["name"] for b in case.board() if b["behaviour"] == "exfiltration" for a in b["areas"] if a["covered"]}
    assert {"Gather", "Compress", "Transfer"} <= areas


def test_a_document_saved_in_another_format_and_taken_on_a_drive_is_taking_out():
    case, _ = top("convert_then_drive")
    assert case.intent == "Taking data out" and case.level in ("case", "urgent")


def test_one_restricted_file_on_a_public_share_is_noted_on_its_own():
    case, _ = top("one_file_to_a_share")
    assert case.level == "noted" and "exfiltration" in case.behaviours


def test_one_deletion_of_the_only_copy_of_something_that_matters_outweighs_sixty_of_the_wrong_ones():
    case, updates = top("sole_copy_deleted")
    assert case.level in ("case", "urgent") and "sabotage" in case.behaviours and any(u.raised for u in updates)
    ordinary, _ = top("ordinary_delete")
    assert ordinary.level == "quiet"
    sixty, _ = top("big_clean_up_by_hand")
    assert sixty.level == "quiet" and case.weight > sixty.weight


def test_removing_backups_and_then_files_is_wrecking_with_no_order_required():
    case, _ = top("backups_then_files")
    assert case.intent == "Wrecking things" and case.level in ("case", "urgent")
    areas = {a["name"] for b in case.board() if b["behaviour"] == "sabotage" for a in b["areas"] if a["covered"]}
    assert {"Disable safety nets", "Destroy"} <= areas


def test_a_patient_collector_over_weeks_is_one_piece_of_work_when_the_folder_ties_them_together():
    det, updates = play(SCENARIOS["weekly_collector"]())
    final = max(det.cases, key=lambda c: c.weight)
    assert final.level in ("case", "urgent") and final.intent == "Taking data out"
    cover = [f for f in final.findings if f.graph == "coverage_exfiltration"][-1]
    assert any("Gather" in line and "Compress" in line and "Transfer" in line for line in cover.why)       # the weeks-old copies are in it


def test_the_first_look_at_the_one_folder_that_was_chosen_is_noted():
    case, _ = top("one_look_at_the_director")
    assert case.level == "noted" and "reach" in case.behaviours


def test_an_ordinary_day_stays_quiet_and_a_permission_change_alone_is_recorded_not_raised():
    day, updates = top("ordinary_day")
    assert day.level == "quiet" and not any(u.raised for u in updates)
    lock, up = top("lock_out")
    assert lock.level == "quiet" and any(f.graph == "coverage_sabotage" for f in lock.findings) and not any(u.raised for u in up)


def test_a_case_shows_its_board_as_areas_covered_with_none_required():
    case, _ = top("zip_one_file_then_upload")
    board = {b["behaviour"]: b for b in case.board()}
    take = board["exfiltration"]
    assert take["of"] == 4 and take["covered"] >= 3 and [a["name"] for a in take["areas"]] == ["Gather", "Transform", "Compress", "Transfer"]
    assert not next(a for a in take["areas"] if a["name"] == "Transform")["covered"]                    # not all of them, and that is fine
    case2, _ = top("leak")
    assert {"exfiltration", "concealment"} <= {b["behaviour"] for b in case2.board()}


@requires_db
async def test_the_engine_hands_the_board_to_the_page_and_knows_when_a_deleted_file_was_the_only_copy(engine, org, connect):
    su = await connect("cid-su")
    pc = org["w1_pc"]
    fi = engine.file_index
    await fi.ingest_sweep_batch(pc, [{"op": "create", "path": "C:\\Legal\\contract-amendment-7.docx", "name": "contract-amendment-7.docx", "hash": "h-only", "resource_tag": "restricted"}], first=True)
    await fi.ingest_event(pc, {"op": "delete", "path": "C:\\Legal\\contract-amendment-7.docx", "name": "contract-amendment-7.docx", "hash": "h-only", "witness": {"by": "hand", "front": "explorer.exe"}})
    case = (await su.ok("detective.cases", {"include_noted": True}))["cases"][0]
    assert case["level"] in ("case", "urgent") and "sabotage" in case["behaviours"]
    detail = await su.ok("detective.case", {"case_id": case["id"]})
    assert any(b["behaviour"] == "sabotage" and any(a["name"] == "Destroy" and a["covered"] for a in b["areas"]) for b in detail["board"])
    # the same content kept somewhere else is not "the only copy"
    await fi.ingest_sweep_batch(pc, [{"op": "create", "path": "C:\\Legal\\copy.docx", "name": "copy.docx", "hash": "h-two"}], first=True)
    await fi.ingest_sweep_batch(org["w2_pc"], [{"op": "create", "path": "C:\\Legal\\copy.docx", "name": "copy.docx", "hash": "h-two"}], first=True)
    await fi.ingest_event(pc, {"op": "delete", "path": "C:\\Legal\\copy.docx", "name": "copy.docx", "hash": "h-two", "witness": {"by": "hand"}})
    rows = await engine.db.pool.fetch("SELECT summary, weight FROM detective_findings WHERE summary ILIKE '%copy.docx%'")
    assert not rows or max(r["weight"] for r in rows) < 0.35
