"""IBM Plex, as the Worker concept sets it, bundled with the Worker Client (OFL, OFL.txt): loaded once into a Qt application."""
from __future__ import annotations

from pathlib import Path


def load() -> None:
    from PySide6.QtGui import QFontDatabase

    for f in sorted(Path(__file__).resolve().parent.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))
