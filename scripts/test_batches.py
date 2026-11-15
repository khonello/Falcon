"""Run the suite in batches, one pytest process at a time, so memory is given back between them (a full run in one process was
stopped for low memory, 15 Nov 2026).

    python scripts/test_batches.py [--per 8] [--skip-gui] [--from N] [pytest args...]

Each batch's output goes to data/test-batches/<n>.txt; the summary lists each batch's result and every failed test, and exits 1 if any failed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUI = {"test_operator_gui.py", "test_detective_gui.py", "test_console_calendar_rule_gui.py"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=8, help="test files per batch")
    ap.add_argument("--skip-gui", action="store_true", help="leave out the GUI test files")
    ap.add_argument("--from", dest="start", type=int, default=1, help="start at this batch (after a stop)")
    a, extra = ap.parse_known_args(argv)
    files = sorted(p for p in (ROOT / "tests").glob("test_*.py") if not (a.skip_gui and p.name in GUI))
    batches = [files[i:i + a.per] for i in range(0, len(files), a.per)]
    out = ROOT / "data" / "test-batches"
    out.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    for n, batch in enumerate(batches, 1):
        if n < a.start:
            continue
        log = out / f"{n:02d}.txt"
        with log.open("w", encoding="utf-8") as f:
            rc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE", *extra, *map(str, batch)],
                                cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=False).returncode
        text = log.read_text(encoding="utf-8", errors="replace")
        tail = next((ln for ln in reversed(text.splitlines()) if re.search(r"passed|failed|error|no tests ran", ln)), f"exit {rc}")
        print(f"batch {n}/{len(batches)} ({batch[0].name} .. {batch[-1].name}): {tail.strip('= ')}", flush=True)
        failed += [ln for ln in text.splitlines() if ln.startswith(("FAILED ", "ERROR tests"))]
    print("\n".join(["", f"{len(failed)} failed:", *failed]) if failed else "\nall batches passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
