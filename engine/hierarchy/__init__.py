"""Hierarchy -- the backbone (hierarchy-system-design.md; spec 7.1).

Implemented entirely server-side. The Operator Client never decides what it may see or do; it
renders what the Engine's permission/session state says.

    traversal        -- Traversal, Session Blocking, Time Limit, red-banner state
    assisted_access  -- Cross-Department Assisted Access (its own state machine, NOT traversal)
    display_names    -- top-down naming, non-propagating across layers
    reports          -- Report Routing (additive to Super User's always-on visibility)
    alerts           -- System Alerts & Announcements
    accounts         -- Department creation/assignment, offboarding
"""

from engine.hierarchy import (  # noqa: F401
    accounts,
    alerts,
    assisted_access,
    display_names,
    reports,
    traversal,
)
