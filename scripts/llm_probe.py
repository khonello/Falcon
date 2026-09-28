"""Does this model discriminate at all? The cheap gate before any benchmark run.

Asks the graph's pick-from-list questions about descriptions whose correct answers are
unmistakable and different from each other. A model with signal varies its answer; a model
below the floor for this task answers the same thing every time regardless of the text.

Measured: Qwen3-0.6B scores 6/8 here, Qwen3-1.7B scores 8/8 -- which is why the default model
is the 1.7B despite costing about 3x the time per call.

A trap worth recording, because it looks like an obvious improvement: do NOT wrap these calls
in a GBNF grammar that forces the answer to be one of the options. The grammar constrains from
the very first token, and Qwen3 wants to emit a <think> block there, so masking it destroys the
output -- under a forced grammar BOTH models answer almost constantly ("change an existing
file" to every file question), which reads exactly like a model with no signal and is really a
broken measurement. Ask unconstrained and let `LocalLLM.choose` reject what does not parse: an
unparsed answer is the "unclear -> surface to the assigner" signal the design wants, and is far
safer than a well-formed guess the graph cannot tell from a real answer.

    environ-engine\\Scripts\\python.exe scripts\\llm_probe.py [--model-path <file.gguf>]

Run this FIRST when trying a different model: if it collapses here, it will not help the
graph, and there is no point running scripts/llm_benchmark.py against it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.llm import SYSTEM
from engine.task.llm_graph import FILE_INTENT_OPTIONS, PROGRAM_INTENT_OPTIONS

FILE_Q = "For the file {name}, does the task ask to:"
PROGRAM_Q = "What should happen with the program {name}?"

# (question, options-map, description, the only defensible answer)
PROBES = [
    (FILE_Q.format(name="fresh.xlsx"), FILE_INTENT_OPTIONS,
     "Create a brand new spreadsheet called fresh.xlsx from nothing", "create"),
    (FILE_Q.format(name="report.pdf"), FILE_INTENT_OPTIONS,
     "Just confirm report.pdf is present, do not touch it", "exists"),
    (FILE_Q.format(name="ledger.xlsx"), FILE_INTENT_OPTIONS,
     "Edit the existing totals in ledger.xlsx", "update"),
    (FILE_Q.format(name="blank.log"), FILE_INTENT_OPTIONS,
     "Make a new empty log file called blank.log", "create"),
    (PROGRAM_Q.format(name="Firefox"), PROGRAM_INTENT_OPTIONS,
     "Install Firefox on the machine, nothing else", "installed_available"),
    (PROGRAM_Q.format(name="Spotify"), PROGRAM_INTENT_OPTIONS,
     "Quit Spotify immediately, shut it down", "closed_not_running"),
    (PROGRAM_Q.format(name="Blender"), PROGRAM_INTENT_OPTIONS,
     "Spend two hours working inside Blender", "used"),
    (PROGRAM_Q.format(name="Nginx"), PROGRAM_INTENT_OPTIONS,
     "Make absolutely sure Nginx stays up and running", "running"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-path", default="models/Qwen3-1.7B-Q8_0.gguf")
    args = ap.parse_args()

    from llama_cpp import Llama

    llama = Llama(model_path=args.model_path, n_ctx=2048, verbose=False)
    print(f"model: {args.model_path}\n")

    answers: dict[str, list[str]] = {}
    correct = 0
    for question, options, text, want in PROBES:
        opts = list(options)
        prompt = (f'{question}\n\nText: """{text}"""\n\n'
                  f'Answer with exactly one of: {" | ".join(opts)}.')
        out = llama.create_chat_completion(
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": prompt + " /no_think"}],
            max_tokens=16, temperature=0.0)
        raw = str(out["choices"][0]["message"]["content"]).rsplit("</think>", 1)[-1].strip()
        got = options.get(raw, raw)
        ok = got == want
        correct += ok
        answers.setdefault("file" if options is FILE_INTENT_OPTIONS else "program", []).append(raw)
        print(f"[{'OK ' if ok else 'BAD'}] want {want:20s} got {got!r:24s} {text}")

    print(f"\n{correct}/{len(PROBES)} correct")
    for kind, given in answers.items():
        if len(set(given)) == 1:
            print(f"COLLAPSED: every {kind} question answered {given[0]!r} -- this model has no "
                  f"signal on {kind} intents and will not help the graph.")
        else:
            print(f"{kind}: {len(set(given))} distinct answers over {len(given)} questions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
