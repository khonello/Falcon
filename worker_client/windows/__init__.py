"""The Worker's windows (boards WR01, TK07): small, calm, in plain words -- a person at their own machine never sees
the Operator's vocabulary.

Each window is its own short-lived process, `python -m worker_client.windows <kind> <json>` (the spec's helper
exes, spawned with `asyncio.create_subprocess_exec`; frozen into Overlay/Dialog exes at packaging). It shows one
window and prints the person's answer as one JSON line on stdout, then exits:

    blocked   "R. Mensah is using this machine"   -- topmost; stays until the service closes it
    message   a message from your Admin, with OK
    locked    "Locked by your Admin"               -- stays until the service closes it
    ask       ask your Admin for help: one message, then wait for their reply
    task      a task given to you: what it is, when it is due, what will show the work; Start -- never Complete

PySide6 is the optional `worker-ui` extra: without it the service runs headless and says so once.
"""

from __future__ import annotations

KINDS = ("blocked", "message", "locked", "ask", "task")


def available() -> bool:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        return False
    return True
