"""Check Windows' instant program and file-open events on this machine (run from an elevated prompt, or as the Worker's service account).

    python scripts/etw_check.py [seconds=15] [path_prefix=C:/Users]

Starts the same two trace sessions the Worker starts, prints every program that starts or stops and every file opened under the path
for a few seconds, and stops them again. Not elevated, it says why it cannot and exits: the Worker then keeps looking every few seconds.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker_client.etw import EtwWatcher


def main() -> int:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    prefix = sys.argv[2] if len(sys.argv) > 2 else "C:/Users"
    watcher = EtwWatcher(lambda t, d: print(time.strftime("%H:%M:%S"), t, str(d).encode("ascii", "replace").decode(), flush=True))
    programs, files = watcher.want_programs(True), watcher.want_files([{"path_prefix": prefix}])
    print(f"programs live: {programs} {watcher.errors.get('programs', '')}\nfile opens live: {files} {watcher.errors.get('files', '')}")
    if not (programs or files):
        return 1
    print(f"watching for {seconds:.0f}s: start a program, open a file under {prefix}")
    try:
        time.sleep(seconds)
    finally:
        got = {k: v.records for k, v in (("program records", watcher._process), ("file records", watcher._file)) if v is not None}
        watcher.stop()
    print("stopped; records Windows delivered:", got)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
