"""QApplication + qasync event loop + QML engine.

    python -m operator_client --gui [--engine host:port --client-id ID --plaintext]

The asyncio loop is qasync's, so `EngineConnection` (asyncio) and Qt share one thread and one
loop -- the same single-threaded model the Engine uses (spec 4.1).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSize, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from operator_client.core.config import LocalConfig
from operator_client.gui.bridge import FalconBridge

log = logging.getLogger(__name__)

QML_DIR = Path(__file__).parent / "qml"


def application() -> QGuiApplication:
    # Material dark, chosen in exactly one place before any QML loads (ui-reference.md): it takes
    # accent/background as attached properties, so the whole console is themed from Theme.qml.
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("Falcon Operator Client")
    app.setOrganizationName("Falcon")
    QQuickStyle.setStyle("Material")
    return app


def create(config: LocalConfig, *, auto_connect: bool = False) -> tuple[QGuiApplication, QQmlApplicationEngine, FalconBridge]:
    """Build the QML engine + bridge. Set the (qasync) event loop first: QML issues `falcon.call`s
    from Component.onCompleted and those are scheduled on the current loop."""
    app = application()
    bridge = FalconBridge(config)
    engine = QQmlApplicationEngine()
    # QML errors are otherwise silent here: the loader below raises "see errors above" with nothing
    # above it, because Qt's default message handler does not reach this console. One bad property
    # name then costs an hour. Print them instead.
    engine.warnings.connect(
        lambda warnings: [print("QML:", w.toString(), file=sys.stderr) for w in warnings])
    bridge.js_engine = engine          # QJSValue.engine() is not exposed by PySide6; results are converted through this
    engine.rootContext().setContextProperty("falcon", bridge)
    engine.rootContext().setContextProperty("autoConnect", auto_connect)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "main.qml")))
    if not engine.rootObjects():
        raise SystemExit("failed to load QML (see errors above)")
    win = engine.rootObjects()[0]
    QTimer.singleShot(0, lambda: fit_to_screen(win))   # after the native window exists (frame margins known)
    return app, engine, bridge


def fit_to_screen(win) -> QSize:
    """The window is FRAMELESS (main.qml), so it owns what the frame used to do.

    It opens maximised over the work area -- the pages are drawn for that much room -- and restores
    to the design's own 1440 x 900, centred, so the maximise button in the top bar means something
    in both directions. A minimum size keeps a four-cell page from collapsing into unreadable
    columns. The returned size is the restored one.

    This replaces the old pinning (min == max == the work area), which existed to make the NATIVE
    frame non-resizable and drop its maximize button. With no native frame there is nothing to
    strip, and the window can be moved and resized from the top bar and the grips instead.
    """
    screen = win.screen()
    avail = screen.availableGeometry()
    win.setMaximumSize(QSize(16777215, 16777215))
    win.setMinimumSize(QSize(min(1024, avail.width()), min(680, avail.height())))
    normal = QSize(min(1440, avail.width()), min(900, avail.height()))
    win.resize(normal)
    win.setPosition(avail.x() + (avail.width() - normal.width()) // 2,
                    avail.y() + (avail.height() - normal.height()) // 2)
    win.showMaximized()
    return normal


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
