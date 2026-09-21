"""Benchmark the Task decision graph (spec 7.2.1) against a local model.

Runs realistic task descriptions through `engine.task.llm_graph.populate` with the real
`LocalLLM` and compares the produced structure with what a careful assigner would expect.
Accuracy on THIS graph is what matters, not leaderboard standing.

    environ-engine\\Scripts\\python.exe scripts\\llm_benchmark.py [--backend llamacpp|openai|ollama]
        [--model-path models/Qwen3-0.6B-Q8_0.gguf] [--endpoint URL] [--model NAME] [-v]

Exit code 0 when every case matches, 1 otherwise. Prints a per-case table and a summary.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.llm import LocalLLM
from engine.task import llm_graph

# (description, expected items [(target_type, intent, name-substring)], expected flags kinds,
#  expected deadline substring or None, expect split)
CASES: list[tuple[str, list[tuple[str, str, str]], set[str], str | None, bool]] = [
    ("Put together the Q3 sales report as sales-q3.xlsx by Friday",
     [("file", "create", "sales-q3.xlsx")], set(), "Friday", False),
    ("Keep inventory.csv current -- update it with this week's counts",
     [("file", "update", "inventory.csv")], set(), None, False),
    ("Make sure onboarding.pdf is present on your machine before the new hire starts on Monday",
     [("file", "exists", "onboarding.pdf")], set(), "Monday", False),
    ("Use Excel to update budget.xlsx before end of day Thursday",
     [("file", "update", "budget.xlsx"), ("program", "used_with_file", "Excel")], set(), "Thursday", False),
    ("Spend the afternoon in Photoshop cleaning up the product photos",
     [("program", "used", "Photoshop")], set(), None, False),
    ("Install 7-Zip so it's available when we need it",
     [("program", "installed_available", "7-Zip")], set(), None, False),
    ("Close Outlook before you leave today",
     [("program", "closed_not_running", "Outlook")], set(), "today", False),
    ("Write the minutes into meeting-notes.docx in the Shared/Minutes folder",
     [("file", "create", "meeting-notes.docx")], set(), None, False),
    ("Finish the slides by Monday or Wednesday, whichever works",
     [], {"ambiguous_deadline"}, None, False),
    ("Update payroll.xlsx and also archive last year's invoices into archive-2024.zip",
     [("file", "update", "payroll.xlsx"), ("file", "create", "archive-2024.zip")], set(), None, True),
    ("Open the CRM and export this month's leads to leads-sept.csv",
     [("file", "create", "leads-sept.csv"), ("program", "used_with_file", "CRM")], set(), None, False),
    ("Fix the typos in handbook.docx and send it back to me by 3pm tomorrow",
     [("file", "update", "handbook.docx")], set(), "3pm", False),
    ("Please take care of the usual Friday things",
     [], {"no_target"}, None, False),
]


def check(case, structure) -> list[str]:
    _desc, items, flags, deadline, split = case
    problems: list[str] = []
    got = [(i.target_type, i.intent, i.name) for i in structure.items]
    for exp in items:
        if not any(g[0] == exp[0] and g[1] == exp[1] and exp[2].lower() in g[2].lower() for g in got):
            problems.append(f"missing item {exp}")
    extra = [g for g in got if not any(g[0] == e[0] and e[2].lower() in g[2].lower() for e in items)]
    if extra:
        problems.append(f"unexpected items {extra}")
    got_flags = {f["kind"] for f in structure.flags}
    for k in flags:
        if k not in got_flags:
            problems.append(f"missing flag {k}")
    if items and "no_target" in got_flags:
        problems.append("flagged no_target despite targets")
    if deadline and (structure.final_deadline is None or deadline.lower() not in structure.final_deadline.lower()):
        problems.append(f"deadline: expected ~{deadline!r}, got {structure.final_deadline!r}")
    if not deadline and structure.final_deadline and "ambiguous_deadline" not in flags:
        problems.append(f"unexpected deadline {structure.final_deadline!r}")
    if split and not structure.proposed_split:
        problems.append("multi-task split not proposed")
    if not split and structure.proposed_split:
        problems.append("split proposed for a single task")
    return problems


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="llamacpp")
    ap.add_argument("--model-path", default="models/Qwen3-0.6B-Q8_0.gguf")
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="qwen3:0.6b")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    llm = LocalLLM(args.backend, model_path=args.model_path, endpoint=args.endpoint, model=args.model)
    print(f"backend: {llm.describe()}  available={llm.available}")
    if not llm.available:
        return 2
    passed = 0
    t0 = time.perf_counter()
    for case in CASES:
        calls_before = llm.calls
        t1 = time.perf_counter()
        structure = await llm_graph.populate(llm, case[0])
        dt = time.perf_counter() - t1
        problems = check(case, structure)
        ok = not problems
        passed += ok
        print(f"[{'OK ' if ok else 'BAD'}] {dt:5.1f}s {llm.calls - calls_before:2d} calls  {case[0]}")
        if args.verbose or not ok:
            print(f"      items={[(i.target_type, i.intent, i.name, i.path) for i in structure.items]}")
            print(f"      deadline={structure.final_deadline!r} flags={structure.flags} split={bool(structure.proposed_split)}")
            for p in problems:
                print(f"      - {p}")
    total = time.perf_counter() - t0
    print(f"\n{passed}/{len(CASES)} cases correct, {llm.calls} model calls, {total:.1f}s total "
          f"({total / max(llm.calls, 1):.2f}s per call)")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
