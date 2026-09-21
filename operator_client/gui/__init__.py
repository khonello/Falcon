"""Operator Client GUI (PySide6 + QML + qasync) -- Phase 6.

Sits on the same `operator_client.core` as the TUI: `EngineConnection`, `ClientState`,
`LocalConfig`. The GUI owns no business logic; every view sends the same Engine messages the
TUI commands send and renders what comes back, live-updated by pushes.

    bridge   FalconBridge: QObject exposed to QML as `falcon` -- state properties, a generic
             `call(type, payload, callback)`, and `pushReceived(type, payload)`
    app      QApplication + qasync loop, loads qml/main.qml
    qml/     main window (status bar, navigation, push feed) and one view per area
"""
