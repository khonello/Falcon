"""The audit log in words (the user, 10 Nov 2026: "Deviation raised, just that, how is someone expected to understand this").

Every action the Engine records has an entry in `engine.console.feed.ENTRIES` -- a kind, a level and a sentence -- so nothing falls back
to its code name; the machinery is left out of the log unless Everything is asked for; a line that repeats another is left out; a flow's
files are folded into one line; and the things an entry is about are named, not numbered.
"""

from __future__ import annotations

import ast
from pathlib import Path

from engine.console.feed import ENTRIES, KINDS, W, fold
from tests.conftest import requires_db

ROOT = Path(__file__).resolve().parent.parent


def _recorded() -> set[str]:
    """Every action type the Engine's code passes to `audit.record`, both arms of a choice included."""
    found: set[str] = set()

    def names(a: ast.AST) -> list[str]:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return [a.value]
        if isinstance(a, ast.IfExp):
            return names(a.body) + names(a.orelse)
        return []
    for p in (ROOT / "engine").rglob("*.py"):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "record" and len(n.args) >= 2:
                found.update(names(n.args[1]))
    return found


def test_everything_the_engine_records_has_words_of_its_own():
    missing = sorted(_recorded() - set(ENTRIES))
    assert not missing, f"recorded with no sentence in engine/console/feed.py ENTRIES: {missing}"
    # the two that are spelled with an f-string
    assert {"task.deadline_soft", "task.deadline_final", "detective.dismissed", "detective.confirmed"} <= set(ENTRIES)


def test_each_sentence_reads_as_words_even_with_nothing_to_go_on():
    for action, (kind, level, say) in ENTRIES.items():
        assert kind in KINDS and level in ("worth", "done", "routine"), action
        text = say(W({"detail": {}}, None, {}, {}, 0))
        # it starts as a sentence does, or with the name of the thing it is about (a flow is called what its Admin called it)
        assert text and (text[0].isupper() or text.startswith(("a flow ", "flow "))), (action, text)
        assert action not in text and "_" not in text and "None" not in text, (action, text)


def test_a_flow_s_files_fold_into_one_line_per_flow_and_hour():
    at = "2026-11-10T10:00:00+00:00"
    rows = [{"action_type": "flow.synced", "what": f"reports copied {f} to WS-D2", "pc_id": 3, "host": "WS-D2", "at": at} for f in ("a.csv", "b.csv", "c.csv")]
    rows.append({"action_type": "flow.synced", "what": "archive copied d.txt to WS-D1", "pc_id": 1, "host": "WS-D1", "at": at})
    out = fold(rows)
    assert [e["what"] for e in out] == ["reports copied 3 files to WS-D2: a.csv, b.csv and 1 more", "archive copied d.txt to WS-D1"]


@requires_db
async def test_the_log_names_things_leaves_out_the_machinery_and_folds_the_rest(engine, org, connect):
    a1 = await connect("cid-a1")
    db = engine.db
    task_id = await db.pool.fetchval(
        "INSERT INTO tasks (assigner_account_id, assignee_account_id, description_raw, status, verification_mode) "
        "VALUES ($1, $2, 'Write the weekly sales summary', 'active', 'stack') RETURNING id", org["a1"], org["w1"])
    await engine.audit.record(None, "task.created", target_type="tasks", target_id=task_id, pc_id=org["w1_pc"],
                              detail={"assignee_account_id": org["w1"], "items": 1, "verification_mode": "stack"})
    await engine.audit.record(None, f"task.deadline_{'final'}", target_type="tasks", target_id=task_id, pc_id=org["w1_pc"])
    for name in ("a.csv", "b.csv"):
        await engine.audit.record(None, "flow.synced", target_type="flow_destinations", target_id=None, pc_id=org["w1_pc"],
                                  detail={"flow_id": 999, "relative_path": name})
    shown = (await a1.ok("audit.events", {}))["events"]
    whats = [e["what"] for e in shown]
    assert any(w.startswith("Gave ") and w.endswith("a task: Write the weekly sales summary") for w in whats), whats
    assert "The task “Write the weekly sales summary” passed its deadline" in whats
    assert not any(e["action_type"] in ("flow.synced", "auth.connected") for e in shown)               # the machinery is under Everything
    late = next(e for e in shown if e["action_type"] == "task.deadline_final")
    assert late["worth"] and late["level"] == "worth" and late["actor"] == "Falcon"
    everything = (await a1.ok("audit.events", {"routine": True}))["events"]
    assert any(e["action_type"] == "auth.connected" for e in everything)
    assert any(e["what"] == "flow 999 copied 2 files to FIN-01: b.csv, a.csv" for e in everything), [e["what"] for e in everything]


@requires_db
async def test_a_machine_s_other_name_is_not_checked_in_this_version(engine, org, connect):
    """Postponed to version 2 (ENGINE-GAPS 30): a machine connecting under another name records nothing."""
    await connect("cid-w2", hostname="SOMEWHERE-ELSE")
    assert not await engine.db.audit.deviations()
    assert not await engine.db.pool.fetchval("SELECT count(*) FROM issues WHERE source_table = 'hostname_mismatch'")


@requires_db
async def test_a_deadline_is_said_once_even_when_the_engine_starts_again(engine, org):
    from engine.task.tasks import _deadline_job

    task_id = await engine.db.pool.fetchval(
        "INSERT INTO tasks (assigner_account_id, assignee_account_id, description_raw, status, verification_mode, final_deadline_at) "
        "VALUES ($1, $2, 'Send the stock count', 'active', 'stack', now() - interval '1 hour') RETURNING id", org["a1"], org["w1"])
    for _ in range(3):                                         # the job, as each start of the Engine re-arms it
        await _deadline_job(engine, task_id, "final")()
    n = await engine.db.pool.fetchval("SELECT count(*) FROM audit_log WHERE action_type = 'task.deadline_final' AND target_id = $1", str(task_id))
    assert n == 1
