"""Hierarchy -- the backbone (hierarchy-system-design.md; spec 7.1).

Implemented entirely server-side. The Operator Client never decides what it may see or do; it
renders what the Engine's permission/session state says.

    traversal        -- Traversal, Session Blocking, Time Limit, red-banner state
    display_names    -- top-down naming, non-propagating across layers
    reports          -- Report Routing (additive to Super User's always-on visibility)
    alerts           -- System Alerts & Announcements
    accounts         -- Department creation/assignment, offboarding
    auditing         -- reading the audit trail and deviations, role-scoped
"""

from engine.hierarchy import (  # noqa: F401
    accounts,
    alerts,
    auditing,
    display_names,
    enrollment,
    handover,
    reports,
    traversal,
)
