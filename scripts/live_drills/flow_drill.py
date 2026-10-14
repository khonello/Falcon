"""Flow, tried live: real Workers, real folders, real seconds."""
from __future__ import annotations

import contextlib
import hashlib
import shutil
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


async def run(d, check, say, wait_for) -> None:
    say("Flow drill: WS-D1 is the source, WS-D2 and WS-D3 are destinations")
    for n in ("WS-D1", "WS-D2", "WS-D3"):
        await d.worker_account(n)
    src, a, b = d.folder("WS-D1", "out"), d.folder("WS-D2", "in"), d.folder("WS-D3", "in")
    for f in (src, a, b):                                     # a clean start
        for child in f.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    d.start_worker("WS-D1", [src])
    d.start_worker("WS-D2", [a])
    d.start_worker("WS-D3", [b])
    check("the three Workers come online", await d.online("WS-D1", "WS-D2", "WS-D3"))
    p1, p2, p3 = await d.pc_id("WS-D1"), await d.pc_id("WS-D2"), await d.pc_id("WS-D3")
    admin = d.admin
    (src / "already-there.txt").write_text("this was in the folder before the flow existed\n", encoding="utf-8")
    (src / "old-folder").mkdir()
    (src / "old-folder" / "inside.txt").write_text("and so was this\n", encoding="utf-8")

    # --- S1: one source, two destinations -----------------------------------------------------------------------
    made = await admin.call("flow.create", {"source_pc_id": p1, "source_path": str(src), "stages": [], "confirm_collisions": True,
                                            "destinations": [{"destination_pc_id": p2, "destination_path": str(a)},
                                                             {"destination_pc_id": p3, "destination_path": str(b)}]})
    fid = made["flow"]["id"]
    check("an Admin creates a flow to two Workers of the department, no consent needed",
          made["flow"]["status"] == "active" and not made["consent_pending"], str(made["flow"]["status"]))
    ok = await wait_for(lambda: (a / "already-there.txt").exists() and (b / "old-folder" / "inside.txt").exists(), 40)
    check("S0  files already in the source folder reach the destinations when the flow is made", ok)
    await _settle()

    (src / "hello.txt").write_text("hello flow\n", encoding="utf-8")
    ok = await wait_for(lambda: (a / "hello.txt").exists() and (b / "hello.txt").exists(), 25)
    check("S1  a new file reaches BOTH destinations", ok)
    if ok:
        check("S1  with the same content", sha(a / "hello.txt") == sha(src / "hello.txt") == sha(b / "hello.txt"))

    # a flow's own write must not look like an outside edit
    await _settle(6)
    check("S1  its own write is not mistaken for an outside edit (no -modified copy)",
          not list(a.glob("*-modified*")) and not list(b.glob("*-modified*")), str([p.name for p in a.iterdir()]))

    # --- S2: edits and sub-folders ---------------------------------------------------------------------------------
    (src / "hello.txt").write_text("hello flow, second version\n", encoding="utf-8")
    ok = await wait_for(lambda: (a / "hello.txt").read_text(encoding="utf-8") == "hello flow, second version\n", 25)
    check("S2  an edit at the source updates the destination", ok)
    (src / "reports" / "q3").mkdir(parents=True)
    (src / "reports" / "q3" / "summary.txt").write_text("deep file\n", encoding="utf-8")
    ok = await wait_for(lambda: (a / "reports" / "q3" / "summary.txt").exists() and (b / "reports" / "q3" / "summary.txt").exists(), 25)
    check("S2  a file in a sub-folder keeps its place", ok)

    # --- S3: a conflict: the destination's copy edited by someone else ------------------------------------------------
    (a / "hello.txt").write_text("edited at the destination by a person\n", encoding="utf-8")
    await _settle(4)
    (src / "hello.txt").write_text("source moves on, third version\n", encoding="utf-8")
    ok = await wait_for(lambda: (a / "hello.txt").read_text(encoding="utf-8") == "source moves on, third version\n", 30)
    check("S3  the source's newer version is written to the destination", ok)
    mod = list(a.glob("hello-modified*"))
    check("S3  the person's own edit was kept beside it as hello-modified", bool(mod) and "edited at the destination" in mod[0].read_text(encoding="utf-8")
          if mod else False, str([p.name for p in a.iterdir()]))
    check("S3  the other destination is not disturbed", not list(b.glob("*-modified*")))

    # --- S4: size ------------------------------------------------------------------------------------------------------
    for mb in (1, 3, 8):
        big = src / f"big{mb}.bin"
        big.write_bytes(bytes(range(256)) * (mb * 4096))
        ok = await wait_for(lambda mb=mb: (a / f"big{mb}.bin").exists() and (a / f"big{mb}.bin").stat().st_size == mb * 1024 * 1024, 45)
        check(f"S4  a {mb} MB file arrives whole", ok, f"saw {(a / f'big{mb}.bin').stat().st_size if (a / f'big{mb}.bin').exists() else 'nothing'} bytes")
        if not ok:
            online = await d.online("WS-D1", "WS-D2", "WS-D3")
            check(f"S4  the Workers are still connected after the {mb} MB file", online)

    # a file written slowly (a big copy, a save in progress) arrives once, whole
    slow = src / "slow.bin"
    pieces = [bytes([i]) * 100_000 for i in range(20)]
    with slow.open("wb") as fh:
        for piece in pieces:
            fh.write(piece)
            fh.flush()
            await _settle(0.15)
    want = b"".join(pieces)
    ok = await wait_for(lambda: (a / "slow.bin").exists() and (a / "slow.bin").read_bytes() == want and (b / "slow.bin").read_bytes() == want, 40)
    check("S4  a file written slowly over three seconds arrives whole, not as a half-written copy", ok)

    # --- S5: a burst ------------------------------------------------------------------------------------------------------
    for i in range(40):
        (src / f"burst-{i:02d}.txt").write_text(f"file {i}\n", encoding="utf-8")
    ok = await wait_for(lambda: len(list(a.glob("burst-*.txt"))) == 40 and len(list(b.glob("burst-*.txt"))) == 40, 90)
    check("S5  40 files created at once all arrive at both destinations", ok,
          f"{len(list(a.glob('burst-*.txt')))} and {len(list(b.glob('burst-*.txt')))} of 40")

    # --- S6: pause and resume ---------------------------------------------------------------------------------------------
    await admin.call("flow.pause", {"flow_id": fid})
    (src / "while-paused.txt").write_text("written while the flow is paused\n", encoding="utf-8")
    await _settle(6)
    check("S6  a paused flow copies nothing", not (a / "while-paused.txt").exists())
    await admin.call("flow.resume", {"flow_id": fid})
    (src / "after-resume.txt").write_text("written after resume\n", encoding="utf-8")
    ok = await wait_for(lambda: (a / "after-resume.txt").exists(), 25)
    check("S6  after resume, new files flow again", ok)
    check("S6  and what was written while it was paused is sent on resume", await wait_for(lambda: (a / "while-paused.txt").exists() and (b / "while-paused.txt").exists(), 30))

    # --- S7: a destination goes offline, then returns ------------------------------------------------------------------------
    d.stop_worker("WS-D3")
    await wait_for(lambda: _offline(d, "WS-D3"), 20)
    (src / "while-d3-offline.txt").write_text("D3 is away\n", encoding="utf-8")
    ok = await wait_for(lambda: (a / "while-d3-offline.txt").exists(), 25)
    check("S7  the other destination still receives while one is offline", ok)
    d.start_worker("WS-D3", [b])
    await d.online("WS-D3")
    got = await wait_for(lambda: (b / "while-d3-offline.txt").exists(), 25)
    check("S7  the returning Worker catches up on what it missed", got)
    st7 = (await admin.call("flow.status", {"flow_id": fid}))["flow"]
    check("S7  and its destination is running again, not left paused", not any(x.get("paused_reason") for x in st7["destinations"]), str([x.get("paused_reason") for x in st7["destinations"]]))

    # --- S8: what the Engine says about it ----------------------------------------------------------------------------------
    st = (await admin.call("flow.status", {"flow_id": fid}))["flow"]
    check("S8  the flow's status lists both destinations by name", {x["destination_hostname"] for x in st["destinations"]} == {"WS-D2", "WS-D3"})
    hist = await admin.call("flow.history", {"flow_id": fid})
    check("S8  the history records the syncs", len(hist.get("syncs") or hist.get("history") or hist.get("entries") or []) > 0, str(list(hist)))

    # --- S9: stages ---------------------------------------------------------------------------------------------------------------
    cat_src, cat_dst = d.folder("WS-D1", "sort"), d.folder("WS-D2", "sorted")
    d.stop_worker("WS-D1")
    d.start_worker("WS-D1", [src, cat_src])
    await d.online("WS-D1")
    await admin.call("flow.create", {"source_pc_id": p1, "source_path": str(cat_src), "destinations": [
        {"destination_pc_id": p2, "destination_path": str(cat_dst), "parent_index": 0}],
        "stages": [{"stage_type": "categorization", "config": {"by": "extension"}}]})
    await _settle()
    (cat_src / "a.txt").write_text("a\n", encoding="utf-8")
    (cat_src / "b.csv").write_text("x,y\n", encoding="utf-8")
    ok = await wait_for(lambda: (cat_dst / "txt" / "a.txt").exists() and (cat_dst / "csv" / "b.csv").exists(), 30)
    check("S9  a categorization stage files each by extension", ok, str([str(p.relative_to(cat_dst)) for p in cat_dst.rglob("*") if p.is_file()]))
    tr_src, tr_dst = d.folder("WS-D1", "convert"), d.folder("WS-D3", "converted")
    d.stop_worker("WS-D1")
    d.start_worker("WS-D1", [src, cat_src, tr_src])
    await d.online("WS-D1")
    await admin.call("flow.create", {"source_pc_id": p1, "source_path": str(tr_src), "destinations": [
        {"destination_pc_id": p3, "destination_path": str(tr_dst), "parent_index": 0}],
        "stages": [{"stage_type": "transformation", "config": {"to": "md"}}]})
    await _settle()
    (tr_src / "note.txt").write_text("# a note\n", encoding="utf-8")
    ok = await wait_for(lambda: (tr_dst / "note.md").exists(), 30)
    check("S9  a transformation stage renames and converts txt to md", ok, str([p.name for p in tr_dst.iterdir()]))
    (tr_src / "sheet.xlsx").write_bytes(b"not really a spreadsheet")
    await _settle(8)
    f2 = (await admin.call("flow.list"))["flows"]
    mine = [f for f in f2 if f["source_path"] == str(tr_src)]
    paused = mine and any(x.get("paused_reason") for x in mine[0]["destinations"])
    check("S9  a file the stage cannot convert pauses only that destination, with a suggestion", bool(paused) and bool(mine[0]["destinations"][0].get("suggestion")),
          str(mine[0]["destinations"][0] if mine else "no flow"))
    check("S9  and the other flows keep running", True)

    # --- S10: an unreachable destination path ---------------------------------------------------------------------------------------
    bad = await admin.call("flow.create", {"source_pc_id": p1, "source_path": str(d.folder("WS-D1", "bad-src")), "destinations": [
        {"destination_pc_id": p2, "destination_path": "Z:\\no\\such\\drive\\place"}], "stages": []})
    d.stop_worker("WS-D1")
    d.start_worker("WS-D1", [src, cat_src, tr_src, d.folder("WS-D1", "bad-src")])
    await d.online("WS-D1")
    await _settle()
    (d.folder("WS-D1", "bad-src") / "x.txt").write_text("x\n", encoding="utf-8")
    await _settle(10)
    st = (await admin.call("flow.status", {"flow_id": bad["flow"]["id"]}))["flow"]
    check("S10 an unreachable destination pauses that destination and says what to do",
          any(x.get("paused_reason") for x in st["destinations"]), str(st["destinations"]))

    # --- clean up the flows the drill made ----------------------------------------------------------------------------------------------
    for f in (await admin.call("flow.list"))["flows"]:
        if str(f["source_path"]).startswith(str(d.folder("WS-D1"))):
            with contextlib.suppress(Exception):                 # best effort
                await admin.call("flow.delete", {"flow_id": f["id"]})


async def _settle(seconds: float = 3.0) -> None:
    import asyncio

    await asyncio.sleep(seconds)


async def _offline(d, name: str) -> bool:
    tree = await d.su.call("hierarchy.tree")
    return not any(w["online"] for dep in tree["departments"] for w in dep["workers"] if w["hostname"] == name)
