"""The console itself, against the live Engine: every page of both levels loads clean with real data, and a picture of each is kept.

Runs the real QML offscreen (no window on your screen), connected to the running Engine as the Admin, then as the Super User. Pictures go to
`data/drill/shots/`; QML errors and warnings are collected per page.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

ADMIN_PAGES = ["overview", "messages", "tasks", "restricted", "flows", "machines", "sessions", "issues", "automation", "actions", "rollout",
               "audit", "reports", "tasks/new", "flows/new", "automation/new", "actions/new", "restricted/mark"]
SU_PAGES = ["overview", "messages", "tasks", "restricted", "flows", "departments", "accountability", "access", "registry", "reports", "rules",
            "rollout", "audit", "tasks/new", "rules/new"]
PICTURES = {"admin": ["overview", "tasks", "restricted", "flows", "issues", "machines"], "su": ["overview", "departments", "flows", "access"]}


def pump(seconds: float) -> None:
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()


async def settle(seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pump(0.05)
        await asyncio.sleep(0.05)


async def run(d, check, say, wait_for) -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    from live_drill import admin_config, su_config
    from PySide6.QtCore import QObject

    from operator_client.core import LocalConfig
    from operator_client.gui.app import create

    shots = Path(d.folder("shots").parent / "shots")
    if shots.exists():
        shutil.rmtree(shots)
    shots.mkdir(parents=True)

    # --- something real on every page: a flow, a mark with a copy, a task -----------------------------------------------------------
    for n in ("WS-D1", "WS-D2"):
        await d.worker_account(n)
    ac = admin_config()
    d.state["workers"]["ADM-01"] = {"client_id": ac["client_id"], "client_key": ac["client_key"]}
    src, dst, mine, theirs = d.folder("WS-D1", "gui-out"), d.folder("WS-D2", "gui-in"), d.folder("ADM-01", "gui-restricted"), d.folder("WS-D1", "gui-docs")
    d.start_worker("ADM-01", [mine])
    d.start_worker("WS-D1", [src, theirs])
    d.start_worker("WS-D2", [dst])
    check("the Workers are online", await d.online("WS-D1", "WS-D2"))
    admin = d.admin
    p1, p2 = await d.pc_id("WS-D1"), await d.pc_id("WS-D2")
    stamp = str(int(time.time()))
    with contextlib.suppress(Exception):
        await admin.call("flow.create", {"source_pc_id": p1, "source_path": str(src), "stages": [], "confirm_collisions": True,
                                         "destinations": [{"destination_pc_id": p2, "destination_path": str(dst)}]})
    (src / f"report-{stamp}.txt").write_text("weekly report\n", encoding="utf-8")
    secret = mine / f"salaries-{stamp}.txt"
    secret.write_text(f"confidential {stamp}\n", encoding="utf-8")
    await wait_for(lambda: _seen(admin, secret), 30)
    with contextlib.suppress(Exception):
        await admin.call("marks.create", {"paths": [str(secret)], "keep": "path"})
    (theirs / f"copy-{stamp}.txt").write_text(f"confidential {stamp}\n", encoding="utf-8")
    me = d.state["workers"]["WS-D1"]
    with contextlib.suppress(Exception):
        await admin.call("task.create", {"assignee_account_id": me["account_id"], "description": f"Write summary-{stamp}.txt", "verification_mode": "none",
                                         "confirm_none": True})
    await asyncio.sleep(8)

    async def visit(level: str, cfg: dict, pages: list[str]) -> None:
        local = LocalConfig(path=shots / f"{level}.json", engine_host=cfg["engine_host"], engine_port=cfg["engine_port"], client_id=cfg["client_id"],
                            client_key=cfg["client_key"], tls=cfg["tls"], ca_cert=cfg.get("ca_cert"))
        _app, qml, bridge = create(local)
        warnings: list[str] = []
        qml.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
        win = qml.rootObjects()[0]
        try:
            start = time.monotonic()
            while not bridge.isConnected and time.monotonic() - start < 20:
                await settle(0.2)
            check(f"{level}: the console connects by itself and knows who it is", bridge.isConnected and bridge.role in ("admin", "super_user"), str(bridge.role))
            await settle(1.0)
            win.showNormal()
            win.resize(1440, 900)                              # the design's size, after the console's own fit-to-screen has run
            await settle(1.5)
            for page in pages:
                before = len(warnings)
                win.setProperty("view", page)
                await settle(2.0)
                loader = win.findChild(QObject, "page")
                ready = loader is not None and loader.property("item") is not None
                new = [w for w in warnings[before:] if "qt.qml.propertyCache" not in w]
                check(f"{level}: {page} loads clean", ready and not new, "; ".join(new)[:300] or ("did not load" if not ready else ""))
                if page in PICTURES["admin" if level == "admin" else "su"]:
                    win.grabWindow().save(str(shots / f"{level}-{page.replace('/', '_')}.png"))
        finally:
            qml.warnings.disconnect()
            qml.deleteLater()
            await bridge.conn.close() if bridge.conn is not None else None

    await visit("admin", ac, ADMIN_PAGES)
    await visit("su", su_config(), SU_PAGES)
    say(f"pictures in {shots}")
    _ = json, sys


async def _seen(admin, path: Path) -> bool:
    tree = await admin.call("marks.tree")
    want = str(path).replace("\\", "/").lower()
    return any(f["path"].replace("\\", "/").lower() == want for f in tree["files"])
