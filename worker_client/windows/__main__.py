"""python -m worker_client.windows <kind> '<json>' [--shot out.png] -- one window, the answer on stdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from worker_client.windows import KINDS

QML_DIR = Path(__file__).with_name("qml")


def main(argv: list[str]) -> int:
    if len(argv) < 1 or argv[0] not in KINDS:
        print(f"usage: python -m worker_client.windows {{{'|'.join(KINDS)}}} '<json>' [--shot out.png]", file=sys.stderr)
        return 2
    kind = argv[0]
    data = json.loads(argv[1]) if len(argv) > 1 and not argv[1].startswith("--") else {}
    shot = argv[argv.index("--shot") + 1] if "--shot" in argv else None

    from PySide6.QtCore import QObject, QTimer, QUrl, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import (
        QQuickWindow,  # noqa: F401 -- types the root as a QQuickWindow (grabWindow)
    )

    class Answer(QObject):
        """What the window hands back: printed as one JSON line for the service to read."""

        @Slot("QVariant")
        def give(self, value: object) -> None:
            v = value.toVariant() if hasattr(value, "toVariant") else value
            print(json.dumps(v if v is not None else {}), flush=True)
            QGuiApplication.quit()

    app = QGuiApplication(sys.argv[:1])
    engine = QQmlApplicationEngine()
    answer = Answer()
    engine.rootContext().setContextProperty("answer", answer)
    engine.rootContext().setContextProperty("spec", data)
    engine.rootContext().setContextProperty("kind", kind)
    engine.rootContext().setContextProperty("backdrop", bool(shot))
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Window.qml")))
    if not engine.rootObjects():
        return 1
    if shot:
        win = engine.rootObjects()[0]

        def grab() -> None:
            try:
                win.grabWindow().save(shot)
                print(json.dumps({"saved": shot}), flush=True)
            finally:
                app.quit()

        QTimer.singleShot(700, grab)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
