"""Worker Client -- the headless service on a Client PC (spec 5).

Keeps a persistent authenticated connection to the Engine and does what the Engine tells it:
enforce Session Blocking locally, execute Control/Monitoring/Custom Actions, move files for
Flow, and report what the Engine needs to know -- file events for the Global File Index,
metrics for polled Events, program signals for Task expectations, update attempts.

The narrow Client UI (task view/start/monitor, Assistance search/ping, alerts) is a small
command shell (`worker_client.ui`), the Overlay/Dialog helper exes come in Phase 6.

    service    WorkerService: connection lifecycle + push dispatch
    config     WorkerConfig: engine address, client id, watched roots (JSON)
    watcher    file events (watchdog native, polling fallback) + idle-time full sweep
    executor   Script Execution Model for built-in and Custom Actions
    flowsync   flow.read / flow.apply / flow.resolve_conflict on this PC
    signals    metrics + task program signals
    lockout    session-blocking surface
    updater    update attempts with retry-on-idle
    ui         the narrow Worker TUI
"""
