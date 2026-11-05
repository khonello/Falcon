"""The hands-on scenarios' machines: real Workers on this PC, each with its own folders, running until you press Ctrl+C. The steps are `docs/HANDS-ON-SCENARIOS.md`.

    environ-operator\\Scripts\\python.exe scripts\\hands_on.py          (from an elevated prompt, with the Engine running)
    environ-operator\\Scripts\\python.exe scripts\\hands_on.py wipe     a program deletes the old contracts (a person's own deleting counts for less)
    environ-operator\\Scripts\\python.exe scripts\\hands_on.py refill   puts them back, to go again

Three "machines" run here at once, as they would on three PCs: a person's (WS-D1), a second person's (WS-D2) and the Admin's workstation (ADM-01). It uses the Admin in
`data/admin.json` and the Workers `scripts/live_drill.py` made. Everything is under `data/hands-on/`, which is git-ignored and made fresh each time: nothing else is touched.
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from live_drill import Drill

HOME = ROOT / "data" / "hands-on"
FOLDERS = {"WS-D1": ["Documents", "Elsewhere", "Outbox"], "WS-D2": ["Inbox"], "ADM-01": ["Restricted", "Other"]}
FILES = {"WS-D1/Documents/sales.txt": "Region,Sales\nNorth,1200\nSouth,900\n",
         "WS-D1/Documents/notes.txt": "Notes for the week\n",
         "ADM-01/Restricted/payroll.txt": "Name,Salary\nAma,4000\nKofi,3800\n"}
OLD_DOCUMENTS = 60
OLD = HOME / "WS-D1" / "Documents" / "Old"


def refill() -> None:
    OLD.mkdir(exist_ok=True)
    for i in range(OLD_DOCUMENTS):
        (OLD / f"contract-{i:02d}.docx").write_text(f"contract {i}\n", encoding="utf-8")


def wipe() -> None:
    for p in OLD.glob("*.docx"):
        p.unlink()


async def main() -> int:
    if HOME.exists():
        shutil.rmtree(HOME)
    d = Drill()
    await d.start()
    for m in (await d.admin.call("marks.list", {"scope": "mine"}))["marks"]:      # a fresh start: an earlier go's marks and flows would answer for this one
        await d.admin.call("marks.unmark", {"mark_id": m["id"]})
    for f in (await d.admin.call("flow.list"))["flows"]:
        if "hands-on" in str(f.get("source_path") or ""):
            await d.admin.call("flow.delete", {"flow_id": f["id"]})
    for machine, names in FOLDERS.items():
        for name in names:
            (HOME / machine / name).mkdir(parents=True)
    for rel, text in FILES.items():
        (HOME / rel).write_text(text, encoding="utf-8")
    refill()
    for name in ("WS-D1", "WS-D2"):
        await d.worker_account(name)
    for machine, names in FOLDERS.items():
        d.start_worker(machine, [HOME / machine / n for n in names], drives=machine == "WS-D1")      # three machines on one PC: one of them answers for the real drives
    ready = await d.online("WS-D1", "WS-D2")
    await asyncio.sleep(10)                                                       # the machines tell what this rebuild looked like: to Detective, a mass deletion
    for c in (await d.admin.call("detective.cases", {"include_noted": True}))["cases"]:
        if c["status"] == "open":
            await d.admin.call("detective.review", {"case_id": c["id"], "outcome": "dismissed", "note": "Cleared before a hands-on test"})
    print("\nThe machines are running." if ready else "\nA machine did not come online: see data/drill/<name>/worker.log.")
    for name in ("WS-D1", "WS-D2"):
        print(f"  {name}  account {d.state['workers'][name]['account_id']}  machine {await d.pc_id(name)}  {HOME / name}")
    print(f"  ADM-01  machine {await d.pc_id('ADM-01')}  {HOME / 'ADM-01'}")
    print("\nFollow docs/HANDS-ON-SCENARIOS.md. Press Ctrl+C here when you are done.", flush=True)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await d.stop()
    return 0


if __name__ == "__main__":
    if sys.argv[1:] in (["wipe"], ["refill"]):
        {"wipe": wipe, "refill": refill}[sys.argv[1]]()
        print(f"{sys.argv[1]}: done, {len(list(OLD.glob('*.docx')))} contracts in {OLD}")
        sys.exit(0)
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
