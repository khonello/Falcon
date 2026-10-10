"""The Worker's tray icon: how a person asks their Admin for help (WR01, "ask").

    python -m worker_client.windows.tray

A small icon in the notification area; clicking it, or choosing "Ask my Admin for help" from its menu, prints
one line, `ask`, on stdout and keeps running. The service reads those lines, opens the ask window and sends the
ping -- the icon itself never talks to the Engine, so it needs no key and no connection. It runs in the person's
own session (a service has no desktop of its own) and is stopped by the service when it stops.

The icon is drawn here (a plain disc with an exclamation mark), so there is no image file to ship.
"""

from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("no-tray", flush=True)
        return 3

    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    paint = QPainter(pix)
    paint.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint.setBrush(QColor("#5b7cfa"))
    paint.setPen(Qt.PenStyle.NoPen)
    paint.drawEllipse(4, 4, 56, 56)
    paint.setPen(QColor("white"))
    font = QFont("Segoe UI", 30)
    font.setBold(True)
    paint.setFont(font)
    paint.drawText(QRectF(0, 0, 64, 64), int(Qt.AlignmentFlag.AlignCenter), "?")
    paint.end()

    tray = QSystemTrayIcon(QIcon(pix))
    tray.setToolTip("Ask your Admin for help")
    menu = QMenu()
    ask = QAction("Ask my Admin for help")
    ask.triggered.connect(lambda: print("ask", flush=True))
    menu.addAction(ask)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda why: print("ask", flush=True) if why == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
