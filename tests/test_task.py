"""Task end-to-end over the socket (skipped without FALCON_TEST_DATABASE_URL).

Pins the governing rules from task-natural-combo.md: propose never commits; 'none' must be
explicit; Create-intent collisions are surfaced not resolved; only the assigner's manual
verification completes; the assignee can start and watch; expectation signals ride the
file-index stream; deadlines are scheduled events that push the pulsing indicator.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from engine.database import _now
from engine.llm import LocalLLM
from engine.task import llm_graph
from tests.conftest import requires_db

pytestmark = requires_db


class ScriptedLLM(LocalLLM):
    """Deterministic stand-in: answers by keyword so the decision graph can be exercised."""

    def __init__(self, answers: dict[str, object]) -> None:
        super().__init__("ollama")
        self.answers = answers
        self.asked: list[str] = []

    @property
    def available(self) -> bool:
        return True

    async def yes_no(self, question: str, text: str) -> bool | None:
        self.asked.append(question)
        return self.answers.get(question)  # type: ignore[return-value]

    async def choose(self, question: str, text: str, options: list[str]) -> str | None:
        self.asked.append(question)
        return self.answers.get(question)  # type: ignore[return-value]

    async def extract(self, what: str, text: str) -> str | None:
        self.asked.append(what)
        return self.answers.get(what)  # type: ignore[return-value]


# --- the decision graph (no DB needed, but grouped here) ----------------------------------------

async def test_graph_populates_a_clean_structure():
    llm = ScriptedLLM({
        "the name of the software program or application mentioned": "Excel",
        "What should happen with the program Excel?": "use it",
    })
    s = await llm_graph.populate(llm, "Use Excel to update budget.xlsx by Friday")
    assert [(i.target_type, i.intent, i.name) for i in s.items] == [("file", "update", "budget.xlsx"),
                                                                     ("program", "used_with_file", "Excel")]
    assert s.items[1].linked_item_index == 0 and s.final_deadline == "by Friday" and not s.needs_assigner()
    # The model asked only what the graph could not settle mechanically.
    assert set(llm.asked) == {"the name of the software program or application mentioned",
                              "What should happen with the program Excel?"}


async def test_graph_flags_instead_of_guessing():
    llm = ScriptedLLM({
        "the name of the software program or application mentioned": "Excel",
        "What should happen with the program Excel?": "use it on the file",
    })
    s = await llm_graph.populate(llm, "Use Excel by Monday or Wednesday, and also tidy the archive")
    kinds = sorted(f["kind"] for f in s.flags)
    assert kinds == ["ambiguous_deadline", "contradiction", "no_target"]
    # A hallucinated program name (not in the text) is rejected, never accepted.
    s2 = await llm_graph.populate(ScriptedLLM({"the name of the software program or application mentioned": "Word"}),
                                  "tidy the archive")
    assert s2.items == [] and {f["kind"] for f in s2.flags} == {"no_target"}
    # Two file targets joined by "and also" stay one task with both targets: a description is always one task.
    s3 = await llm_graph.populate(ScriptedLLM({}), "Update payroll.xlsx and also zip the logs into logs.zip")
    assert [(i.intent, i.name) for i in s3.items] == [("update", "payroll.xlsx"), ("create", "logs.zip")]
    assert not hasattr(s3, "proposed_split") and s3.flags == []


def test_graph_mechanical_helpers():
    assert llm_graph.find_file_names("send sales-q3.xlsx and notes.md; not v1.2 or 3.14") == ["sales-q3.xlsx", "notes.md"]
    assert llm_graph.find_path("Write the minutes into meeting-notes.docx in the Shared/Minutes folder",
                               "meeting-notes.docx") == "Shared/Minutes"
    assert llm_graph.find_deadlines("finish by 3pm tomorrow") == ["by 3pm tomorrow"]
    assert llm_graph.find_deadlines("Close Outlook before you leave today") == ["today"]
    assert llm_graph.find_deadlines("the usual Friday things") == []
    assert llm_graph.file_intent_cue("Update payroll.xlsx and also archive invoices into a.zip", "a.zip") == "create"
    assert llm_graph.file_intent_cue("Update payroll.xlsx and also archive invoices into a.zip", "payroll.xlsx") == "update"
    assert llm_graph.file_intent_cue("Make sure onboarding.pdf is present on your machine", "onboarding.pdf") == "exists"
    assert llm_graph.file_intent_cue("Look at data.csv", "data.csv") is None
    assert llm_graph.program_candidates("Install 7-Zip so it's available by Friday", []) == ["7-Zip"]
    assert llm_graph.program_candidates("Close Outlook today", []) == ["Outlook"]
    assert llm_graph.program_candidates("Put the Q3 report in Shared/Minutes", []) == []
    assert llm_graph.program_intent_cue("Install 7-Zip so it is available", "7-Zip") == "installed_available"
    assert llm_graph.program_intent_cue("Close Outlook before you leave", "Outlook") == "closed_not_running"
    assert llm_graph.program_intent_cue("Use Excel to update budget.xlsx", "Excel") is None


def test_graph_reads_running_source_and_bare_times():
    """The corrections a held-out pass forced: an Intent for 'still running', a file the work
    reads FROM, 24-hour deadlines, a bare 'then' split, and nouns that are not programs."""
    # "still running" is the opposite check from "close it" -- it used to become Close.
    assert llm_graph.program_intent_cue("Check whether Slack is still running", "Slack") == "running"
    assert llm_graph.program_intent_cue("Keep Jenkins running while the build finishes", "Jenkins") == "running"
    assert llm_graph.program_intent_cue("Close Outlook before you leave", "Outlook") == "closed_not_running"
    # A source file must be there, not be produced.
    assert llm_graph.file_intent_cue("Convert scan.tiff to scan.pdf", "scan.tiff") == "exists"
    assert llm_graph.file_intent_cue("Get the invoices out of invoices.zip", "invoices.zip") == "exists"
    assert llm_graph.file_intent_cue("Confirm nda.pdf is sitting in Legal/Signed", "nda.pdf") == "exists"
    # 24-hour times and a deadline with no by/before in front of it.
    assert llm_graph.find_deadlines("Deadline is 17:00 sharp") == ["Deadline is 17:00"]
    assert llm_graph.find_deadlines("hand it in by 09:30 tomorrow") == ["by 09:30 tomorrow"]
    assert llm_graph.find_deadlines("finish by 3pm tomorrow") == ["by 3pm tomorrow"]
    # A date inside a file name is part of the name, however verbatim it is.
    assert llm_graph._inside_file_name("2026-09-28", "back it up to backup-2026-09-28.bak")
    assert not llm_graph._inside_file_name("2026-09-28", "backup-2026-09-28.bak by 2026-09-28")
    # Capitalised nouns that are not programs.
    assert llm_graph.program_candidates("Finish the audit by the 14th", []) == []
    assert llm_graph.program_candidates("Confirm the signed NDA nda-acme.pdf is there", ["nda-acme.pdf"]) == []


async def test_graph_keeps_a_target_it_cannot_read():
    """An unsettled Intent is 'surface to the assigner', not 'nothing was found' -- the flag
    names the target so the assigner sees what the graph saw."""
    s = await llm_graph.populate(ScriptedLLM({}), "Look at data.csv")
    assert s.items == []  # nothing is guessed
    flag = next(f for f in s.flags if f["kind"] == "unclear")
    assert flag["target"] == "data.csv" and flag["options"] == ["create", "update", "exists"]
    assert not any(f["kind"] == "no_target" for f in s.flags)


async def test_choose_prefers_the_longest_option_it_contains():
    """'use it' is a substring of 'use it on the file': a correct answer must not read as two."""
    llm = LocalLLM("ollama")
    options = ["use it", "use it on the file", "close it"]
    assert await _chosen(llm, "use it on the file", options) == "use it on the file"
    assert await _chosen(llm, "close it", options) == "close it"
    # A model that echoes the option list back has not chosen anything.
    assert await _chosen(llm, "use it | close it", options) is None


async def _chosen(llm: LocalLLM, answer: str, options: list[str]) -> str | None:
    async def _ask(prompt: str, *, max_tokens: int) -> str:
        return answer
    llm._ask = _ask  # type: ignore[method-assign]
    return await llm.choose("q", "text", options)


# --- lifecycle ----------------------------------------------------------------------------------

async def _index(engine, pc_id: int, path: str, name: str, h: str = "h") -> int:
    return await engine.db.file_index.upsert(pc_id, path, name, h, "common", None, "event")


async def test_propose_reports_collisions_and_llm_state(engine, org, connect):
    a1 = await connect("cid-a1")
    engine.llm = ScriptedLLM({})
    await _index(engine, org["w1_pc"], "C:/docs/report.docx", "report.docx")
    res = await a1.ok("task.propose", {"description": "write report.docx", "assignee_account_id": org["w1"]})
    assert res["items"][0]["intent"] == "create" and res["collisions"][0]["name"] == "report.docx"
    # the existing file is named by its index id, so "it means the existing file" can bind an Update to it
    assert res["collisions"][0]["existing"][0]["file_index_id"]
    assert res["needs_assigner"] is True and res["llm_available"] is True
    # Scope: Admin cannot propose for another department's worker or for an Admin.
    assert await a1.err("task.propose", {"description": "x", "assignee_account_id": org["a2"]}) == "forbidden"


async def test_create_rules_and_full_lifecycle(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    su = await connect("cid-su")
    base = {"assignee_account_id": org["w1"], "description": "write report.docx"}

    # 'none' must be explicit; a stack needs items; bad items are refused.
    assert await a1.err("task.create", {**base, "verification_mode": "none"}) == "invalid"
    assert await a1.err("task.create", {**base, "verification_mode": "stack", "items": []}) == "invalid"
    assert await a1.err("task.create", {**base, "verification_mode": "stack",
                                        "items": [{"target_type": "file", "intent": "used", "name": "x"}]}) == "invalid"
    # exists/update need an indexed file on the assignee's PC.
    other_pc_file = await _index(engine, org["w2_pc"], "C:/x/data.csv", "data.csv")
    assert await a1.err("task.create", {**base, "verification_mode": "stack",
                                        "items": [{"target_type": "file", "intent": "update", "name": "data.csv",
                                                   "file_index_id": other_pc_file}]}) == "invalid"
    # Create-intent collision is surfaced, resolved by a path.
    await _index(engine, org["w1_pc"], "C:/old/report.docx", "report.docx")
    items = [{"target_type": "file", "intent": "create", "name": "report.docx"}]
    assert await a1.err("task.create", {**base, "verification_mode": "stack", "items": items}) == "conflict"
    items[0]["path"] = "C:/new"
    items.append({"target_type": "program", "intent": "used_with_file", "name": "Word", "linked_item_index": 0})
    soft, final = _now() + timedelta(hours=1), _now() + timedelta(hours=2)
    res = await a1.ok("task.create", {**base, "verification_mode": "stack", "items": items,
                                      "soft_deadline_at": soft.isoformat(), "final_deadline_at": final.isoformat()})
    task = res["task"]
    tid = task["id"]
    assert task["status"] == "active" and len(task["items"]) == 2
    assert task["items"][1]["linked_file_verification_item_id"] == task["items"][0]["id"]
    assert "task.assigned" in w1.push_types(await w1.drain_pushes())
    assert f"task.{tid}.deadline_soft" in engine.scheduler._tasks

    # Visibility: assignee, assigner, Super User, same-department Admin; not another worker.
    for c in (a1, w1, su):
        assert (await c.ok("task.get", {"task_id": tid}))["task"]["id"] == tid
    assert await w2.err("task.get", {"task_id": tid}) == "not_found"
    assert [t["id"] for t in (await w1.ok("task.list"))["tasks"]] == [tid]
    # the list carries each task's checks, so "0 of 2 checks passed" needs no task.get
    listed = (await a1.ok("task.list"))["tasks"][0]
    assert (listed["checks_total"], listed["checks_passed"]) == (2, 0)

    # Only the assignee starts; only the assigner verifies; the assignee never can.
    assert await a1.err("task.start", {"task_id": tid}) == "not_found"
    assert await w1.err("task.verify", {"task_id": tid, "outcome": "complete"}) == "forbidden"
    await w1.ok("task.start", {"task_id": tid})
    assert "task.started" in a1.push_types(await a1.drain_pushes())
    assert (await a1.ok("task.get", {"task_id": tid}))["task"]["status"] == "in_progress"

    # The file appears on the worker's PC under the given path -> create item binds and passes.
    await w1.ok("index.event", {"event": {"op": "create", "path": "C:/new/report.docx", "hash": "abc"}})
    pushes = a1.push_types(await a1.drain_pushes())
    assert "task.stack" in pushes
    stack = (await a1.ok("task.stack", {"task_id": tid}))["items"]
    assert stack[0]["status"] == "passed" and stack[1]["status"] == "pending"
    # Program signal with the file open -> used_with_file passes.
    await w1.ok("task.program_signal", {"task_id": tid, "item_id": stack[1]["id"], "running": True, "active": True,
                                        "open_files": ["C:\\new\\report.docx"]})
    stack = (await a1.ok("task.stack", {"task_id": tid}))["items"]
    assert stack[1]["status"] == "passed"
    # Stack passing does NOT complete the task -- only manual verification does.
    assert (await a1.ok("task.get", {"task_id": tid}))["task"]["status"] == "in_progress"

    await a1.ok("task.verify", {"task_id": tid, "outcome": "incomplete"})
    assert "task.incomplete" in w1.push_types(await w1.drain_pushes())
    assert (await a1.ok("task.get", {"task_id": tid}))["task"]["status"] == "in_progress"
    await a1.ok("task.verify", {"task_id": tid, "outcome": "complete"})
    assert "task.completed" in w1.push_types(await w1.drain_pushes())
    done = (await a1.ok("task.get", {"task_id": tid}))["task"]
    assert done["status"] == "completed" and done["manual_verification"]["outcome"] == "complete"
    assert f"task.{tid}.deadline_soft" not in engine.scheduler._tasks
    assert (await w1.ok("task.list"))["tasks"] == []
    assert await a1.err("task.verify", {"task_id": tid, "outcome": "complete"}) == "conflict"


async def test_deadline_fires_as_event_and_pushes_indicator(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    soon = _now() + timedelta(milliseconds=200)
    res = await a1.ok("task.create", {"assignee_account_id": org["w1"], "description": "quick", "verification_mode": "none",
                                      "confirm_none": True, "soft_deadline_at": soon.isoformat()})
    await asyncio.sleep(0.5)
    for c in (a1, w1):
        deadline = next(p for p in await c.drain_pushes() if p.type == "task.deadline")
        assert deadline.payload == {"task_id": res["task"]["id"], "kind": "soft", "indicator": "deadline_reached"}
    audit = await engine.db.audit.recent(action_prefix="task.deadline")
    assert audit and audit[0]["target_id"] == str(res["task"]["id"])


async def test_folders_are_offered_to_pick_never_typed(engine, org, connect):
    """index.folders: a machine's indexed folders, so a flow's source is chosen, not typed as a path. Scoped: an
    Admin sees folders only on machines in their own department."""
    await _index(engine, org["w1_pc"], "C:/docs/q3/report.docx", "report.docx")
    await _index(engine, org["w1_pc"], r"C:\docs\q3\data.xlsx", "data.xlsx")
    await _index(engine, org["w1_pc"], "C:/raw/in.pdf", "in.pdf")
    a1 = await connect("cid-a1")
    got = await a1.ok("index.folders", {"pc_id": org["w1_pc"]})
    by = {f["path"]: f for f in got["folders"]}
    assert by["C:/docs/q3"]["files"] == 2 and by["C:/docs/q3"]["name"] == "q3" and "C:/raw" in by
    a2 = await connect("cid-a2")
    assert await a2.err("index.folders", {"pc_id": org["w1_pc"]}) == "forbidden"


async def test_searching_the_index_returns_files_with_their_times(engine, org, connect):
    """Found trying Task live: index.search (the Task page's 'find an existing file') returned raw rows and failed on their timestamps."""
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await w1.ok("index.event", {"event": {"op": "create", "path": "C:/docs/budget-2026.txt", "hash": "H"}})
    found = (await a1.ok("index.search", {"query": "budget-2026"}))["results"]
    assert [f["filename"] for f in found] == ["budget-2026.txt"]


async def test_a_deadline_the_console_writes_is_understood(engine, org, connect):
    """Found filling the New task form live: JavaScript writes 2026-10-17T17:00:00.000Z, which Python 3.10's fromisoformat refuses, so every deadline
    set in the console failed with "must be ISO 8601"."""
    a1 = await connect("cid-a1")
    soft = (_now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    final = (_now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    res = await a1.ok("task.create", {"assignee_account_id": org["w1"], "description": "x", "verification_mode": "none", "confirm_none": True,
                                      "soft_deadline_at": soft, "final_deadline_at": final})
    assert res["task"]["final_deadline_at"] is not None and res["task"]["soft_deadline_at"] is not None


async def test_an_admins_own_to_dos_are_theirs_alone(engine, org, connect):
    """A to-do is a line, when it is due, when it was done (ENGINE-GAPS #17). Only its owner sees, adds, ticks and untick it; it reaches
    the strip when due within a day or past, and the Calendar and the Overview when it has a date. Not a Task: no checks, no assignee."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w = await connect("cid-w1")
    assert await w.err("todo.list") == "forbidden" and await w.err("todo.add", {"text": "x"}) == "forbidden"
    for bad in ({"text": "   "}, {"text": "x" * 301}, {"text": "x", "due_at": "friday"}):
        assert await a1.err("todo.add", bad) == "invalid", bad

    late = (await a1.ok("todo.add", {"text": "Renew the  backup licence", "due_at": (now - timedelta(hours=2)).isoformat()}))["todo"]
    soon = (await a1.ok("todo.add", {"text": "Order two docking stations", "due_at": (now + timedelta(hours=5)).isoformat()}))["todo"]
    later = (await a1.ok("todo.add", {"text": "Plan the printer swap", "due_at": (now + timedelta(days=9)).isoformat()}))["todo"]
    undated = (await a1.ok("todo.add", {"text": "Tidy the cable drawer"}))["todo"]
    assert late["text"] == "Renew the backup licence" and late["overdue"] and late["on_strip"] and not undated["on_strip"]
    assert "todo.changed" in a1.push_types(await a1.drain_pushes())

    mine = await a1.ok("todo.list")
    assert [t["id"] for t in mine["todos"]] == [late["id"], soon["id"], later["id"], undated["id"]]   # soonest first, no date last
    assert [t["id"] for t in mine["strip"]] == [late["id"], soon["id"]] and mine["open"] == 4

    # Another Admin sees none of it and cannot tick it.
    assert (await a2.ok("todo.list"))["todos"] == []
    assert await a2.err("todo.done", {"todo_id": late["id"]}) == "not_found"

    ticked = (await a1.ok("todo.done", {"todo_id": late["id"]}))["todo"]
    assert ticked["done"] and not ticked["on_strip"]
    assert [t["id"] for t in (await a1.ok("todo.list", {"done_days": 0}))["todos"]] == [soon["id"], later["id"], undated["id"]]
    assert (await a1.ok("todo.list"))["todos"][-1]["id"] == late["id"]                                # done ones after, this week's
    back = (await a1.ok("todo.done", {"todo_id": late["id"], "done": False}))["todo"]
    assert not back["done"] and back["overdue"]

    cal = await a1.ok("calendar.board", {"days": 30})
    assert {i["title"] for i in cal["items"] if i["kind"] == "todo"} == {late["text"], soon["text"], later["text"]}
    assert not [i for i in (await a2.ok("calendar.board"))["items"] if i["kind"] == "todo"]
    waiting = (await a1.ok("overview.admin"))["waiting"]
    assert waiting["todos_due"] == 2 and waiting["todos_overdue"] == 1
