"""python -m worker_client.program [--background] [--shot out.png --view view.json [--tab today|tasks|announcements|machine]]"""

from __future__ import annotations

import getpass
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

QML_DIR = Path(__file__).with_name("qml")
POLL_VISIBLE_MS = 5000
POLL_HIDDEN_MS = 15000


def state_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home() / ".config") / "Falcon"
    return base / "program.json"


def badge_of(view: dict[str, Any], seen_alert: int) -> int:
    """What is new to this person: tasks they have not started, and announcements they have not opened the list for."""
    tasks = sum(1 for t in view.get("tasks") or [] if not t.get("started"))
    notes = sum(1 for a in view.get("announcements") or [] if int(a.get("id") or 0) > seen_alert)
    return tasks + notes


def main(argv: list[str]) -> int:
    shot = argv[argv.index("--shot") + 1] if "--shot" in argv else None
    view_arg = argv[argv.index("--view") + 1] if "--view" in argv else None
    tab = argv[argv.index("--tab") + 1] if "--tab" in argv else "today"
    background = "--background" in argv and shot is None
    if shot:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
    from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import (
        QQuickWindow,  # noqa: F401 -- types the root as a window (grabWindow)
    )
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    from worker_client.program.client import LocalClient, ServiceAway

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    # one copy per person: a second start only asks the first to come forward
    name = f"FalconProgram-{getpass.getuser()}"
    server = None
    if not shot:
        probe = QLocalSocket()
        probe.connectToServer(name)
        if probe.waitForConnected(300):
            probe.write(b"show\n")
            probe.waitForBytesWritten(300)
            return 0
        QLocalServer.removeServer(name)
        server = QLocalServer()
        server.listen(name)

    class Bridge(QObject):
        viewChanged = Signal()
        toastArrived = Signal("QVariant")
        asked = Signal(str)
        showRequested = Signal()
        _got = Signal(object)

        def __init__(self) -> None:
            super().__init__()
            self._view: dict[str, Any] = {"tasks": [], "announcements": [], "admins": [], "connected": False}
            self._away = True
            self._seen = 0
            self._badge = 0
            self._shown: set[str] = set()
            self._client = LocalClient()
            self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="falcon-program")
            self._got.connect(self._apply)
            try:
                self._seen = int(json.loads(state_path().read_text(encoding="utf-8")).get("seen_alert", 0))
            except (OSError, ValueError, TypeError):
                self._seen = 0

        @Property("QVariant", notify=viewChanged)
        def view(self) -> Any:
            return self._view

        @Property(bool, notify=viewChanged)
        def away(self) -> bool:
            return self._away

        @Property(int, notify=viewChanged)
        def badge(self) -> int:
            return self._badge

        @Property(int, notify=viewChanged)
        def seenAlert(self) -> int:
            return self._seen

        def preview(self, view: dict[str, Any]) -> None:
            self._view, self._away = view, False
            self._badge = badge_of(view, self._seen)
            self.viewChanged.emit()

        @Slot()
        def refresh(self) -> None:
            self._pool.submit(self._fetch)

        def _fetch(self) -> None:
            try:
                self._got.emit(self._client.view())
            except ServiceAway:
                self._got.emit(None)

        def _apply(self, view: Any) -> None:
            if view is None:
                self._away = True
                self._view = {**self._view, "connected": False}
            else:
                self._away, self._view = False, view
                for t in view.get("toasts") or []:
                    if t["id"] not in self._shown:
                        self._shown.add(t["id"])
                        self.toastArrived.emit(t)
            self._badge = badge_of(self._view, self._seen)
            self.viewChanged.emit()

        @Slot()
        def markAnnouncementsSeen(self) -> None:
            top = max((int(a.get("id") or 0) for a in self._view.get("announcements") or []), default=0)
            if top > self._seen:
                self._seen = top
                try:
                    state_path().parent.mkdir(parents=True, exist_ok=True)
                    state_path().write_text(json.dumps({"seen_alert": top}), encoding="utf-8")
                except OSError:
                    pass
                self._badge = badge_of(self._view, self._seen)
                self.viewChanged.emit()

        def _act(self, fn: Any, *args: Any) -> None:
            def run() -> None:
                try:
                    fn(*args)
                except ServiceAway:
                    pass
                self._fetch()
            self._pool.submit(run)

        @Slot(int)
        def startTask(self, task_id: int) -> None:
            self._act(self._client.start_task, task_id)

        @Slot(int, str)
        def ask(self, account_id: int, name: str) -> None:
            self._act(self._client.ask, account_id)
            self.asked.emit(name)

        @Slot("QVariant")
        def ack(self, ids: Any) -> None:
            self._act(self._client.ack, list(ids))

        @Slot()
        def show(self) -> None:
            self.showRequested.emit()

    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("program", bridge)
    engine.rootContext().setContextProperty("startTab", tab)
    engine.rootContext().setContextProperty("previewOnly", bool(shot))
    engine.warnings.connect(lambda ws: [print("QML:", w.toString(), file=sys.stderr) for w in ws])
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Program.qml")))
    if not engine.rootObjects():
        return 1
    win = engine.rootObjects()[0]

    def bring_forward() -> None:
        win.show()
        win.raise_()
        win.requestActivate()
        bridge.refresh()

    bridge.showRequested.connect(bring_forward)

    if shot:
        data = json.loads(Path(view_arg).read_text(encoding="utf-8")) if view_arg and Path(view_arg).exists() else json.loads(view_arg or "{}")
        bridge.preview(data)
        win.show()
        QTimer.singleShot(900, lambda: (win.grabWindow().save(shot), print(json.dumps({"saved": shot}), flush=True), app.quit()))
        return app.exec()

    def icon() -> QIcon:
        pix = QPixmap(64, 64)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#1677ff"))
        p.setPen(QColor(0, 0, 0, 0))
        p.drawEllipse(4, 4, 56, 56)
        p.setPen(QColor("white"))
        f = QFont("Segoe UI", 28)
        f.setBold(True)
        p.setFont(f)
        p.drawText(pix.rect(), 0x84, "F")                       # centred
        if bridge._badge:
            p.setBrush(QColor("#d4380d"))
            p.setPen(QColor("white"))
            p.drawEllipse(34, 0, 30, 30)
            f2 = QFont("Segoe UI", 15)
            f2.setBold(True)
            p.setFont(f2)
            p.drawText(34, 0, 30, 30, 0x84, str(min(bridge._badge, 9)) + ("+" if bridge._badge > 9 else ""))
        p.end()
        return QIcon(pix)

    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(icon())
        tray.setToolTip("Falcon")
        menu = QMenu()
        menu.addAction("Open Falcon").triggered.connect(bring_forward)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda why: bring_forward() if why == QSystemTrayIcon.ActivationReason.Trigger else None)
        tray.show()

        def refresh_icon() -> None:
            tray.setIcon(icon())
            tray.setToolTip("Falcon" + (f": {bridge._badge} new" if bridge._badge else ""))

        bridge.viewChanged.connect(refresh_icon)

    if server is not None:
        def accept() -> None:
            sock = server.nextPendingConnection()
            if sock is not None:
                sock.readyRead.connect(lambda: (sock.readAll(), bring_forward()))
                sock.disconnected.connect(sock.deleteLater)

        server.newConnection.connect(accept)

    timer = QTimer()
    timer.timeout.connect(bridge.refresh)
    timer.start(POLL_HIDDEN_MS)
    win.visibleChanged.connect(lambda: timer.setInterval(POLL_VISIBLE_MS if win.isVisible() else POLL_HIDDEN_MS))
    bridge.refresh()
    if not background:
        bring_forward()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
