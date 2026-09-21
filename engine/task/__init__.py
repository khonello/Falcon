"""Task (task-natural-combo.md; spec 7.2).

A unit of work assigned to a user account. No task directory -- targets are tracked by identity
through the Global File Index. Verification is the anchor; only manual verification by the
assigner closes a task. Governing rule: the LLM proposes and surfaces ambiguity, never decides.

    tasks        -- lifecycle handlers (create / review / assign / start / verify / close)
    verification -- verification items, Intent, collision check, stack status
    llm_graph    -- decomposed question graph that populates the structure from plain language
    expectation  -- soft progress signals derived from targets (never completion)
"""

from engine.task import expectation, tasks, verification  # noqa: F401
