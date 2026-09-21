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

from PySide6.QtCore import QSize, QTimer, QUrl
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
    win = engine.rootObjects()[0]
    QTimer.singleShot(0, lambda: fit_to_screen(win))   # after the native window exists (frame margins known)
    return app, engine, bridge


def fit_to_screen(win) -> QSize:
    """Full screen without resizing: pin min == max size to the screen's available work area
    (minus the native frame) and place the window at its top-left. Equal min/max sizes make the
    Windows frame non-resizable and drop the maximize button; minimize/close stay."""
    _drop_resize_frame(win)
    screen = win.screen()
    avail = screen.availableGeometry()
    fm = win.frameMargins()
    size = QSize(avail.width() - fm.left() - fm.right(), avail.height() - fm.top() - fm.bottom())
    win.setMinimumSize(size)
    win.setMaximumSize(size)
    win.setPosition(avail.x() + fm.left(), avail.y() + fm.top())
    return size


def _drop_resize_frame(win) -> None:
    """Windows keeps the thick (resize) frame even for a fixed-size window; strip it so the edges
    show no resize cursor. Operator Client is Windows-only; a no-op elsewhere."""
    if sys.platform != "win32":
        return
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = int(win.winId())
    GWL_STYLE, WS_THICKFRAME, WS_MAXIMIZEBOX = -16, 0x00040000, 0x00010000
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX)
    SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x0002, 0x0001, 0x0004, 0x0020
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)


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
