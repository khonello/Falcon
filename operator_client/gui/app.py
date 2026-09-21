"""QApplication + qasync event loop + QML engine.

    python -m operator_client --gui [--engine host:port --client-id ID --plaintext]

The asyncio loop is qasync's, so `EngineConnection` (asyncio) and Qt share one thread and one
loop -- the same single-threaded model the Engine uses (spec 4.1).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from operator_client.core.config import LocalConfig
from operator_client.gui.bridge import FalconBridge

log = logging.getLogger(__name__)

QML_DIR = Path(__file__).parent / "qml"


def application() -> QGuiApplication:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("Falcon Operator Client")
    app.setOrganizationName("Falcon")
    QQuickStyle.setStyle("Fusion")
    return app


def create(config: LocalConfig, *, auto_connect: bool = False) -> tuple[QGuiApplication, QQmlApplicationEngine, FalconBridge]:
    """Build the QML engine + bridge. Set the (qasync) event loop first: QML issues `falcon.call`s
    from Component.onCompleted and those are scheduled on the current loop."""
    app = application()
    bridge = FalconBridge(config)
    engine = QQmlApplicationEngine()
    bridge.js_engine = engine          # QJSValue.engine() is not exposed by PySide6; results are converted through this
    engine.rootContext().setContextProperty("falcon", bridge)
    engine.rootContext().setContextProperty("autoConnect", auto_connect)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "main.qml")))
    if not engine.rootObjects():
        raise SystemExit("failed to load QML (see errors above)")
    return app, engine, bridge


def run(config: LocalConfig, *, auto_connect: bool = False) -> None:
    import qasync

    app = application()
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    app, _engine, bridge = create(config, auto_connect=auto_connect)   # keep the QML engine alive for the loop
    close_event = asyncio.Event()
    app.aboutToQuit.connect(close_event.set)
    with loop:
        loop.run_until_complete(close_event.wait())
        if bridge.conn is not None:
            loop.run_until_complete(bridge.conn.close())
