"""What a description asks that Falcon cannot read as a target (engine/task/cues.py): each says what it could not work out, and nothing is guessed."""

from __future__ import annotations

from datetime import datetime, timezone

from engine.task import cues
from engine.task.verification import ProposedStructure, VerificationItem
from scripts.llm_cases import HELDOUT, TUNED


def _read(text: str, *items: VerificationItem, deadline: str | None = None, now: datetime | None = None) -> ProposedStructure:
    out = ProposedStructure()
    out.items.extend(items)
    out.final_deadline = deadline
    cues.read(text, out, now)
    return out


def _file(name: str, intent: str, path: str | None = None) -> VerificationItem:
    return VerificationItem(target_type="file", intent=intent, name=name, path=path, source="rule", intent_by="model")


def kinds(out: ProposedStructure) -> set[str]:
    return {f["kind"] for f in out.flags}


def test_combining_two_files_for_someone_says_what_it_cannot_check_and_picks_no_deadline():
    friday = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
    out = _read("There is a report.xlsx and findings.docx, find a way to combine them into a suitable output and send it to me through the message channel. Finish it today or a day after.",
                _file("report.xlsx", "update"), _file("findings.docx", "update"), deadline="today", now=friday)
    assert kinds(out) == {"cannot_check", "unnamed_result", "made_from", "ambiguous_deadline"}
    assert [i.intent for i in out.items] == ["exists", "exists"]                         # what it is made from, not what is made
    assert out.final_deadline is None                                                    # two deadlines: neither is picked
    said = next(f for f in out.flags if f["kind"] == "ambiguous_deadline")
    assert said["candidates"] == ["today", "a day after"] and "Saturday" in said["detail"]
    assert "sending it to someone" in next(f for f in out.flags if f["kind"] == "cannot_check")["detail"]


def test_a_task_built_on_another_and_a_flow_says_so():
    out = _read("The task I gave you, when you finish, use it to create the annual report into a pdf, a flow will pick it up.")
    assert kinds(out) == {"cannot_check", "unnamed_result", "waits_on_event"}
    assert next(f for f in out.flags if f["kind"] == "cannot_check")["what"] == ["another task", "a flow picking it up"]


def test_waiting_on_something_and_a_described_folder():
    out = _read("When the reports comes in, use that to create a new summary.docx immediately and put it into the document folder.", _file("summary.docx", "create", "document"))
    assert kinds(out) == {"waits_on_event", "folder_guess"}
    assert not _read("Save it", _file("a.docx", "create", "C:/docs")).flags               # a real path is not a guess


def test_check_then_make_depends_on_what_is_found():
    out = _read("Check if the annual evaluation for last year and this year are available, if not create them into docx.")
    assert kinds(out) == {"depends_on_check", "unnamed_result"}


def test_redoing_work_and_what_is_inside_a_file_are_said_and_work_on_means_it_is_there():
    out = _read("The summary.docx you did was missing key details, was utterly garbage. Redo it.", _file("summary.docx", "update"))
    assert kinds(out) == {"quality_unseen"}
    out = _read("Make sure you work on the sales.xlsx.", _file("sales.xlsx", "create"))
    assert out.items[0].intent == "update" and not out.flags
    out = _read("Check and be sure that salary column is in the report.xlsx.", _file("report.xlsx", "update"))
    assert out.items[0].intent == "exists" and kinds(out) == {"inside_file"} and "salary column" in out.flags[0]["detail"]
    assert kinds(_read("Update sales.xlsx every day", _file("sales.xlsx", "update"))) == {"recurring"}


def test_plain_descriptions_raise_nothing():
    """A check on the filter, not a target for it: on our own clean cases it should stay quiet, or it would become noise people stop reading."""
    noisy = []
    for case in [*TUNED[7:], *HELDOUT]:
        if "ambiguous_deadline" in case[2] or "every morning" in case[0]:
            continue                                                                     # (two deadlines, and a repeating job: rightly said)
        out = ProposedStructure()
        cues.read(case[0], out)
        if out.flags:
            noisy.append((case[0], sorted(kinds(out))))
    assert noisy == []


def test_a_deadline_the_person_marked_stands_whatever_the_words_say():
    out = ProposedStructure()
    out.final_deadline_at, out.deadline_source = "2026-10-16T15:00:00+00:00", "hint"
    cues.read("Finish the slides by Monday or Wednesday", out)
    assert out.final_deadline_at == "2026-10-16T15:00:00+00:00" and not out.flags
