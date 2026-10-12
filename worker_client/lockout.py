"""Session Blocking on this PC (Hierarchy -> Session Blocking During Traversal; spec 5.1).

When a superior enters this PC's session the Engine pushes `session.blocked`; the user must
see an unmistakable "inaccessible / traversal in progress" surface until `session.released`.
The Overlay exe (QML, topmost, re-asserting) is Phase 6; v1 provides:

  * state + a callback the narrow TUI uses to render a full-width BLOCKED banner, and
  * optionally (config `lock_workstation_on_block`), Windows `LockWorkStation()` -- blunt but
    effective local input restriction until the overlay exists.

The block ends only when the Engine says so; the client then re-claims its native session.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


class Lockout:
    def __init__(self, *, lock_workstation: bool = False) -> None:
        self.lock_workstation = lock_workstation
        self.blocked_by: dict[str, Any] | None = None
        self.viewing_by: dict[str, Any] | None = None       # someone is looking at this machine and the person keeps working
        self.listeners: list[Callable[[dict[str, Any] | None], None]] = []
        self.view_listeners: list[Callable[[dict[str, Any] | None], None]] = []

    def on_change(self, fn: Callable[[dict[str, Any] | None], None]) -> None:
        self.listeners.append(fn)

    def on_view_change(self, fn: Callable[[dict[str, Any] | None], None]) -> None:
        self.view_listeners.append(fn)

    def view(self, session: dict[str, Any]) -> None:
        """A superior is looking at this machine (and perhaps not controlling it): the person is told, and keeps their keyboard and mouse."""
        was_blocked = self.blocked_by is not None
        self.blocked_by = None
        self.viewing_by = session
        log.warning("VIEWED: %s (%s) is looking at this PC until %s", session.get("occupant_name"), session.get("occupant_role"), session.get("deadline_at"))
        if was_blocked:
            for fn in list(self.listeners):
                fn(None)
        for fn in list(self.view_listeners):
            fn(self.viewing_by)

    def block(self, session: dict[str, Any]) -> None:
        if self.viewing_by is not None:
            self.viewing_by = None
            for fn in list(self.view_listeners):
                fn(None)
        self.blocked_by = session
        log.warning("BLOCKED: this PC is occupied by %s (%s) until %s", session.get("occupant_name"),
                    session.get("occupant_role"), session.get("deadline_at"))
        if self.lock_workstation and sys.platform == "win32":
            try:
                ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
            except (AttributeError, OSError) as exc:
                log.warning("LockWorkStation failed: %s", exc)
        for fn in list(self.listeners):
            fn(self.blocked_by)

    def release(self) -> None:
        if self.viewing_by is not None:
            self.viewing_by = None
            for fn in list(self.view_listeners):
                fn(None)
        if self.blocked_by is None:
            return
        log.info("released: this PC is available again")
        self.blocked_by = None
        for fn in list(self.listeners):
            fn(None)

    @property
    def is_blocked(self) -> bool:
        return self.blocked_by is not None
