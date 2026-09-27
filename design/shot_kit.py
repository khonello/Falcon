"""Render the shared kit (design/kit_preview.qml) with the real QML components, offscreen, to design/shots/gui-kit.png.

    environ-operator\\Scripts\\python.exe design\\shot_kit.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401  (registers the window type for grabWindow)

HERE = Path(__file__).resolve().parent


def main() -> None:
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda ws: [print("QML:", w.toString()) for w in ws])
    engine.load(QUrl.fromLocalFile(str(HERE / "kit_preview.qml")))
    if not engine.rootObjects():
        sys.exit("kit_preview.qml failed to load")
    win = engine.rootObjects()[0]

    def grab() -> None:
        try:
            out = HERE / "shots" / "gui-kit.png"
            win.grabWindow().save(str(out))
            print("saved", out)
        finally:
            app.quit()

    QTimer.singleShot(1500, grab)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
