"""The console's own forms, filled in and saved through the real QML against the live Engine: New flow (with and without files already at the
destination), New task (proposed by the real model, then created), Mark files. What each saves is read back from the Engine.

Each form gets a console of its own, so no page, dialog or state is left over from the one before.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import time
from pathlib import Path


async def run(d, check, say, wait_for) -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    from live_drill import admin_config
    from PySide6.QtCore import Q_ARG, QMetaObject, QObject
    from PySide6.QtQml import QJSValue

    from live_drills.gui_drill import settle
    from operator_client.core import LocalConfig
    from operator_client.gui.app import create

    def prop(obj, name):
        v = obj.property(name)
        return v.toVariant() if isinstance(v, QJSValue) else v

    ac = admin_config()
    d.state["workers"]["ADM-01"] = {"client_id": ac["client_id"], "client_key": ac["client_key"]}
    for n in ("WS-D1", "WS-D2"):
        await d.worker_account(n)
    src, dst = d.folder("WS-D1", "form-out"), d.folder("WS-D2", "form-in")
    mine = d.folder("ADM-01", "form-restricted")
    crowded, out2 = d.folder("WS-D2", "form-crowded"), d.folder("WS-D1", "form-out2")
    d.start_worker("ADM-01", [mine])
    d.start_worker("WS-D1", [src, out2])
    d.start_worker("WS-D2", [dst, crowded])
    check("the Workers are online", await d.online("WS-D1", "WS-D2"))
    admin = d.admin
    p1, p2 = await d.pc_id("WS-D1"), await d.pc_id("WS-D2")
    tag = str(int(time.time()))
    for f in (src, dst, mine, crowded, out2):
        for child in f.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    await asyncio.sleep(4)
    warnings: list[str] = []

    @contextlib.asynccontextmanager
    async def console(view: str, name: str):
        """A fresh console, on the page asked for; yields (window, page)."""
        local = LocalConfig(path=d.folder("shots", "forms") / f"{name}.json", engine_host=ac["engine_host"], engine_port=ac["engine_port"],
                            client_id=ac["client_id"], client_key=ac["client_key"], tls=ac["tls"], ca_cert=ac.get("ca_cert"))
        _app, qml, bridge = create(local)
        qml.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws if "qt.qml.propertyCache" not in w.toString()))
        win = qml.rootObjects()[0]
        try:
            start = time.monotonic()
            while not bridge.isConnected and time.monotonic() - start < 20:
                await settle(0.2)
            await settle(1.0)
            win.showNormal()
            win.resize(1440, 900)
            await settle(1.5)
            win.setProperty("view", view)
            page = None
            for _ in range(80):
                await settle(0.1)
                page = win.findChild(QObject, name)
                if page is not None:
                    break
            await settle(1.0)
            yield win, page
        finally:
            qml.warnings.disconnect()
            qml.deleteLater()
            if bridge.conn is not None:
                await bridge.conn.close()
            await settle(0.3)

    async def flows() -> list:
        return (await admin.call("flow.list"))["flows"]

    # --- F1: New flow, nothing in the way -----------------------------------------------------------------------------------
    before = {f["id"] for f in await flows()}
    async with console("flows/new", "newFlow") as (win1, page):
        check("F1  the New flow page opens", page is not None)
        if page is not None:
            page.setProperty("src", {"pc": p1, "path": str(src)})
            page.setProperty("dests", [{"mode": "mine", "pc": p2, "path": str(dst), "who": 0}])
            await settle(0.5)
            check("F1  the form accepts it (no problem named)", prop(page, "problem") == "", str(prop(page, "problem")))
            QMetaObject.invokeMethod(page, "save")
            await settle(2.0)
            confirm = win1.findChild(QObject, "confirm")
            if confirm is not None and (prop(confirm, "visible") or prop(confirm, "opened")):         # the index still remembered an earlier run's files
                say("      (a leftover of an earlier run was in the destination: confirmed)")
                QMetaObject.invokeMethod(win1.findChild(QObject, "confirmYes"), "clicked")
            check("F1  saving creates the flow in the Engine", await wait_for(lambda: _new_flow(flows, before), 15))
    (src / f"hello-{tag}.txt").write_text("through the form\n", encoding="utf-8")
    check("F1  and it copies", await wait_for(lambda: (dst / f"hello-{tag}.txt").exists(), 30))

    # --- F2: New flow where files are already at the destination ----------------------------------------------------------
    (crowded / "already.txt").write_text("a person's file\n", encoding="utf-8")
    (out2 / "already.txt").write_text("the source's file\n", encoding="utf-8")
    check("F2  the destination's own file is in the index (so the flow can see the collision)",
          await wait_for(lambda: _indexed_file(admin, "already.txt", str(crowded)), 60))
    before = {f["id"] for f in await flows()}
    async with console("flows/new", "newFlow") as (win, page):
        if page is not None:
            page.setProperty("src", {"pc": p1, "path": str(out2)})
            page.setProperty("dests", [{"mode": "mine", "pc": p2, "path": str(crowded), "who": 0}])
            await settle(0.5)
            QMetaObject.invokeMethod(page, "save")
            confirm = None
            for _ in range(40):
                await settle(0.1)
                confirm = win.findChild(QObject, "confirm")
                if confirm is not None and (prop(confirm, "visible") or prop(confirm, "opened")):
                    break
            asked = confirm is not None and bool(prop(confirm, "visible") or prop(confirm, "opened"))
            check("F2  files already at the destination are put to the creator as a question, not an error", asked,
                  f"flows now {[f['id'] for f in await flows()]}, before {sorted(before)}")
            if asked:
                check("F2  and the question says nothing is overwritten", "overwritten" in str(prop(confirm, "cost")), str(prop(confirm, "cost"))[:200])
                QMetaObject.invokeMethod(win.findChild(QObject, "confirmYes"), "clicked")
                check("F2  'Create anyway' makes the flow", await wait_for(lambda: _new_flow(flows, before), 15))
                check("F2  the person's own file is kept beside the new one", await wait_for(lambda: (crowded / "already-modified.txt").exists(), 40),
                      str(sorted(p.name for p in crowded.iterdir())))
                check("F2  and the destination holds the source's file under the name", (crowded / "already.txt").exists()
                      and (crowded / "already.txt").read_text(encoding="utf-8") == "the source's file\n")

    # --- F3: New task, read by the model, then created --------------------------------------------------------------------------
    who = d.state["workers"]["WS-D1"]["account_id"]
    async with console("tasks/new", "newTask") as (_win, page):
        check("F3  the New task page opens", page is not None)
        names = {m["account"]: m["name"] for m in (prop(page, "people") or [])} if page is not None else {}
        person = names.get(who)
        if page is not None and person:
            page.setProperty("text", f"{person} should write forms-{tag}.txt by tomorrow evening.")
            await settle(2.5)
            QMetaObject.invokeMethod(page, "readIt")
            ok = await wait_for(lambda: prop(page, "proposal") is not None, 120)
            check("F3  the model's proposal comes back into the form", ok)
            if ok:
                before_tasks = {t["id"] for t in (await admin.call("task.list"))["tasks"]}
                QMetaObject.invokeMethod(page, "create", Q_ARG("QVariant", False))
                made = await wait_for(lambda: _new_task(admin, before_tasks, f"forms-{tag}"), 20)
                why = ""
                if not made:
                    t0 = (prop(page, "tasks") or [{}])[0]
                    payload = {"description": t0.get("phrase"), "assignee_account_id": t0.get("whoAccount"),
                               "verification_mode": "stack" if t0.get("checks") else "none",
                               "items": [{"target_type": c["target_type"], "intent": c["intent"], "name": c["name"], "path": c.get("path"),
                                          "file_index_id": c.get("file_index_id"), "linked_item_index": c.get("linked_item_index"),
                                          "populated_by": "llm" if c.get("src") == "model" else "manual"} for c in t0.get("checks", [])]}
                    if t0.get("final"):
                        payload["final_deadline_at"] = t0["final"]
                    try:
                        await admin.call("task.create", payload)
                        why = "the same payload is accepted by the Engine (the form did not send it)"
                    except Exception as exc:  # noqa: BLE001
                        why = f"{getattr(exc, 'code', '')}: {getattr(exc, 'message', exc)}  payload={payload}"
                check("F3  creating it makes the task in the Engine, for that person", made, why)
        else:
            check("F3  the signed-in person is known to the form", False, f"{person!r} among {names}")

    # --- F4: Mark files ------------------------------------------------------------------------------------------------------------
    secret = mine / f"form-secret-{tag}.txt"
    secret.write_text(f"restricted via the form {tag}\n", encoding="utf-8")
    await wait_for(lambda: _seen(admin, secret), 40)
    async with console("restricted/mark", "markFiles") as (_win, page):
        check("F4  the Mark files page opens", page is not None)
        if page is not None:
            await settle(1.5)
            tree = prop(page, "tree") or {}
            key = next((k for k, n in (tree.get("byKey") or {}).items()
                        if str(n.get("path", "")).replace("\\", "/").lower() == str(secret).replace("\\", "/").lower()), None)
            check("F4  the file is in the page's tree", key is not None)
            if key is not None:
                page.setProperty("checked", [key])
                page.setProperty("keep", "path")
                await settle(0.3)
                QMetaObject.invokeMethod(page, "mark")
                check("F4  marking it makes the mark in the Engine, kept to its place", await wait_for(lambda: _marked(admin, secret), 15))
    bad = [w for w in warnings if "TypeError" in w or "ReferenceError" in w]
    check("no QML error appeared while the forms were used", not bad, "; ".join(bad)[:300])
    for f in await flows():
        if str(f["source_path"]).startswith(str(d.folder("WS-D1"))):
            with contextlib.suppress(Exception):
                await admin.call("flow.delete", {"flow_id": f["id"]})
    say("(forms done)")
    _ = Path


async def _new_flow(flows, before) -> bool:
    return any(f["id"] not in before for f in await flows())


async def _new_task(admin, before, needle: str) -> bool:
    return any(t["id"] not in before and needle in (t.get("description_raw") or "") for t in (await admin.call("task.list"))["tasks"])


async def _indexed_file(admin, name: str, folder: str) -> bool:
    found = (await admin.call("index.search", {"query": name.rsplit(".", 1)[0]}))["results"]
    return any(str(f["path"]).replace("\\", "/").lower().startswith(folder.replace("\\", "/").lower()) for f in found)


async def _seen(admin, path) -> bool:
    tree = await admin.call("marks.tree")
    want = str(path).replace("\\", "/").lower()
    return any(f["path"].replace("\\", "/").lower() == want for f in tree["files"])


async def _marked(admin, path) -> bool:
    marks = (await admin.call("marks.list", {"scope": "mine"}))["marks"]
    return any(str(m["path"]).replace("\\", "/").lower() == str(path).replace("\\", "/").lower() and m["keep"] == "path" for m in marks)
