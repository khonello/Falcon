"""What the Worker never ends nor lists as something to end (ENGINE-GAPS #9): Windows' own, the machine's accounts, itself."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from worker_client import inventory, protected
from worker_client.executor import BUILTIN_SCRIPTS

psutil = pytest.importorskip("psutil")


def test_windows_own_the_machines_accounts_and_the_worker_are_protected():
    own = protected.falcon_pids()
    assert os.getpid() in own
    assert protected.is_protected(4, "System", None, own) and protected.is_protected(900, "lsass.exe", "Ama", own)
    assert protected.is_protected(900, "backup.exe", r"NT AUTHORITY\SYSTEM", own)
    assert not protected.is_protected(900, "EXCEL.EXE", r"PC\Ama", own)
    assert os.getpid() not in {p["pid"] for p in inventory.processes(limit=10_000)}


def test_kill_process_refuses_a_protected_process_even_by_pid():
    script = BUILTIN_SCRIPTS["kill_process"]
    run = subprocess.run([sys.executable, "-c", script, "", str(os.getpid())], capture_output=True, text=True, timeout=60, check=False,
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert run.returncode != 0 and "is protected" in run.stderr and "part of Falcon" in run.stderr
