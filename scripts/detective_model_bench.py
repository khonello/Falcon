"""What is the local model worth to Detective? Measured, with and without it.

    environ-engine\\Scripts\\python.exe scripts\\detective_model_bench.py [--no-model]

Two jobs (engine/detective/labels.py), one used and one measured-and-left-out, each scored against what a careful person would say:
  1. Does a rename make a file look like a different kind of file?  Rules only (the extension rule), the model alone, and the two together.
  2. Which description fits a case's story?  The model's reading against the intent the rules concluded, on the scripted scenarios.

Two suites, and the split is the point (as in scripts/llm_cases.py): TUNED is what the prompts and rules were written against and is a regression guard;
HELDOUT was written afterwards and must never be tuned against -- fix only what is wrong by the system's own rules, then move the case into TUNED and write
a fresh held-out one.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from detective_scenarios import SCENARIOS, play

from common.detective import disguised
from engine.detective import labels
from engine.llm import LocalLLM

# (old name, new name, is it made to look like a different kind of file?)
TUNED = [
    ("payroll.xlsx", "vacation-photo.jpg", True), ("budget.xlsx", "IMG_2041.jpg", True), ("payroll-q3.xlsx", "notes.txt.dll", True), ("customers.xlsx", "holiday-pics.zip", True), ("board-minutes.docx", "cat.png", True),
    ("report-draft.docx", "report-final.docx", False), ("budget.xlsx", "budget-2026.xlsx", False), ("notes.txt", "meeting-notes.txt", False), ("data.csv", "data-clean.csv", False),
]
HELDOUT = [
    ("hr-review.docx", "song.mp3", True), ("recipes-list.docx", "podcast.m4a", True), ("salaries.csv", "windows-update.dat", True), ("clients.xlsx", "wallpaper.bmp", True),
    ("contract.pdf", "contract-signed.pdf", False), ("scan.pdf", "invoice-0042.pdf", False), ("photo.jpg", "photo-edited.jpg", False), ("plan.docx", "plan-v2.docx", False),
]
# (scenario, the description a careful person would pick from labels.OPINION)
OPINIONS = [
    ("leak", "taking data out"), ("patient", "taking data out"), ("ransom", "wrecking"), ("wiped", "wrecking"), ("log_cleared", "covering up"),
    ("goes_dark", "hiding"), ("snooping", "spying"),
]


async def disguise_scores(llm: LocalLLM | None, suite: list[tuple[str, str, bool]]) -> tuple[int, int, int, int]:
    rules = model = both = 0
    for old, new, truth in suite:
        by_rule = disguised(old, new)
        by_model = await labels.looks_disguised(llm, old, new) if llm is not None else None
        rules += by_rule == truth
        model += (by_model if by_model is not None else False) == truth
        both += (by_rule or bool(by_model)) == truth
    return rules, model, both, len(suite)


async def opinion_scores(llm: LocalLLM) -> tuple[int, list[str]]:
    hits, misses = 0, []
    for name, want in OPINIONS:
        det, _ = play(SCENARIOS[name]())
        cases = det.open_cases()
        if not cases:
            misses.append(f"{name}: no case")
            continue
        said = await labels.second_opinion(llm, cases[0].story())
        mapped = next((k for k, v in labels.OPINION.items() if v == said), None) if said is not None else None
        if mapped == want:
            hits += 1
        else:
            misses.append(f"{name}: wanted {want}, the model said {mapped}")
    return hits, misses


async def main(argv: list[str]) -> None:
    llm = None if "--no-model" in argv else LocalLLM("llamacpp", model_path="models/Qwen3-1.7B-Q8_0.gguf")
    if llm is not None and not llm.available:
        print("the model is not available:", llm.describe())
        return
    started = time.monotonic()
    for title, suite in (("TUNED (regression guard)", TUNED), ("HELDOUT (the measurement; never tune against it)", HELDOUT)):
        rules, model, both, n = await disguise_scores(llm, suite)
        print(f"{title}: does a rename make a file look like a different kind?  rules alone {rules}/{n}"
              + (f"   model alone {model}/{n}   rules + model {both}/{n}" if llm is not None else ""))
    if llm is not None:
        hits, misses = await opinion_scores(llm)
        print(f"second opinion on a case: the model agrees with a careful reading on {hits}/{len(OPINIONS)}")
        for m in misses:
            print("   ", m)
        print(f"{llm.stats()['calls']} model calls in {time.monotonic() - started:.0f}s")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
