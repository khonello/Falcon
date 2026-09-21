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
    # Two file targets joined by "and also" -> a concrete split proposal, never a silent merge.
    s3 = await llm_graph.populate(ScriptedLLM({}), "Update payroll.xlsx and also zip the logs into logs.zip")
    assert [(i.intent, i.name) for i in s3.items] == [("update", "payroll.xlsx"), ("create", "logs.zip")]
    assert s3.proposed_split and [p["targets"] for p in s3.proposed_split] == [["payroll.xlsx"], ["logs.zip"]]


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


# --- lifecycle ----------------------------------------------------------------------------------

async def _index(engine, pc_id: int, path: str, name: str, h: str = "h") -> int:
    return await engine.db.file_index.upsert(pc_id, path, name, h, "common", None, "event")


async def test_propose_reports_collisions_and_llm_state(engine, org, connect):
    a1 = await connect("cid-a1")
    engine.llm = ScriptedLLM({})
    await _index(engine, org["w1_pc"], "C:/docs/report.docx", "report.docx")
    res = await a1.ok("task.propose", {"description": "write report.docx", "assignee_account_id": org["w1"]})
    assert res["items"][0]["intent"] == "create" and res["collisions"][0]["name"] == "report.docx"
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


async def test_super_user_assigns_to_admin_only(engine, org, connect):
    su = await connect("cid-su")
    assert await su.err("task.create", {"assignee_account_id": org["w1"], "description": "x",
                                        "verification_mode": "none", "confirm_none": True}) == "forbidden"
    res = await su.ok("task.create", {"assignee_account_id": org["a1"], "description": "department task",
                                      "verification_mode": "none", "confirm_none": True})
    assert res["task"]["assignee_account_id"] == org["a1"]
    assert len((await su.ok("task.list"))["tasks"]) == 1
