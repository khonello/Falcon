"""Detective: what a person seems to be doing, read from several things happening together.

The scenarios are scripted (scripts/detective_scenarios.py): malicious and benign ones side by side, because the point is that the same moves with a
different context stay quiet. Nothing here needs a database or a Worker.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from detective_scenarios import PC, SCENARIOS, R, Script, clock, play

from common.detective import (
    CASE,
    NOTED,
    URGENT,
    Context,
    Detective,
    Sig,
    disguised,
    ext_of,
    is_archive,
    is_system_folder,
)


def test_the_leak_is_raised_before_anything_leaves_and_reads_as_one_story():
    det, updates = play(SCENARIOS["leak"]())
    raised = [u for u in updates if u.raised]
    assert raised and raised[0].now in ("case", "urgent")
    first = raised[0]
    # raised while the files are still on the machine: the drive has not been plugged in yet
    drive_at = next(s.at for s in SCENARIOS["leak"]().sigs if s.verb == "attached")
    assert first.finding.at < drive_at
    assert first.intent in ("Hiding something", "Taking data out") and "Taking data out" in {u.intent for u in raised}
    stage_raise = next(u for u in raised if u.intent == "Taking data out")
    assert stage_raise.not_yet == "It has not left the machine yet." and stage_raise.finding.at < drive_at
    (case,) = det.open_cases()                                                              # one case, not a pile of findings
    assert case.intent == "Taking data out" and case.level == "urgent" and case.weight >= URGENT
    assert case.behaviours >= {"concealment", "collection", "exfiltration", "erasure"}
    assert case.stage[0] == 4 and case.not_yet() is None
    story = case.story()
    assert any("copied 14 files to C:/Users/kojo/Staging" in line for line in story)         # fourteen events read as one line
    assert any("plugged in a drive" in line for line in story) and story == sorted(story, key=lambda ln: ln[:5])
    assert "payroll-q3.xlsx was renamed to look like a different kind of file" in case.headline() or "hidden" in case.headline()


def test_the_backup_that_makes_the_same_moves_stays_quiet():
    det, updates = play(SCENARIOS["backup_twin"]())
    assert not [u for u in updates if u.raised]
    assert all(c.level in ("quiet", "noted") and c.weight < CASE for c in det.cases)
    # ... and it is the context that does it: without it the very same signals are a case
    plain = SCENARIOS["backup_twin"]()
    det2 = Detective(Context())
    plain_sigs = [Sig(s.at, s.pc, s.verb, s.path, s.old, s.thing, "unknown-tool.exe", s.by, s.device, s.tags) for s in plain.sigs]
    for s in plain_sigs:
        det2.feed(s)
    assert any(c.weight >= CASE for c in det2.cases)


def test_a_patient_actor_is_a_case_only_when_the_same_file_ties_the_days_together():
    sc = SCENARIOS["patient"]()
    det = Detective(sc.ctx)
    early = [det.feed(s) for s in sc.sigs[:2]]
    assert not any(u.raised for ups in early for u in ups)                                  # Monday and Wednesday: noted, nothing raised
    assert det.cases[0].level in ("noted", "quiet")
    late = [det.feed(s) for s in sc.sigs[2:]]
    assert any(u.raised for ups in late for u in ups)                                       # the drive and the copy of the very file hidden on Monday
    (case,) = det.open_cases()
    assert case.intent == "Taking data out" and case.level in ("case", "urgent")
    assert case.last_at - case.first_at > 3.5 * 86400
    assert case.stage[2] == "Covering up" and case.not_yet() == "Nothing has been erased yet."   # it says what usually comes next
    assert any(line.startswith("Mon") for line in case.story()) and any(line.startswith("Fri") for line in case.story())


def test_two_unrelated_small_things_far_apart_are_not_joined():
    s = Script(clock(1, 10, 0))
    s.add("hid", r"C:\Users\a\Documents\one.docx", thing="h1", by="hand")
    s.after(20 * 86400).add("hid", r"C:\Users\a\Documents\two.docx", thing="h2", by="hand")
    det = Detective()
    for sig in s.out:
        det.feed(sig)
    assert len(det.cases) == 2 and all(c.level == "noted" for c in det.cases)


def test_one_hidden_personal_file_is_noted_not_raised():
    det, updates = play(SCENARIOS["one_hidden_file"]())
    assert not [u for u in updates if u.raised]
    (case,) = det.open_cases()
    assert case.level == "noted" and case.intent == "Hiding something" and case.not_yet() is None     # nothing to say about "leaving" for a lone file


def test_falcons_own_work_is_not_behaviour_at_all():
    det, updates = play(SCENARIOS["flow_to_drive"]())
    assert updates == [] and det.cases == [] and det.mem.get(PC) is not None and len(det.mem[PC].recent) == 1     # only the drive was seen


def test_a_task_that_asks_for_exactly_this_takes_the_edge_off():
    det, updates = play(SCENARIOS["covered_by_task"]())
    assert not [u for u in updates if u.raised]
    (case,) = det.cases
    assert case.level == "quiet" and any("a task covers" in w for f in case.findings for w in f.why)


def test_reaching_outside_ones_work_is_noted_and_named():
    det, _ = play(SCENARIOS["snooping"]())
    (case,) = det.open_cases()
    assert case.intent == "Looking where they should not" and case.level == "noted" and case.behaviours == {"reach"}
    assert "15 files were opened across 4 folders" in case.headline()


def test_what_makes_a_name_a_disguise():
    assert disguised("payroll.xlsx", "notes.txt.dll") and disguised("a.docx", "a.docx.exe") and disguised("a.pdf", "a.sys")
    assert not disguised("a.docx", "b.docx") and not disguised("a.docx", "a.pdf") and not disguised("", "x.dll") and not disguised("a.docx", "")
    assert ext_of(r"C:\x\Report.FINAL.XLSX") == "xlsx" and ext_of("noext") == "" and is_archive("a.7z") and not is_archive("a.docx")
    assert is_system_folder(r"C:\Windows\Temp\x") and is_system_folder(r"C:\Users\kojo\AppData\Local\x") and not is_system_folder(r"C:\Finance\Payroll\x.xlsx")


def test_a_drive_this_machine_always_uses_lowers_it_and_a_new_one_raises_it():
    def run(uses):
        s = Script(clock(2, 14, 0))
        s.add("attached", "E:\\", device="E:\\", by="alone")
        s.after(10).add("copied", "E:\\board.zip", old=r"C:\x\board.zip", thing="h", by="hand", tags=R)
        d = Detective(Context(known_device=lambda pc, dev: uses))
        for sig in s.out:
            d.feed(sig)
        return d.cases[0].weight

    assert run(0) > run(1) >= run(5) and run(0) >= CASE > run(5)


def test_time_of_day_never_starts_anything_and_only_nudges():
    s = Script(clock(2, 3, 0))
    s.add("modified", r"C:\Users\a\Documents\notes.docx", thing="h", by="hand")
    s.add("opened", r"C:\Users\a\Documents\notes.docx", thing="h", by="hand")
    det = Detective()
    for sig in s.out:
        assert det.feed(sig) == []
    assert det.cases == []
    late = Script(clock(2, 3, 0)).add("hid", r"C:\Users\a\Documents\n.docx", thing="h", by="hand").out[0]
    day = Script(clock(2, 14, 0)).add("hid", r"C:\Users\a\Documents\n.docx", thing="h", by="hand").out[0]
    a, b = Detective(), Detective()
    assert a.feed(late)[0].case.weight - b.feed(day)[0].case.weight == pytest.approx(0.04, abs=0.01)


def test_weights_combine_like_independent_hints_and_stay_below_certainty():
    det = Detective()
    for i in range(30):
        det.feed(Sig(clock() + i, 1, "hid", rf"C:\Windows\Temp\f{i}.docx", thing=f"h{i}", tags=R))
    assert all(c.weight <= 0.99 for c in det.cases) and max(c.weight for c in det.cases) >= URGENT
    assert NOTED < CASE < URGENT


def test_it_survives_anything_it_is_given():
    rnd = random.Random(5)
    verbs = ["created", "modified", "renamed", "moved", "copied", "deleted", "opened", "hid", "unhid", "attached", "detached", "launched", "exited", "captured", "cleared", "silent", "nonsense"]
    paths = ["", r"C:\a\b.docx", r"E:\x.zip", "relative", "/etc/passwd", r"C:\Windows\Temp\z.dll", "ünï\u202e.docx", "a" * 500, r"\\hr\files\x.docx"]
    det = Detective(Context(task_things=lambda pc: {"t"}, known_device=lambda pc, d: 3))
    t = clock()
    for _ in range(3000):
        t += rnd.random() * 400
        det.feed(Sig(t, rnd.randint(1, 3), rnd.choice(verbs), rnd.choice(paths), rnd.choice(paths), rnd.choice(["", "t", "u", "v"]), rnd.choice(["", "robocopy.exe", "x.exe"]),
                     rnd.choice(["hand", "alone", "started", "falcon", "unknown"]), rnd.choice(["", "E:\\"]), frozenset(rnd.sample(["restricted", "outside_role"], rnd.randint(0, 2)))))
    for c in det.cases:
        assert 0 <= c.weight <= 0.99 and c.intent and c.story() is not None and c.headline()


def test_what_is_remembered_is_bounded():
    det = Detective()
    t = clock()
    for i in range(20000):
        det.feed(Sig(t + i * 5, 1, "modified", rf"C:\a\f{i % 50}.txt", thing=str(i)))
    assert len(det.mem[1].recent) < 5000 and time.time() > 0


def test_a_case_draws_as_a_picture_where_a_burst_is_one_thing():
    det, _ = play(SCENARIOS["leak"]())
    g = det.open_cases()[0].graph()
    by = {n["label"]: n for n in g["nodes"]}
    assert by["14 files in Payroll"]["col"] == 0 and by["14 files in Staging"]["col"] == 1 and by["Drive E:"]["col"] == 3 and by["q3.zip"]["col"] == 2
    assert by["notes.txt.dll"]["badges"] == ["hidden"] and by["q3.zip"]["badges"] == ["deleted"] and by["cleared the list of recent files"]["col"] == 4
    verbs = [(e["verb"], e["to"].split(":")[0]) for e in g["edges"]]
    assert ("moved", "f") in verbs and ("copied", "dir") in verbs and ("packed", "f") in verbs and ("copied", "dev") in verbs
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in g["edges"])                  # every line joins two things that are drawn
    assert [n["col"] for n in g["nodes"]] == sorted(n["col"] for n in g["nodes"])


def test_a_graph_of_nothing_is_empty_and_the_evidence_survives_a_round_trip():
    from common.detective import graph_of, sig_from_dict, sig_to_dict

    assert graph_of([]) == {"nodes": [], "edges": []}
    det, _ = play(SCENARIOS["patient"]())
    before = det.open_cases()[0].graph()
    sigs = [sig_from_dict(sig_to_dict(e)) for f in det.open_cases()[0].findings for e in f.evidence]
    assert {n["label"] for n in graph_of(sigs)["nodes"]} == {n["label"] for n in before["nodes"]}
