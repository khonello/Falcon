"""Every place code that stays still reaches into code that goes (docs/next-product/RAVEN-MAP.md).

    python scripts/cut_edges.py . data/graph.json engine.task,engine.flow [tests]

Run scripts/import_graph.py first. A cut is finished when this prints nothing for its modules, with and without `tests`.
"""
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
g = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
OUT = [p for p in sys.argv[3].split(",")]
show_tests = len(sys.argv) > 4


def is_out(m):
    return any(m == p or m.startswith(p + ".") for p in OUT)


for m in sorted(g):
    if is_out(m) or (m.startswith("tests") != show_tests):
        continue
    d = g[m]
    hits = [e for e in d["edges"] if is_out(e["to"])]
    if not hits:
        continue
    src = (root / d["file"]).read_text(encoding="utf-8", errors="replace")
    print(f"\n{d['file']} ({d['lines']} lines)")
    seen = set()
    for e in hits:
        key = (e["to"], tuple(e["names"]))
        if key in seen:
            continue
        seen.add(key)
        lines = sorted({x["line"] for x in hits if (x["to"], tuple(x["names"])) == key})
        uses = set()
        for n in e["names"]:
            uses |= set(re.findall(rf"\b{re.escape(n)}\.([A-Za-z_]\w*)", src))
            if not uses:
                count = len(re.findall(r"\b" + re.escape(n) + r"\b", src)) - 1
                uses.add(f"<{n} x{count}>")
        lazy = "lazy" if e["lazy"] else "TOP"
        print(f"  -> {e['to']} [{lazy}] lines {lines} uses: {', '.join(sorted(uses))}")
