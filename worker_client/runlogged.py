"""Run a program with its output appended to a log file: `python -m worker_client.runlogged <log> <program> [args...]`.

How an Action that needs the person's desktop is run when the Worker is a service: the service starts this on their desktop (it cannot give a program there a
file as its output), and this runs the real program with its output going to the file the service reads. Exits with the program's own exit code.
"""

from __future__ import annotations

import subprocess
import sys


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m worker_client.runlogged <log> <program> [args...]", file=sys.stderr)
        return 2
    with open(argv[0], "ab") as log:
        return subprocess.run(argv[1:], stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
