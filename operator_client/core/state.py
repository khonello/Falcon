"""Client-side view of what the Engine says about us.

The Engine decides; the client renders. This holds exactly what the UI needs to render the
persistent surfaces the design calls for -- who we are, the session we occupy (and the red
banner when Super User is inside someone else's view), whether our own PC is blocked, and the
shared pulsing status indicator (unaddressed pings, deadlines reached, task completed) -- and
it is updated from pushes so every UI on top of it stays live.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

Listener = Callable[[], None]


@dataclass
class Indicator:
    """One pulsing status entry. `kind` selects the colour in the UI (deadline_reached,
    task_completed, unaddressed_ping, blocked, flow_failed, violation, offer)."""
    kind: str
    text: str
    at: datetime = field(default_factory=datetime.now)
    key: str | None = None  # dedup key, e.g. "ping" or f"task:{id}"


@dataclass
class ClientState:
    client_id: str = ""
    account_id: int | None = None
    role: str | None = None
    pc_id: int | None = None
    department_id: int | None = None
    connected: bool = False
    engine: str = ""

    # The session we currently occupy (our own PC, or one we traversed into).
    session: dict[str, Any] | None = None
    # Our own PC has been entered by a superior: we are blocked out.
    blocked_by: dict[str, Any] | None = None
    indicators: list[Indicator] = field(default_factory=list)
    unaddressed_pings: int = 0
    recent_pushes: list[tuple[datetime, str, dict[str, Any]]] = field(default_factory=list)
    _listeners: list[Listener] = field(default_factory=list, repr=False)

    # --- observation ----------------------------------------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def _changed(self) -> None:
        for fn in list(self._listeners):
            fn()

    # --- derived --------------------------------------------------------------------------------

    @property
    def super_user_banner(self) -> bool:
        return bool(self.session and self.session.get("super_user_banner"))

    @property
    def traversing(self) -> bool:
        return bool(self.session and self.session.get("occupied_via") != "native")

    @property
    def role_label(self) -> str:
        return {"super_user": "Super User", "admin": "Admin", "worker": "Worker"}.get(self.role or "", "?")

    def set_identity(self, ident: Any, engine: str) -> None:
        self.client_id = ident.client_id
        self.account_id, self.role = ident.account_id, ident.role
        self.pc_id, self.department_id = ident.pc_id, ident.department_id
        self.connected, self.engine = True, engine
        self._changed()

    def set_session(self, session: dict[str, Any] | None) -> None:
        self.session = session
        self._changed()

    def add_indicator(self, kind: str, text: str, key: str | None = None) -> None:
        if key:
            self.indicators = [i for i in self.indicators if i.key != key]
        self.indicators.append(Indicator(kind, text, key=key))
        self._changed()

    def clear_indicator(self, key: str) -> None:
        self.indicators = [i for i in self.indicators if i.key != key]
        self._changed()

    # --- pushes ---------------------------------------------------------------------------------

    async def on_push(self, type_: str, payload: dict[str, Any]) -> None:
        """Keep the persistent surfaces current. Returns nothing; UIs subscribe for redraws."""
        self.recent_pushes.append((datetime.now(), type_, payload))
        del self.recent_pushes[:-200]
        if type_ == "session.blocked":
            if payload.get("pc_id") == self.pc_id and payload.get("occupant_account_id") != self.account_id:
                self.blocked_by = payload
                self.add_indicator("blocked", f"your PC is occupied by {payload.get('occupant_name')}", key="blocked")
        elif type_ == "session.released":
            if payload.get("pc_id") == self.pc_id:
                self.blocked_by = None
                self.clear_indicator("blocked")
        elif type_ == "session.ended":
            if self.session and payload.get("session_id") == self.session.get("session_id"):
                self.session = None
                self.add_indicator("session", f"session ended ({payload.get('reason')})", key="session")
        elif type_ == "session.extended":
            if self.session and payload.get("session_id") == self.session.get("session_id"):
                self.session["deadline_at"] = payload.get("deadline_at")
        elif type_ == "assistance.ping_status":
            self.unaddressed_pings = int(payload.get("unaddressed", 0))
            if self.unaddressed_pings:
                self.add_indicator("unaddressed_ping", f"{self.unaddressed_pings} unaddressed ping(s)", key="ping")
            else:
                self.clear_indicator("ping")
        elif type_ == "task.deadline":
            self.add_indicator("deadline_reached", f"task #{payload.get('task_id')} {payload.get('kind')} deadline reached",
                               key=f"task:{payload.get('task_id')}")
        elif type_ == "task.completed":
            self.add_indicator("task_completed", f"task #{payload.get('task_id')} completed",
                               key=f"task:{payload.get('task_id')}")
        elif type_ == "flow.failed":
            self.add_indicator("flow_failed", f"flow #{payload.get('flow_id')} failed: {payload.get('reason')}",
                               key=f"flow:{payload.get('flow_id')}:{payload.get('destination_id')}")
        elif type_ == "resource.violation":
            self.add_indicator("violation", payload.get("message", "resource violation"),
                               key=f"violation:{payload.get('violation_id')}")
        elif type_ == "assisted_access.offer":
            self.add_indicator("offer", f"assistance request #{payload.get('request_id')} from "
                                        f"{payload.get('requester_name')}", key=f"offer:{payload.get('request_id')}")
        elif type_ in ("assisted_access.declined", "assisted_access.closed"):
            self.clear_indicator(f"offer:{payload.get('request_id')}")
        self._changed()
