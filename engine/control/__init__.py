"""Control, Events, Monitoring & Actions (control-events-monitoring-actions-combo.md; spec 7.5).

The automation layer. Lives at the Admin interface; Super User traverses in.

    actions        -- the action library: Control (do), Monitoring (observe), Custom (Admin-authored)
    events         -- Event definitions; native/pushed matched from agent signals, polled/evaluated
                      checked by the Scheduler; fires attached Actions independently
    executions     -- per-run lifecycle: dispatch to agent, timeout, manual termination, output,
                      Dashboard operational view
    custom_actions -- validation of PowerShell/Python scripts (stdlib + Windows-native only)
"""

from engine.control import actions, custom_actions, events, executions  # noqa: F401
