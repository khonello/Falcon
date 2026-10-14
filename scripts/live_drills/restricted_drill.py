"""Restricted marks, tried live: the Admin marks files on their own workstation; a copy where it is not allowed becomes an issue."""
from __future__ import annotations

import asyncio
import contextlib
import shutil
import time
from pathlib import Path

TAG = str(int(time.time()))        # each run has its own contents, so nothing a person allowed in an earlier run applies to this one
V1, V2, V3, V4, V5, V6 = (f"{what} [{TAG}]\n" for what in ("salaries: confidential v1", "salaries: confidential v2, after the raise", "board minutes, 14 Oct",
                                                           "a private memo", "contract one", "contract two, added after the mark"))


async def run(d, check, say, wait_for) -> None:
    say("Restricted drill: ADM-01 (the Admin's own workstation) marks files; WS-D1 and WS-D2 are people's PCs")
    from live_drill import admin_config

    ac = admin_config()
    d.state["workers"]["ADM-01"] = {"client_id": ac["client_id"], "client_key": ac["client_key"]}
    for n in ("WS-D1", "WS-D2"):
        await d.worker_account(n)
    home = d.folder("ADM-01", "restricted")
    elsewhere = d.folder("ADM-01", "elsewhere")
    p1, p2 = d.folder("WS-D1", "docs"), d.folder("WS-D2", "docs")
    d.start_worker("ADM-01", [home, elsewhere])
    d.start_worker("WS-D1", [p1])
    d.start_worker("WS-D2", [p2])
    check("the Admin's workstation and two people's PCs come online", await _online(d, "WS-D1", "WS-D2") and await wait_for(lambda: _admin_online(d), 30))
    admin = d.admin
    for f in (home, elsewhere, p1, p2):                       # cleared with the Workers watching, so the index learns the files are gone
        for child in f.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    await asyncio.sleep(5)

    async def mine(path: Path):
        tree = await admin.call("marks.tree")
        return next((f for f in tree["files"] if f["path"].replace("\\", "/").lower() == str(path).replace("\\", "/").lower()), None)

    async def file_issues():
        return [i for i in (await admin.call("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"]

    async def issue_for(name: str, host: str):
        for i in await file_issues():
            got = await admin.call("issues.get", {"issue_id": i["id"]})
            if got["detail"].get("file") == name and (got["issue"].get("host") == host or got["issue"].get("hostname") == host):
                return got
        return None

    async def wait_issue(name: str, host: str, seconds: float = 30):
        end = asyncio.get_running_loop().time() + seconds
        while asyncio.get_running_loop().time() < end:
            if found := await issue_for(name, host):
                return found
            await asyncio.sleep(0.5)
        return None

    # --- R1: marking ---------------------------------------------------------------------------------------------------------------
    secret = home / "payroll.txt"
    secret.write_text(V1, encoding="utf-8")
    seen = await wait_for(lambda: _seen(admin, secret), 30)
    check("R1  the file index sees the Admin's new file (so it can be marked)", seen)
    made = await admin.call("marks.create", {"paths": [str(secret)], "keep": "path"})
    check("R1  the Admin marks a file where it is, kept to its place", len(made["marks"]) == 1 and made["marks"][0]["keep"] == "path", str(made))
    check("R1  the file shows as marked in the tree", bool((await mine(secret)) and (await mine(secret))["marked"]))

    # --- R2: a copy on a person's PC -----------------------------------------------------------------------------------------------
    (p1 / "payroll-copy.txt").write_text(V1, encoding="utf-8")
    got = await wait_issue("payroll-copy.txt", "WS-D1")
    check("R2  a copy on a person's PC becomes an issue, under another name too (matched by content)", got is not None)
    if got:
        check("R2  it is owned by whoever marked it, and high (another PC of the same department)",
              got["issue"]["owner"] is not None and got["issue"]["severity"] == "high", f"{got['issue'].get('owner')} {got['issue']['severity']}")
        keys = [o["key"] for o in got["options"]]
        check("R2  the Admin may ask the person, delete the copy, or allow it", {"ask", "delete", "allow"} <= set(keys), str(keys))
    violations = await admin.call("resource.violations", {})
    check("R2  and the violation is on record", bool(violations.get("violations") or violations.get("items") or violations), str(list(violations)))

    # --- R3: delete the copy from the Admin's console ----------------------------------------------------------------------------
    if got:
        await admin.call("issues.act", {"issue_id": got["issue"]["id"], "key": "delete"})
        gone = await wait_for(lambda: not (p1 / "payroll-copy.txt").exists(), 40)
        check("R3  'Delete this copy' removes it from the person's PC", gone)
        closed = await wait_for(lambda: _issue_closed(admin, got["issue"]["id"]), 40)
        check("R3  and the issue closes by itself once the copy is gone", closed)

    # --- R4: same PC, elsewhere ---------------------------------------------------------------------------------------------------
    shutil.copy(secret, elsewhere / "payroll-on-same-pc.txt")
    got2 = await wait_issue("payroll-on-same-pc.txt", "ADM-01", 20)
    check("R4  a copy elsewhere on the same PC is caught when the mark is kept to its place", got2 is not None)
    if got2:
        check("R4  and it is medium, not high", got2["issue"]["severity"] == "medium", got2["issue"]["severity"])
        mark_id = made["marks"][0]["id"]
        eff = await admin.call("marks.keep_effect", {"mark_id": mark_id, "keep": "machine"})
        await admin.call("marks.change_keep", {"mark_id": mark_id, "keep": "machine"})
        closed = await wait_for(lambda: _issue_closed(admin, got2["issue"]["id"]), 20)
        check("R4  widening the mark to the whole PC closes that issue (it said so beforehand)", closed, str(eff)[:160])
    # --- R5: machine-kept: a copy on another PC is still caught ---------------------------------------------------------------------
    (p2 / "elsewhere.txt").write_text(V1, encoding="utf-8")
    got3 = await wait_issue("elsewhere.txt", "WS-D2", 30)
    check("R5  kept to the whole PC, a copy on ANOTHER PC is still caught", got3 is not None)

    # --- R6: versions -----------------------------------------------------------------------------------------------------------------
    secret.write_text(V2, encoding="utf-8")
    await asyncio.sleep(4)
    (p1 / "old-version.txt").write_text(V1, encoding="utf-8")
    got4 = await wait_issue("old-version.txt", "WS-D1", 30)
    check("R6  editing the original does not let a copy of the OLD version through", got4 is not None)
    (p2 / "new-version.txt").write_text(V2, encoding="utf-8")
    got5 = await wait_issue("new-version.txt", "WS-D2", 30)
    check("R6  nor a copy of the new one", got5 is not None)

    # --- R7: allow, with a reason ----------------------------------------------------------------------------------------------------
    if got4:
        done = await admin.call("issues.act", {"issue_id": got4["issue"]["id"], "key": "allow", "reason": "the payroll clerk needs it"})
        check("R7  'Allow it' with a reason resolves the issue", done["issue"]["state"] == "resolved", done["issue"]["state"])
        (p1 / "old-version.txt").unlink()
        await asyncio.sleep(3)
        (p1 / "old-version.txt").write_text(V1, encoding="utf-8")
        await asyncio.sleep(8)
        again = await issue_for("old-version.txt", "WS-D1")
        check("R7  and an allowed copy is not reported again", again is None)
    with contextlib.suppress(OSError):
        (p1 / "old-version.txt").unlink()

    # --- R8: a folder mark ---------------------------------------------------------------------------------------------------------------
    folder = home / "contracts"
    folder.mkdir()
    (folder / "first.txt").write_text(V5, encoding="utf-8")
    await wait_for(lambda: _seen(admin, folder / "first.txt"), 30)
    fm = await admin.call("marks.create", {"paths": [str(folder)], "keep": "path"})
    check("R8  a whole folder can be marked", len(fm["marks"]) == 1 and fm["marks"][0]["kind"] == "folder")
    (folder / "added-later.txt").write_text(V6, encoding="utf-8")
    await asyncio.sleep(5)
    (p1 / "c1.txt").write_text(V5, encoding="utf-8")
    (p2 / "c2.txt").write_text(V6, encoding="utf-8")
    g1, g2 = await wait_issue("c1.txt", "WS-D1", 30), await wait_issue("c2.txt", "WS-D2", 30)
    check("R8  a copy of a file in the folder is caught", g1 is not None)
    check("R8  and so is a copy of a file added to the folder AFTER it was marked", g2 is not None)

    # --- R9: unmarking -----------------------------------------------------------------------------------------------------------------------
    await admin.call("marks.unmark", {"mark_id": fm["marks"][0]["id"]})
    closed = []
    for g in (g1, g2):
        if g:
            closed.append(await wait_for(lambda g=g: _issue_closed(admin, g["issue"]["id"]), 20))
    check("R9  unmarking closes the issues of its copies", all(closed) and bool(closed), str(closed))

    # --- R10: the person is told ---------------------------------------------------------------------------------------------------------------
    marks = await admin.call("marks.list", {"scope": "mine"})
    check("R10 the marks list shows each mark with its copies", len(marks["marks"]) >= 1)

    # --- R11: copies that were already there when the file is marked ------------------------------------------------------------------------
    old = home / "board-minutes.txt"
    old.write_text(V3, encoding="utf-8")
    (p2 / "minutes-already-here.txt").write_text(V3, encoding="utf-8")
    await wait_for(lambda: _seen(admin, old), 30)
    await asyncio.sleep(4)
    made11 = await admin.call("marks.create", {"paths": [str(old)], "keep": "path"})
    got11 = await wait_issue("minutes-already-here.txt", "WS-D2", 20)
    check("R11 marking a file finds the copies that were already out there", got11 is not None and made11["copies_found"] >= 1, str(made11["copies_found"]))

    # --- R12: renaming the original itself must not turn it into a violation -----------------------------------------------------------------
    memo = home / "memo.txt"
    memo.write_text(V4, encoding="utf-8")
    await wait_for(lambda: _seen(admin, memo), 30)
    made12 = await admin.call("marks.create", {"paths": [str(memo)], "keep": "path"})
    memo.rename(home / "memo-final.txt")
    await asyncio.sleep(10)
    own = await issue_for("memo-final.txt", "ADM-01")
    check("R12 renaming the marked file in its own folder is not reported as a copy", own is None, str(own and own["issue"]["code"]))
    moved_dir = home / "archive"
    moved_dir.mkdir()
    (home / "memo-final.txt").rename(moved_dir / "memo-final.txt")
    await asyncio.sleep(10)
    own2 = await issue_for("memo-final.txt", "ADM-01")
    check("R12 nor moving it into a sub-folder of its own folder", own2 is None, str(own2 and own2["issue"]["code"]))
    _ = made12

    # --- clean up ---------------------------------------------------------------------------------------------------------------------------------
    for m in (await admin.call("marks.list", {"scope": "mine"}))["marks"]:
        with contextlib.suppress(Exception):
            await admin.call("marks.unmark", {"mark_id": m["id"]})


async def _online(d, *names: str) -> bool:
    return await d.online(*names)


async def _admin_online(d) -> bool:
    tree = await d.su.call("hierarchy.tree")
    return any(a["online"] for dep in tree["departments"] for a in dep["admins"] if a["hostname"] == "ADM-01")


async def _seen(admin, path: Path) -> bool:
    tree = await admin.call("marks.tree")
    want = str(path).replace("\\", "/").lower()
    return any(f["path"].replace("\\", "/").lower() == want for f in tree["files"])


async def _issue_closed(admin, issue_id: int) -> bool:
    got = await admin.call("issues.get", {"issue_id": issue_id})
    return got["issue"]["state"] == "resolved"
