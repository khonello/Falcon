"""Looking THROUGH a held session: the reads that answer as the Admin the head of the organisation is inside.

Hierarchy -> Traversal: the head of the organisation inside an Admin's workstation sees "exactly what that Admin sees
(logs, status, all data)"; implementation-spec 4.2 puts that scope on the Engine. But holding a session
and looking through it are different things -- the head of the organisation can step out and keep the session -- so
the client says which it is doing by sending `"view": "session"` on a read. The Engine then decides
whether it is true: only the head of the organisation holding a traversal into an Admin workstation is narrowed, and
narrowing can never widen what anyone sees.

Only READS are listed. A write inside an Admin is still the head of the organisation's act, logged as theirs (the head of the
organisation's exemption), so no handler that changes state may appear here.
"""

VIEW_KEY = "view"
VIEW_SESSION = "session"

VIEWED_AS_TRAVERSED: frozenset[str] = frozenset({
    "hierarchy.tree", "hierarchy.departments", "hierarchy.sessions_today",
    "task.list", "task.get",
    "flow.list", "flow.status", "flow.history",
    "control.action_list", "control.event_list", "control.dashboard",
    "control.execution", "control.execution_output",
    "assistance.channels", "assistance.channel", "assistance.ping_status",
    "reports.list", "audit.recent", "audit.deviations", "resource.violations",
    "updates.current", "updates.rollout_health", "alerts.list",
})
