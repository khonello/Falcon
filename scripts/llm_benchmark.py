"""Benchmark the Task decision graph (spec 7.2.1) against a local model.

Runs realistic task descriptions through `engine.task.llm_graph.populate` and compares the
produced structure with what a careful assigner would expect. Accuracy on THIS graph is what
matters, not leaderboard standing.

Two suites (see scripts/llm_cases.py), and the difference between them is the point:
  tuned    the cases the graph was written against -- a regression guard. Must stay 100%.
  heldout  cases the graph has never been tuned against -- the actual measurement. Reported
           as a score; do not "fix" the graph until it passes, or it stops measuring.

    environ-engine\\Scripts\\python.exe scripts\\llm_benchmark.py [--suite tuned|heldout|all]
        [--backend llamacpp|openai|ollama] [--model-path models/Qwen3-1.7B-Q8_0.gguf]
        [--endpoint URL] [--model NAME] [--floor N] [--no-model] [-v]

`--no-model` answers every question with None instead of calling the model, which measures
how much the model contributes at all: whatever still passes is mechanical, not the model.

Exit code 0 when the tuned suite is perfect and the held-out score is at least `--floor`.
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
from scripts.llm_cases import HELDOUT, SUITES, TUNED, Case

CASES = TUNED  # the name the suite was known by before the split


class NoModel:
    """Every question unanswered. What still passes is the graph's mechanical reading."""

    calls = 0

    async def yes_no(self, question: str, text: str) -> None:
        self.calls += 1

    async def choose(self, question: str, text: str, options: list[str]) -> None:
        self.calls += 1

    async def extract(self, what: str, text: str) -> None:
        self.calls += 1


def check(case: Case, structure) -> list[str]:
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


async def run_suite(llm, cases: list[Case], label: str, verbose: bool) -> int:
    print(f"\n--- {label} ({len(cases)} cases) ---")
    passed = 0
    calls_at_start = llm.calls
    t0 = time.perf_counter()
    for case in cases:
        calls_before = llm.calls
        t1 = time.perf_counter()
        structure = await llm_graph.populate(llm, case[0])
        dt = time.perf_counter() - t1
        problems = check(case, structure)
        ok = not problems
        passed += ok
        print(f"[{'OK ' if ok else 'BAD'}] {dt:5.1f}s {llm.calls - calls_before:2d} calls  {case[0]}")
        if verbose or not ok:
            print(f"      items={[(i.target_type, i.intent, i.name, i.path) for i in structure.items]}")
            print(f"      deadline={structure.final_deadline!r} flags={structure.flags} "
                  f"split={bool(structure.proposed_split)}")
            for p in problems:
                print(f"      - {p}")
    total = time.perf_counter() - t0
    calls = llm.calls - calls_at_start
    print(f"{label}: {passed}/{len(cases)} correct, {calls} model calls, {total:.1f}s "
          f"({total / max(calls, 1):.2f}s per call)")
    return passed


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="all", choices=("tuned", "heldout", "all"))
    ap.add_argument("--backend", default="llamacpp")
    ap.add_argument("--model-path", default="models/Qwen3-1.7B-Q8_0.gguf")
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="qwen3:1.7b")
    ap.add_argument("--floor", type=int, default=0,
                    help="fail if fewer than N held-out cases pass (0 = report only)")
    ap.add_argument("--no-model", action="store_true",
                    help="answer nothing instead of calling the model, to measure its contribution")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.no_model:
        llm: object = NoModel()
        print("backend: none (every question unanswered)")
    else:
        llm = LocalLLM(args.backend, model_path=args.model_path, endpoint=args.endpoint, model=args.model)
        print(f"backend: {llm.describe()}  available={llm.available}")
        if not llm.available:
            return 2

    suites = [(k, SUITES[k]) for k in (("tuned", "heldout") if args.suite == "all" else (args.suite,))]
    scores = {name: await run_suite(llm, cases, name, args.verbose) for name, cases in suites}

    print()
    failed = False
    if "tuned" in scores:
        print(f"tuned   {scores['tuned']}/{len(TUNED)}   (regression guard -- must be perfect)")
        failed |= scores["tuned"] != len(TUNED) and not args.no_model
    if "heldout" in scores:
        print(f"heldout {scores['heldout']}/{len(HELDOUT)}   (the measurement -- do not tune against it)")
        failed |= scores["heldout"] < args.floor
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
