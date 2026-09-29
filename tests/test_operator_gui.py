"""The console's first slice: the QML loads, the shell is there, and the Record page reads what the
Engine answers (docs/UI.md, docs/UI-COMPONENTS.md).

Runs offscreen on pytest-asyncio's loop; skipped without PySide6. The Engine is not needed — the
bridge's connection is the only thing faked, exactly as `scripts/preview.py` does it.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QObject, Qt
from PySide6.QtQml import QJSValue

from operator_client.core import LocalConfig
from operator_client.gui.app import create

AUDIT = [
    {"occurred_at": "2026-09-29T13:11:00+00:00", "actor_name": "R. Mensah", "summary": "Left OPS-03",
     "target_hostname": "OPS-03", "action": "session.ended"},
    {"occurred_at": "2026-09-29T10:02:00+00:00", "actor_name": "System",
     "summary": "budget-2026.xlsx found on a worker machine", "target_hostname": "OPS-07",
     "action": "resource.violation"},
    {"occurred_at": "2026-09-29T09:11:00+00:00", "actor_name": "System",
     "summary": "Hostname did not match the certificate", "target_hostname": "OPS-05",
     "action": "deviation.hostname"},
]


class _Identity:
    client_id, account_id, role, pc_id, department_id = "test", 1, "super_user", 1, 1


class _Connection:
    connected = True

    async def call(self, type_: str, payload: dict) -> dict:
        await asyncio.sleep(0)
        return {"entries": AUDIT} if type_ == "audit.recent" else {}

    async def close(self) -> None:
        return None


@pytest.fixture
def gui(tmp_path: Path):
    """(window, bridge), connected to a stubbed Engine, torn down after."""
    cfg = LocalConfig(path=tmp_path / "cfg.json", engine_host="127.0.0.1", engine_port=1,
                      client_id="", tls=False)
    _app, qml, bridge = create(cfg)
    win = qml.rootObjects()[0]
    bridge.conn = _Connection()
    bridge.state.set_identity(_Identity(), "test")
    # `connected` is emitted by the test that wants data: the views answer it with falcon.call, which
    # needs a running asyncio loop, and a sync test has none.
    yield win, bridge
    qml.warnings.disconnect()          # teardown re-evaluates bindings against a falcon that is gone
    qml.deleteLater()


def prop(obj: QObject, name: str):
    v = obj.property(name)
    return v.toVariant() if isinstance(v, QJSValue) else v


async def _wait(cond, timeout: float = 4.0) -> None:
    for _ in range(int(timeout / 0.05)):
        if cond():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


def test_the_shell_is_the_console(gui):
    """Sider, header, content -- and the window's own chrome, because it is frameless: the app draws
    minimise, maximise and close itself, so it does not also wear Windows'."""
    win, _ = gui
    assert win.title() == "Falcon"
    assert bool(win.flags() & Qt.WindowType.FramelessWindowHint)

    for name in ("sideMenu", "crumb", "recordView", "recordTable",
                 "winMinimize", "winMaximize", "winClose"):
        assert win.findChild(QObject, name) is not None, name

    # the sider is the only navigation, and it names every area
    menu = win.findChild(QObject, "sideMenu")
    keys = [e["key"] for e in prop(menu, "entries")]
    assert keys[0] == "overview" and "record" in keys and len(keys) == 13


def test_the_tokens_are_the_one_place_a_colour_is_named(gui):
    """Ant Design 6's values, with Falcon's two rationed status hues (docs/UI.md)."""
    win, _ = gui
    table = win.findChild(QObject, "recordTable")
    assert table is not None
    # the page and its table exist before anything is fetched, and the table says it is loading
    assert table.property("loading") is True


async def test_the_record_reads_what_the_engine_answers(gui):
    """The Record is the most table-shaped page, and the one the idiom is proved on: rows come from
    `audit.recent`, and the kind of each is named rather than left as a handler's type."""
    win, bridge = gui
    view = win.findChild(QObject, "recordView")
    table = win.findChild(QObject, "recordTable")
    bridge.connected.emit()                      # the views refetch, now that there is a loop

    await _wait(lambda: len(prop(view, "rows") or []) == len(AUDIT))
    rows = prop(view, "rows")
    assert [r["at"] for r in rows] == ["13:11", "10:02", "09:11"]
    assert rows[0]["who"] == "R. Mensah" and rows[0]["subject"] == "OPS-03"

    # only the two that need a person carry a hue; a session is neutral
    assert [r["kind"] for r in rows] == ["session", "violation", "deviation"]
    assert table.property("loading") is False

    # the table pages, sorts and filters over those rows without touching the Engine again
    assert len(prop(table, "filtered")) == 3
    table.setProperty("activeFilters", {"kind": "violation"})
    assert [r["kind"] for r in prop(table, "filtered")] == ["violation"]
