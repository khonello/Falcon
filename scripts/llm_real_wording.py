"""The Task graph on REAL task descriptions, for a person to read. The benchmark's cases were written by us; this is the only way to find out how
the model does on the way people at a customer actually write.

Put real descriptions in a text file, one per line (blank lines and lines starting with # are skipped). Keep the file under data/, which git
ignores: real descriptions name real people and files. Then:

    environ-engine\\Scripts\\python.exe scripts\\llm_real_wording.py data\\real-task-descriptions.txt [--model-path models\\Qwen3-1.7B-Q8_0.gguf] [--out data\\real-wording-report.md]

There are no expected answers, so nothing is scored: the report shows what the Engine would propose for each description (targets, deadline, what
it flagged as unclear, how long it took), with a line for the reader to mark right or wrong. Anything that comes out wrong is a candidate for a
new case in HELDOUT (scripts/llm_cases.py), written in fresh words, never for tuning the graph directly.
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


def lines_of(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def report_of(text: str, structure, seconds: float) -> str:
    out = [f"### {text}", ""]
    for i in structure.items:
        out.append(f"- {i.target_type}: **{i.name}** ({i.intent})" + (f", at {i.path}" if i.path else ""))
    if not structure.items:
        out.append("- no targets found")
    out.append(f"- deadline: {structure.final_deadline or 'none'}")
    for f in structure.flags:
        out.append(f"- unclear: {f.get('kind')}" + (f" ({f['detail']})" if f.get("detail") else ""))
    out += [f"- took {seconds:.1f} s", "- right? [ ] yes  [ ] no: ", ""]
    return "\n".join(out)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--model-path", default="models/Qwen3-1.7B-Q8_0.gguf")
    ap.add_argument("--out", type=Path, default=Path("data/real-wording-report.md"))
    args = ap.parse_args()
    descriptions = lines_of(args.file)
    if not descriptions:
        print(f"no descriptions in {args.file}")
        return 2
    llm = LocalLLM("llamacpp", model_path=args.model_path, timeout=60.0)
    if not llm.available:
        print(f"the model is not here: {args.model_path}")
        return 2
    parts = [f"# Real wording: {len(descriptions)} descriptions, {args.model_path}", ""]
    took = []
    for n, text in enumerate(descriptions, start=1):
        began = time.perf_counter()
        structure = await llm_graph.populate(llm, text)
        took.append(time.perf_counter() - began)
        parts.append(report_of(text, structure, took[-1]))
        print(f"{n}/{len(descriptions)}  {took[-1]:5.1f}s  {text[:80]}", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(parts), encoding="utf-8")
    print(f"\n{args.out}: average {sum(took) / len(took):.1f} s, slowest {max(took):.1f} s. Read it and mark each one right or wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
