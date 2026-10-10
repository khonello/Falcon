"""The built-in actions that act on the person's screen or machine: notify, lock_session, reboot, shutdown.

Each runs as the executor's detached script (so it has the same timeout, termination and report as any
action) and prints the FALCON: marks the Engine keeps (see executor.read_returned). They take their settings
as arguments in the order of executor.BUILTIN_ARGS; an empty argument means "not set".

  notify         message, stay_s     a message window; stays until closed (stay_s empty or 0) or for stay_s seconds
  lock_session   duration_s, message the screen locked behind the "Locked by your Admin" window for duration_s
  reboot/shutdown delay_s, message   the warning before it happens (default 30 s), with the message beside it

A lock covers the screen with the window AND blocks the keyboard and mouse at the OS level while it holds.
The windows are the Worker's own (worker_client.windows). Without them (a headless install) notify says so in
its summary and lock_session falls back to locking the workstation once.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from worker_client.windows import available as _installed


def available() -> bool:
    """The windows can be shown: installed, and the Worker is configured to show them (it says so in the
    environment it starts each action with)."""
    return os.environ.get("FALCON_WORKER_WINDOWS", "1") != "0" and _installed()


def _block_input(on: bool) -> bool:
    """Block (or release) the keyboard and mouse at the OS level while a lock holds. Windows ends the block by
    itself if this process dies, and Ctrl+Alt+Del always overrides it, so a person is never stranded. False when
    this is not Windows or Windows refuses."""
    if sys.platform != "win32":
        return False
    import ctypes

    return bool(ctypes.windll.user32.BlockInput(bool(on)))


def _num(argv: list[str], i: int) -> int:
    try:
        return int(argv[i]) if i < len(argv) and argv[i].strip() else 0
    except ValueError:
        return 0


def _text(argv: list[str], i: int) -> str:
    return argv[i].strip() if i < len(argv) else ""


def _mark(summary: str) -> None:
    print(f"FALCON:summary {summary}", flush=True)


def _window(kind: str, spec: dict) -> subprocess.Popen[str]:
    return subprocess.Popen([sys.executable, "-m", "worker_client.windows", kind, json.dumps(spec)],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def _wait(proc: subprocess.Popen[str], seconds: int) -> bool:
    """True if the window ended by itself (the person answered); False if `seconds` passed and it was closed."""
    try:
        proc.wait(timeout=seconds if seconds > 0 else None)
        return True
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        return False


def notify(argv: list[str]) -> int:
    message, stay = _text(argv, 0), _num(argv, 1)
    print(f"NOTIFY: {message}", flush=True)
    if not available():
        _mark("not shown: this machine has no windows installed")
        return 0
    proc = _window("message", {"text": message, "from": ""})
    try:
        answered = _wait(proc, stay)
    finally:
        if proc.poll() is None:
            proc.kill()
    _mark("closed by the person" if answered else f"taken down after {stay} s")
    return 0


def lock(argv: list[str]) -> int:
    duration, message = _num(argv, 0), _text(argv, 1)
    until = datetime.now(timezone.utc).astimezone() + timedelta(seconds=duration)
    if not available():
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.LockWorkStation()
        _mark("locked once (no windows installed, so no timer)")
        return 0
    proc = _window("locked", {"message": message, "until": until.isoformat()})
    blocked = _block_input(True)
    try:
        time.sleep(max(duration, 0))
    finally:
        if blocked:
            _block_input(False)
        _wait(proc, 1)
        if proc.poll() is None:
            proc.kill()
    length = f"{duration // 60} min" if duration >= 60 and duration % 60 == 0 else f"{duration} s"
    _mark(f"locked for {length}" + ("" if blocked else " (screen covered; keyboard and mouse were not blocked)"))
    return 0


def power(kind: str, argv: list[str]) -> int:
    delay, message = _num(argv, 0) or 30, _text(argv, 0 + 1)
    flag = "r" if kind == "reboot" else "s"
    if sys.platform == "win32":
        cmd = ["shutdown", f"/{flag}", "/t", str(delay)] + (["/c", message[:500]] if message else [])
    else:
        cmd = ["shutdown", "-r" if kind == "reboot" else "-h", f"+{max(1, -(-delay // 60))}"] + ([message] if message else [])
    subprocess.run(cmd, check=False)
    _mark(f"{kind} in {delay // 60} min" if delay % 60 == 0 and delay >= 60 else f"{kind} in {delay} s")
    return 0
