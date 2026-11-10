"""Fill the dev Engine with work in every state, so each page of ADM-01's console has something to show (the user, 10 Nov 2026).

    environ-operator\\Scripts\\python.exe scripts\\seed_dev.py           seeds, then keeps the machines running (online) until Ctrl+C
    environ-operator\\Scripts\\python.exe scripts\\seed_dev.py --stop    seeds, then stops the machines (they show as offline)

Nothing is written to a table by hand: everything goes through the Engine as the Admin in `data/admin.json` (ADM-01) and as real Worker
processes (WS-D1, WS-D2, WS-D3 from `data/drill/state.json`, and ADM-01's own machine), the way the console and the machines do it. Their
files live under `data/seed/` (git-ignored). It needs the Engine running on the dev database (`python -m engine`), never the test one.
Run it again and it starts over: its own marks are lifted and its own flows deleted first; a task it already gave that is still open is
not given twice.

What it leaves:
  Protected files  a Restricted file with a copy caught on WS-D2, a Private file only WS-D1's person may open, a watched folder that changed
  Flows            one copying as it happens, one that copies only when run (run once), one paused, one held at something restricted
  Tasks            waiting for your verdict, on track, not started, quiet, and completed
  Messages         a conversation with WS-D1's person, and a request to talk from WS-D2
  Announcements    one sent to everyone, one waiting to go out
  Calendar         the tasks' deadlines and three to-dos, one past its date
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from live_drill import Drill, connect, wait_for

from common import dotenv

HOME = ROOT / "data" / "seed"
FOLDERS = {"WS-D1": ["Documents", "Reports"], "WS-D2": ["Inbox"], "WS-D3": ["Shared", "Archive"], "ADM-01": ["Finance", "HR", "Board"]}
FILES = {
    "WS-D1/Documents/notes.txt": "Notes for the week\n",
    "WS-D1/Documents/price-list.csv": "Item,Price\nPaper,4.50\nToner,62.00\n",
    "WS-D1/Reports/sales-october.csv": "Region,Sales\nNorth,1200\nSouth,900\n",
    "WS-D1/Reports/visits-october.csv": "Client,Visits\nAsante,4\nBoateng,2\n",
    "WS-D3/Archive/tender-2025-01.txt": "tender one\n",
    "WS-D3/Archive/tender-2025-02.txt": "tender two\n",
    "ADM-01/Finance/payroll-november.xlsx": "Name,Salary\nAma,4000\nKofi,3800\nEsi,4100\n",
    "ADM-01/Finance/budget-2027.xlsx": "Line,Amount\nStaff,120000\nRent,24000\n",
    "ADM-01/HR/reviews-2026.docx": "Annual reviews 2026\n",
    "ADM-01/Board/minutes-october.docx": "Board minutes, October\n",
    "ADM-01/Board/strategy-2027.pptx": "Strategy 2027\n",
}
TASKS = [  # who, what, file, folder, deadline in hours, what the seed does with it
    ("WS-D1", "Write the weekly sales summary", "summary-week-45.txt", "WS-D1/Documents", 20, "hand_in"),
    ("WS-D1", "Update the price list for December", "price-list-december.csv", "WS-D1/Documents", 30, "complete"),
    ("WS-D2", "Fill in the November stock count", "stock-count-november.csv", "WS-D2/Inbox", 6, "start"),
    ("WS-D3", "Move last year's tender files to the archive", "tenders-moved.txt", "WS-D3/Shared", 72, "leave"),
    ("WS-D2", "Send the delivery schedule for next week", "delivery-schedule.xlsx", "WS-D2/Inbox", 0.15, "start_quiet"),
]


def when(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def said(what: str, ok: bool = True, why: str = "") -> None:
    print(f"  {'made' if ok else 'not made'}  {what}" + (f"  ({why})" if why else ""), flush=True)


async def step(what: str, coro: Any) -> Any:
    try:
        res = await coro
        said(what)
        return res
    except Exception as exc:                                                    # noqa: BLE001 -- one thing that cannot be made does not stop the rest
        said(what, False, str(exc)[:160])
        return None


def refuse_test_database() -> None:
    dotenv.load()
    dev, test = os.environ.get("FALCON_DATABASE_URL"), os.environ.get("FALCON_TEST_DATABASE_URL")
    if not dev or dev == test:
        sys.exit("seed_dev: the Engine's database is not set, or it is the test database; this only seeds the dev database")


async def main(stop_after: bool) -> int:
    refuse_test_database()
    d = Drill()
    await d.start()
    a = d.admin
    assert a is not None
    print("Clearing what an earlier seed left", flush=True)
    for m in (await a.call("marks.list", {"scope": "all"}))["marks"]:
        if "\\seed\\" in str(m.get("path") or "") or "/seed/" in str(m.get("path") or ""):
            await step(f"lifted {m['name']}", a.call("marks.unmark", {"mark_id": m["id"]}))
    for f in (await a.call("flow.list"))["flows"]:
        if "seed" in str(f.get("source_path") or ""):
            await step(f"deleted flow {f.get('name') or f['id']}", a.call("flow.delete", {"flow_id": f["id"]}))
    if HOME.exists():
        shutil.rmtree(HOME, ignore_errors=True)
    for machine, names in FOLDERS.items():
        for name in names:
            (HOME / machine / name).mkdir(parents=True, exist_ok=True)
    for rel, text in FILES.items():
        (HOME / rel).write_text(text, encoding="utf-8")

    # --- the people talk first, each on a short connection of their own, before their machines start ------------------------------------------
    print("Messages", flush=True)
    w1, w2 = await d.worker_account("WS-D1"), await d.worker_account("WS-D2")
    await d.worker_account("WS-D3")
    convo = await step("a conversation with WS-D1's person", a.call("chat.open", {"account_id": w1["account_id"]}))
    if convo:
        cid = convo["conversation"]["conversation_id"] if "conversation" in convo else convo["conversation_id"]
        await step("  a message to them", a.call("chat.send", {"conversation_id": cid, "body": "Morning. Is the October sales report in the Reports folder yet?"}))
        person = await connect({**d.engine_cfg, "client_id": w1["client_id"], "client_key": w1["client_key"]})
        try:
            await step("  their answer", person.call("chat.send", {"conversation_id": cid, "body": "Yes, sales-october.csv is there. Visits too."}))
        finally:
            await person.close()
    other = await connect({**d.engine_cfg, "client_id": w2["client_id"], "client_key": w2["client_key"]})
    try:
        await step("a request to talk from WS-D2's person", other.call("chat.ask", {"line": "The stock count sheet will not open on my machine"}))
    finally:
        await other.close()

    # --- the machines -----------------------------------------------------------------------------------------------------------------
    print("Starting the machines", flush=True)
    for machine, names in FOLDERS.items():
        d.start_worker(machine, [HOME / machine / n for n in names])
    if not await d.online("WS-D1", "WS-D2", "WS-D3"):
        print("  a machine did not come online: see data/drill/<name>/worker.log", flush=True)
    pc = {h: await d.pc_id(h) for h in FOLDERS}
    files = HOME / "ADM-01"

    async def seen(path: Path) -> bool:                                         # the index has it: ADM-01's machine told the Engine
        tree = await a.call("marks.tree")
        return any(Path(f["path"]).resolve() == path.resolve() for f in tree.get("files", []))
    await wait_for(lambda: seen(files / "Board" / "strategy-2027.pptx"), 40)

    # --- Protected files ----------------------------------------------------------------------------------------------------------------
    print("Protected files", flush=True)
    payroll = files / "Finance" / "payroll-november.xlsx"
    await step("payroll-november.xlsx, restricted to its place", a.call("marks.create", {"paths": [str(payroll)], "protection": "restricted", "keep": "path"}))
    await step("reviews-2026.docx, private to WS-D1's person", a.call("marks.create", {"paths": [str(files / "HR" / "reviews-2026.docx")], "protection": "private",
                                                                                    "keep": "machine", "readers": [w1["account_id"]], "allow_system": True}))
    await step("the Board folder, watched", a.call("marks.create", {"paths": [str(files / "Board")], "protection": "watch", "keep": "machine"}))
    await asyncio.sleep(2)
    (files / "Board" / "minutes-october.docx").write_text("Board minutes, October (corrected)\n", encoding="utf-8")       # the watched folder changes
    shutil.copyfile(payroll, HOME / "WS-D2" / "Inbox" / "payroll-november.xlsx")                                          # and a restricted copy turns up
    said("a change in the watched folder, and a copy of the payroll on WS-D2")

    # --- Flows -------------------------------------------------------------------------------------------------------------------------
    print("Flows", flush=True)
    await step("reports-to-inbox, copying as it happens", a.call("flow.create", {
        "name": "reports-to-inbox", "source_pc_id": pc["WS-D1"], "source_path": str(HOME / "WS-D1" / "Reports"), "stages": [], "confirm_collisions": True,
        "destinations": [{"destination_pc_id": pc["WS-D2"], "destination_path": str(HOME / "WS-D2" / "Inbox")}]}))
    manual = await step("documents-to-shared, only when it is run", a.call("flow.create", {
        "name": "documents-to-shared", "run_mode": "manual", "source_pc_id": pc["WS-D1"], "source_path": str(HOME / "WS-D1" / "Documents"), "stages": [],
        "confirm_collisions": True, "destinations": [{"destination_pc_id": pc["WS-D3"], "destination_path": str(HOME / "WS-D3" / "Shared")}]}))
    if manual:
        await step("  run once", a.call("flow.run", {"flow_id": manual["flow"]["id"]}))
    held = await step("archive-back, paused", a.call("flow.create", {
        "name": "archive-back", "source_pc_id": pc["WS-D3"], "source_path": str(HOME / "WS-D3" / "Archive"), "stages": [], "confirm_collisions": True,
        "destinations": [{"destination_pc_id": pc["WS-D1"], "destination_path": str(HOME / "WS-D1" / "Documents")}]}))
    if held:
        await step("  paused", a.call("flow.pause", {"flow_id": held["flow"]["id"]}))
    await step("finance-to-shared, held at something restricted", a.call("flow.create", {
        "name": "finance-to-shared", "source_pc_id": pc["ADM-01"], "source_path": str(files / "Finance"), "stages": [], "confirm_collisions": True,
        "destinations": [{"destination_pc_id": pc["WS-D3"], "destination_path": str(HOME / "WS-D3" / "Shared")}]}))

    # --- Tasks ---------------------------------------------------------------------------------------------------------------------------
    print("Tasks", flush=True)
    open_already = {t["description_raw"] for t in (await a.call("task.list"))["tasks"] if t["status"] != "completed"}
    for who, what, name, folder, hours, then in TASKS:
        if what in open_already:
            said(f"{what} (still open from an earlier seed)")
            continue
        w = await d.worker_account(who)
        made = await step(what, a.call("task.create", {
            "assignee_account_id": w["account_id"], "description": f"{what}: {name}", "verification_mode": "stack",
            "items": [{"target_type": "file", "intent": "create", "name": name, "path": str(HOME / folder)}],
            "soft_deadline_at": when(hours * 0.7) if hours > 1 else None, "final_deadline_at": when(hours)}))
        if not made or then == "leave":
            continue
        tid = made["task"]["id"]
        person = await connect({**d.engine_cfg, "client_id": w["client_id"], "client_key": w["client_key"]})
        try:
            await step("  started by them", person.call("task.start", {"task_id": tid}))
        finally:
            await person.close()
        if then in ("hand_in", "complete"):
            (HOME / folder / name).write_text(f"{what}\n", encoding="utf-8")

            async def found(t: int = tid) -> bool:
                return all(i["status"] == "passed" for i in (await a.call("task.stack", {"task_id": t}))["items"])
            ok = await wait_for(found, 40)
            said("  its file turned up", ok)
            if ok and then == "complete":
                await step("  verified complete", a.call("task.verify", {"task_id": tid, "outcome": "complete"}))

    # --- Announcements and to-dos -------------------------------------------------------------------------------------------------------
    print("Announcements and to-dos", flush=True)
    await step("an announcement to everyone", a.call("alerts.create", {"type": "announcement", "audience": "all_users", "title": "Printer moved",
                                                                         "body": "The second-floor printer is now by the kitchen."}))
    await step("one waiting to go out on Friday", a.call("alerts.create", {"type": "routine", "audience": "all_users", "title": "Backups this weekend",
                                                                             "body": "Leave your machine on Friday night; the backup runs from 22:00.",
                                                                             "deliver_at": when(70)}))
    for text, hours in (("Order toner for the second floor", -3), ("Check the new starter's machine", 26), ("Renew the antivirus licences", 120)):
        await step(f"to-do: {text}", a.call("todo.add", {"text": text, "due_at": when(hours)}))

    await asyncio.sleep(5)
    print("\nSeeded. The console shows it now; refresh a page if it was already open.", flush=True)
    if stop_after:
        await d.stop()
        print("The machines are stopped, so they show as offline.")
        return 0
    print("The machines keep running so they show as online. Press Ctrl+C here to stop them.", flush=True)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await d.stop()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main("--stop" in sys.argv[1:])))
    except KeyboardInterrupt:
        sys.exit(0)
