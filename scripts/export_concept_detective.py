r"""The Detective sample for the console concept (docs/design/concepts-snapshot.html): the same cases `preview.py` shows, played through the real matcher, with the
clock set to the concept's "now" (13:20 today) so every time on the page agrees with the rest of the concept.

    environ-engine\Scripts\python.exe scripts\export_concept_detective.py > detective.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preview_detective as pd


def main() -> None:
    t = time.localtime()
    now = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 13, 20, 0, 0, 0, -1))
    built = pd.build(now)
    for c in built["cases"]:
        c["when"] = time.strftime("%H:%M", time.localtime(max(0, now - c["ago"] * 3600)))
    out = {"cases": built["cases"], "detail": {str(k): {"findings": v["findings"], "graph": v["graph"], "rule_options": v["rule_options"], "board": v["board"]} for k, v in built["detail"].items()},
           "rules": pd.RULES, "proposals": pd.proposals()}
    for d in out["detail"].values():
        for f in d["findings"]:
            f.pop("evidence", None)
            f.pop("things", None)
    json.dump(out, sys.stdout, default=str, separators=(",", ":"))


if __name__ == "__main__":
    main()
