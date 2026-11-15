"""Fill the dev Engine with work in every state, so each page of ADM-01's console has something to show (the user, 10 and 13 Nov 2026).

    environ-engine\\Scripts\\python.exe scripts\\fresh_dev.py           first, with the Engine stopped: a fresh database (it saves the old one)
    environ-engine\\Scripts\\python.exe -m engine                       then the Engine
    environ-operator\\Scripts\\python.exe scripts\\seed_dev.py           seeds, then keeps the machines running (online) until Ctrl+C
    environ-operator\\Scripts\\python.exe scripts\\seed_dev.py --stop    seeds, then stops the machines (they show as offline)

Every seeded machine is a Worker on THIS PC, so nothing the seed runs or sets running may change it: rules and runs use actions that only
look (the rules that would restart, lock or clean up are made switched off). Nothing is written to a table by hand: everything goes through the Engine as the Admins (ADM-01 in `data/admin.json`, and ADM-02 it makes) and as
real Worker processes, the way the console and the machines do it. Detective's cases are played by `scripts/detective_demo.py` on machines that
run no Worker, so what it sends is all they say. Files live under `data/seed/` (git-ignored). It needs the Engine running on the dev database
(`python -m engine`), never the test one. Each step says whether it was made; one that cannot be made does not stop the rest.

What it leaves, by page:
  Machines       3 departments and an empty one; machines on with someone signed in, one that was on and went off, one never connected,
                 Detective's machines, a second Admin's workstation, and a machine knocking for a seat
  Actions        Falcon's own library, three of ADM-01's and one of ADM-02's; runs that worked, failed, ran out of time, were stopped by
                 hand, and one still running
  Automation     on a schedule, every few minutes, on an event, on a threshold, one switched off, one that keeps failing, one by ADM-02,
                 and a skipped run
  Protected      a restricted file and folder with copies caught (one let stay), a private file, a watched folder that changed
  Flows          copying as it happens, only when run, with a step on the way, paused, held at something restricted, a source gone,
                 a destination off, an ask to ADM-02 and one from ADM-02
  Tasks          waiting for your verdict, on track, not started, quiet, late, and completed
  Detective      urgent cases, a case, a noted one, and reviewed ones (explained, dismissed and remembered, accepted)
  Messages       a conversation with a person, one with ADM-02, the group of every Admin, a request to talk open, one accepted
  Announcements  one sent to everyone, one to Finance, one waiting to go out, one taken back
  Calendar       the tasks' deadlines and to-dos: one past its date, two coming, one done
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from live_drill import STATE, Drill, admin_config, connect, wait_for

from common import dotenv

ENGINE_PY = ROOT / "environ-engine" / "Scripts" / "python.exe"
HOME = ROOT / "data" / "seed"

# --- the organisation ------------------------------------------------------------------------------------------------------------------------
DEPARTMENTS = ["Operations", "Finance", "Logistics", "Front desk"]          # Operations is ADM-01's (fresh_dev made it); Front desk stays empty
MACHINES = [  # host, department, the person at it, what it does in the seed
    ("WS-D1", "Operations", "Kojo Asante", "run"),
    ("WS-D2", "Operations", "Ama Owusu", "run"),
    ("WS-D3", "Operations", "Esi Boateng", "run"),
    ("WS-D4", "Operations", "Yaw Mensah", "was_on"),       # on for a while, then off
    ("FIN-01", "Finance", "Akosua Darko", "run"),
    ("FIN-02", "Finance", "Kofi Adjei", "detective"),      # Detective's machines run no Worker: the demo is all they say
    ("FIN-03", "Finance", "Afua Sarpong", "detective"),
    ("FIN-04", "Finance", "Adjoa Boakye", "detective"),
    ("WS-D5", "Operations", "Nana Agyei", "detective"),
    ("WS-D6", "Operations", "Ekow Hammond", "detective"),
    ("LOG-04", "Logistics", "Yaa Asantewaa", "detective"),
    ("LOG-01", "Logistics", "Efua Quaye", "run"),
    ("LOG-02", "Logistics", "Kwame Boadu", "never"),        # registered, never connected
]
SECOND_ADMIN = ("ADM-02", "Finance", "Abena Ofori")
WAITING_MACHINE = "LOG-03"                                  # installed, knocking: it waits for an Admin to give it a seat

FOLDERS = {"WS-D1": ["Documents", "Reports"], "WS-D2": ["Inbox"], "WS-D3": ["Shared", "Archive", "Old"], "WS-D4": ["Documents"],
           "FIN-01": ["Invoices", "Prices", "Inbox"], "LOG-01": ["Deliveries"], "ADM-01": ["Finance", "HR", "Board", "Payroll"]}
FILES = {
    "WS-D1/Documents/notes.txt": "Notes for the week\n",
    "WS-D1/Documents/price-list.csv": "Item,Price\nPaper,4.50\nToner,62.00\n",
    "WS-D1/Reports/sales-october.csv": "Region,Sales\nNorth,1200\nSouth,900\n",
    "WS-D1/Reports/visits-october.csv": "Client,Visits\nAsante,4\nBoateng,2\n",
    "WS-D3/Archive/tender-2025-01.txt": "tender one\n",
    "WS-D3/Archive/tender-2025-02.txt": "tender two\n",
    "WS-D3/Old/forms-2024.txt": "old forms\n",
    "FIN-01/Invoices/invoice-1041.txt": "Invoice 1041\n",
    "LOG-01/Deliveries/route-monday.txt": "Route for Monday\n",
    "ADM-01/Finance/payroll-november.xlsx": "Name,Salary\nAma,4000\nKofi,3800\nEsi,4100\n",
    "ADM-01/Finance/budget-2027.xlsx": "Line,Amount\nStaff,120000\nRent,24000\n",
    "ADM-01/HR/reviews-2026.docx": "Annual reviews 2026\n",
    "ADM-01/Board/minutes-october.docx": "Board minutes, October\n",
    "ADM-01/Board/strategy-2027.pptx": "Strategy 2027\n",
    "ADM-01/Payroll/payslips-october.pdf": "Payslips, October\n",
    "ADM-01/Payroll/bank-details.csv": "Name,Account\nAma,0001\n",
}
TASKS = [  # who, what, file, folder, deadline in hours, what the seed does with it
    ("WS-D1", "Write the weekly sales summary", "summary-week-45.txt", "WS-D1/Documents", 20, "hand_in"),
    ("WS-D1", "Update the price list for December", "price-list-december.csv", "WS-D1/Documents", 30, "complete"),
    ("WS-D2", "Fill in the November stock count", "stock-count-november.csv", "WS-D2/Inbox", 6, "start"),
    ("WS-D3", "Move last year's tender files to the archive", "tenders-moved.txt", "WS-D3/Shared", 72, "leave"),
    ("WS-D2", "Send the delivery schedule for next week", "delivery-schedule.xlsx", "WS-D2/Inbox", 0.15, "start_quiet"),
    ("FIN-01", "Send the October invoices to the auditors", "invoices-october.zip", "FIN-01/Invoices", 0.04, "start"),
    ("WS-D4", "Back up the project files before the move", "backup-done.txt", "WS-D4/Documents", 48, "leave"),
    ("LOG-01", "Plan the routes for the week", "routes-week-46.txt", "LOG-01/Deliveries", 26, "hand_in"),
]
CASES = [  # machine, Detective's scenario, what the Admin answers afterwards (None: left open). One machine each: a machine's later
    # moves join the case already open on it, so two scenarios on one machine make one case
    ("FIN-02", "leak", None),
    ("FIN-03", "printscreens", None),
    ("WS-D4", "ransom", None),
    ("WS-D5", "one_hidden_file", None),
    ("LOG-04", "upload_after_packing", "accepted"),
    ("WS-D6", "wiped", "explained"),
    ("FIN-04", "goes_dark", "dismissed"),
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
    if not dev or dev == test or "test" in dev.rsplit("/", 1)[-1]:
        sys.exit("seed_dev: the Engine's database is not set, or it is a test database; this only seeds the dev database")


class Seed:
    def __init__(self) -> None:
        self.d = Drill()
        self.dept: dict[str, int] = {}
        self.pc: dict[str, int] = {}
        self.acts: dict[str, int] = {}          # action name -> id
        self.a2: Any = None                     # ADM-02's connection

    @property
    def a(self) -> Any:
        return self.d.admin

    async def as_person(self, host: str) -> Any:
        w = self.d.state["workers"][host]
        return await connect({**self.d.engine_cfg, "client_id": w["client_id"], "client_key": w["client_key"]})

    # --- the organisation --------------------------------------------------------------------------------------------------------------------
    async def organisation(self) -> None:
        print("The organisation", flush=True)
        tree = await self.a.call("hierarchy.tree")
        self.dept = {d["name"]: d["department_id"] for d in tree["departments"]}
        for name in DEPARTMENTS:
            if name not in self.dept:
                made = await step(f"department {name}", self.a.call("hierarchy.department_create", {"name": name}))
                if made:
                    self.dept[name] = made["department"]["id"] if "department" in made else made["department_id"]
        cfg = admin_config()
        self.d.state["workers"].setdefault("ADM-01", {"client_id": cfg["client_id"], "client_key": cfg["client_key"]})
        for host, dept, person, _ in MACHINES:
            if host not in self.d.state["workers"]:
                made = await step(f"{host} in {dept}", self.a.call("hierarchy.account_create", {"role": "worker", "hostname": host, "department_id": self.dept[dept]}))
                if made:
                    self.d.state["workers"][host] = {"client_id": made["client_id"], "client_key": made["client_key"], "account_id": made["account_id"],
                                                     "department_id": self.dept[dept]}
            w = self.d.state["workers"].get(host)
            if w:
                await step(f"  the person at {host} is {person}", self.a.call("hierarchy.set_display_name", {"account_id": w["account_id"], "label": person}))
        host, dept, person = SECOND_ADMIN
        if host not in self.d.state["workers"]:
            made = await step(f"a second Admin, {person}, on {host}", self.a.call("hierarchy.account_create", {"role": "admin", "hostname": host, "department_id": self.dept[dept]}))
            if made:
                self.d.state["workers"][host] = {"client_id": made["client_id"], "client_key": made["client_key"], "account_id": made["account_id"],
                                                 "department_id": self.dept[dept]}
        STATE.write_text(__import__("json").dumps(self.d.state, indent=2), encoding="utf-8")
        self.a2 = await self.as_person(host)

    async def waiting_machine(self) -> None:
        from common.connection import EngineConnection

        cfg = self.d.engine_cfg
        c = EngineConnection(cfg["engine_host"], cfg["engine_port"], client_id="", tls=cfg["tls"], ca_cert=cfg.get("ca_cert"))
        try:
            await c.open()
            await step(f"{WAITING_MACHINE}, knocking for a seat", c.call("knock.hello", {"install_token": "seed-dev-" + WAITING_MACHINE + "-install-token",
                                                                                     "hostname": WAITING_MACHINE, "os": "Windows 11 Pro",
                                                                                     "hardware_id": "seed/" + WAITING_MACHINE, "user": "ama"}))
        finally:
            await c.close()

    # --- files and machines --------------------------------------------------------------------------------------------------------------
    def files(self) -> None:
        shutil.rmtree(HOME, ignore_errors=True)
        for machine, names in FOLDERS.items():
            for name in names:
                (HOME / machine / name).mkdir(parents=True, exist_ok=True)
        for rel, text in FILES.items():
            (HOME / rel).write_text(text, encoding="utf-8")

    async def machines(self) -> None:
        print("Starting the machines", flush=True)
        on = [h for h, _, _, what in MACHINES if what in ("run", "was_on")] + ["ADM-01"]
        for host in on:
            self.d.start_worker(host, [HOME / host / n for n in FOLDERS.get(host, [])])
        if not await self.d.online(*on):
            print("  a machine did not come online: see data/drill/<name>/worker.log", flush=True)
        tree = await self.a.call("hierarchy.tree")
        for dep in tree["departments"]:
            for w in dep["workers"] + dep["admins"]:
                self.pc[w["hostname"]] = w["pc_id"]

    async def seen(self, path: Path, seconds: float = 40) -> bool:
        async def there() -> bool:
            tree = await self.a.call("marks.tree")
            return any(Path(f["path"]).resolve() == path.resolve() for f in tree.get("files", []))
        return await wait_for(there, seconds)

    # --- Actions: Admins' own, and runs that end every way --------------------------------------------------------------------------------
    async def actions(self) -> None:
        print("Actions", flush=True)
        lib = (await self.a.call("control.action_list"))["actions"]
        self.acts = {x["name"]: x["id"] for k in lib.values() for x in k}
        said(f"Falcon's own library: {sum(1 for k in lib.values() for x in k if x.get('falcon_key'))} actions")
        own = [
            (self.a, {"kind": "custom", "name": "Check the backup drive", "language": "powershell", "timeout_s": 30, "output_kind": "text",
                      "description": "Whether drive Z: and its Backups folder are there",
                      "script": "if (-not (Test-Path 'Z:\\Backups')) { 'The backup drive Z: is not there'; exit 1 }\n'Backups are on Z:'\n"}),
            (self.a, {"kind": "custom", "name": "Wait for the scanner", "language": "python", "timeout_s": 8, "output_kind": "text",
                      "description": "Waits for the scanner to answer", "script": "import time\ntime.sleep(40)\nprint('the scanner answered')\n"}),
            (self.a, {"kind": "custom", "name": "Copy the install files", "language": "python", "timeout_s": 900, "output_kind": "text",
                      "description": "Copies the installers from the share; slow", "script": "import time\nfor i in range(600):\n    time.sleep(1)\nprint('copied')\n"}),
            (self.a, {"kind": "custom", "name": "Index the shared drive", "language": "python", "timeout_s": 3600, "output_kind": "text",
                      "description": "Lists every file on the shared drive; takes long", "script": "import time\ntime.sleep(3000)\nprint('done')\n"}),
            (self.a2, {"kind": "custom", "name": "Count the files in Finance", "language": "python", "timeout_s": 60, "output_kind": "list",
                       "description": "How many files each Finance folder holds",
                       "script": "import os\nroot = os.path.expanduser('~')\nfor name in sorted(os.listdir(root))[:12]:\n"
                                 "    p = os.path.join(root, name)\n    if os.path.isdir(p):\n        try:\n            print(f'{name}\\t{len(os.listdir(p))} files')\n"
                                 "        except OSError:\n            pass\n"}),
        ]
        for who, body in own:
            made = await step(f"{body['name']} ({'ADM-02' if who is self.a2 else 'ADM-01'})", who.call("control.action_create", body))
            if made:
                self.acts[body["name"]] = made["action"]["id"]

    async def runs(self) -> None:
        print("Runs by hand", flush=True)

        async def run(name: str, host: str) -> int | None:
            if name not in self.acts or host not in self.pc:
                said(f"ran {name} on {host}", False, "not there")
                return None
            got = await step(f"ran {name} on {host}", self.a.call("control.action_run", {"action_id": self.acts[name], "pc_id": self.pc[host]}))
            return got.get("execution_id") if got else None
        for name, host in (("Free disk space", "WS-D1"), ("Free disk space", "WS-D2"), ("Who is signed in", "FIN-01"), ("Windows version", "LOG-01"),
                           ("Check CPU, memory and disk", "WS-D3"), ("List running programs", "WS-D1"), ("Take a screenshot", "WS-D2"),
                           ("Check the backup drive", "WS-D3"), ("Wait for the scanner", "WS-D2"), ("Does it need a restart", "FIN-01"),
                           ("Index the shared drive", "WS-D1")):
            await run(name, host)
        stop = await run("Copy the install files", "FIN-01")
        if stop:
            await asyncio.sleep(4)
            await step("  stopped it by hand", self.a.call("control.terminate_run", {"execution_ids": [stop]}))

    # --- Automation ----------------------------------------------------------------------------------------------------------------------
    async def automation(self) -> None:
        print("Automation", flush=True)
        A = self.acts
        rules = [
            (self.a, "Disk check every weekday morning", {"type": "time.recurring", "match": {"at": "08:00", "days": [0, 1, 2, 3, 4]}}, ["Free disk space"]),
            (self.a, "How hard they work, every 2 minutes", {"type": "time.recurring", "match": {"interval_s": 120}, "pc_ids": ["WS-D1", "WS-D2"]},
             ["Check CPU, memory and disk"]),
            (self.a, "The backup drive, every 3 minutes", {"type": "time.recurring", "match": {"interval_s": 180}, "pc_ids": ["WS-D3"]}, ["Check the backup drive"]),
            (self.a, "A USB drive goes in", {"type": "usb.inserted"}, ["What is on its USB drives", "Tell them IT is on the way"]),
            (self.a, "New files in Ama's Inbox", {"type": "file.created", "match": {"path_prefix": str(HOME / "WS-D2" / "Inbox")}, "pc_ids": ["WS-D2"]},
             ["List running programs"]),
            (self.a, "CPU over 90% for 5 minutes", {"type": "threshold.cpu", "match": {"percent": 90, "duration_s": 300}}, ["List running programs"]),
            # only actions that look: every seeded machine is this PC, so a rule that changes something would change it here
            (self.a, "Low disk space", {"type": "threshold.disk", "match": {"percent": 90}}, ["Free disk space"]),
            (self.a, "Friday evening restart", {"type": "time.recurring", "match": {"at": "18:00", "days": [4]}, "enabled": False}, ["Restart in 5 minutes"]),
            (self.a, "A restricted copy turns up", {"type": "resource.violation", "enabled": False}, ["Lock the screen for 5 minutes"]),
            (self.a2, "Sign-in outside office hours", {"type": "user.login", "match": {"outside_hours": True}}, ["Take a screenshot"]),
        ]
        made_ids = {}
        for who, name, spec, names in rules:
            body = {"name": name, "type": spec["type"], "match": spec.get("match") or {}, "action_ids": [A[n] for n in names if n in A],
                    "pc_ids": [self.pc[h] for h in spec.get("pc_ids", []) if h in self.pc] or None}
            if spec.get("enabled") is False:
                body["enabled"] = False
            got = await step(f"{name}" + (" (switched off)" if spec.get("enabled") is False else "") + (" (ADM-02)" if who is self.a2 else ""),
                             who.call("control.event_create", body))
            if got:
                made_ids[name] = got["event"]["id"]
        board = await self.a.call("automation.board")
        nxt = next((c for c in board.get("coming_up", []) if c.get("event_id") == made_ids.get("Disk check every weekday morning")), None)
        if nxt:
            await step("  its next run skipped by hand", self.a.call("automation.skip", {"event_id": nxt["event_id"], "at": nxt["at"]}))

    # --- Protected files ----------------------------------------------------------------------------------------------------------------
    async def protected(self) -> None:
        print("Protected files", flush=True)
        files = HOME / "ADM-01"
        await self.seen(files / "Board" / "strategy-2027.pptx")
        w1 = self.d.state["workers"]["WS-D1"]
        payroll = files / "Finance" / "payroll-november.xlsx"
        await step("payroll-november.xlsx, restricted to its place", self.a.call("marks.create", {"paths": [str(payroll)], "protection": "restricted", "keep": "path"}))
        await step("budget-2027.xlsx, restricted to this machine", self.a.call("marks.create", {"paths": [str(files / "Finance" / "budget-2027.xlsx")],
                                                                                              "protection": "restricted", "keep": "machine"}))
        await step("the Payroll folder, restricted", self.a.call("marks.create", {"paths": [str(files / "Payroll")], "protection": "restricted", "keep": "machine"}))
        await step("reviews-2026.docx, private to Kojo Asante", self.a.call("marks.create", {"paths": [str(files / "HR" / "reviews-2026.docx")], "protection": "private",
                                                                                           "keep": "machine", "readers": [w1["account_id"]], "allow_system": True}))
        await step("the Board folder, watched", self.a.call("marks.create", {"paths": [str(files / "Board")], "protection": "watch", "keep": "machine"}))
        await asyncio.sleep(2)
        (files / "Board" / "minutes-october.docx").write_text("Board minutes, October (corrected)\n", encoding="utf-8")
        (files / "Board" / "agenda-november.docx").write_text("Agenda, November\n", encoding="utf-8")
        shutil.copyfile(payroll, HOME / "WS-D2" / "Inbox" / "payroll-november.xlsx")                     # a copy in the same department
        shutil.copyfile(files / "Finance" / "budget-2027.xlsx", HOME / "FIN-01" / "Inbox" / "budget-2027.xlsx")   # and one that left it
        shutil.copyfile(files / "Payroll" / "bank-details.csv", HOME / "LOG-01" / "Deliveries" / "bank-details.csv")
        said("a change in the watched folder, and copies of restricted files on WS-D2, FIN-01 and LOG-01")

        async def caught() -> bool:
            got = await self.a.call("issues.list", {"type": "file"})
            return len(got.get("issues", [])) >= 2
        await wait_for(caught, 40)
        for it in (await self.a.call("issues.list", {"type": "file"})).get("issues", []):
            if it.get("host") == "LOG-01":
                full = await self.a.call("issues.get", {"issue_id": it["id"]})
                stay = next((o for o in full.get("options", []) if o.get("key") == "allow"), None)
                if stay:
                    await step("  the copy on LOG-01 let stay", self.a.call("issues.act", {"issue_id": it["id"], "key": stay["key"],
                                                                                          "reason": "Logistics pays the drivers; agreed with Finance"}))
                break

    # --- Flows ---------------------------------------------------------------------------------------------------------------------------
    async def flows(self) -> None:
        print("Flows", flush=True)
        pc, a = self.pc, self.a

        def flow(name: str, src: str, folder: str, dst: str, dfolder: str, **extra: Any) -> dict[str, Any]:
            return {"name": name, "source_pc_id": pc[src], "source_path": str(HOME / src / folder), "stages": extra.pop("stages", []), "confirm_collisions": True,
                    "destinations": [{"destination_pc_id": pc[dst], "destination_path": str(HOME / dst / dfolder)}], **extra}
        await step("reports-to-inbox, copying as it happens", a.call("flow.create", flow("reports-to-inbox", "WS-D1", "Reports", "WS-D2", "Inbox")))
        manual = await step("documents-to-shared, only when it is run", a.call("flow.create", flow("documents-to-shared", "WS-D1", "Documents", "WS-D3", "Shared", run_mode="manual")))
        if manual:
            await step("  run once", a.call("flow.run", {"flow_id": manual["flow"]["id"]}))
        await step("prices-dated, with a step on the way", a.call("flow.create", flow("prices-dated", "WS-D1", "Documents", "FIN-01", "Prices",
                                                                                        stages=[{"step": {"kind": "renaming", "op": "add_date"}}])))
        held = await step("archive-back, paused", a.call("flow.create", flow("archive-back", "WS-D3", "Archive", "WS-D1", "Documents")))
        if held:
            await step("  paused", a.call("flow.pause", {"flow_id": held["flow"]["id"]}))
        await step("finance-to-shared, held at something restricted", a.call("flow.create", flow("finance-to-shared", "ADM-01", "Finance", "WS-D3", "Shared")))
        await step("old-forms, whose source goes away", a.call("flow.create", flow("old-forms", "WS-D3", "Old", "WS-D1", "Documents")))
        await step("documents-to-yaw, to a machine that goes off", a.call("flow.create", flow("documents-to-yaw", "WS-D1", "Documents", "WS-D4", "Documents")))
        await step("deliveries-to-finance, asking ADM-02 for a folder", a.call("flow.create", {
            "name": "deliveries-to-finance", "source_pc_id": pc["LOG-01"], "source_path": str(HOME / "LOG-01" / "Deliveries"), "stages": [], "confirm_collisions": True,
            "destinations": [{"destination_pc_id": pc["ADM-02"], "destination_path": "", "let_them_choose": True, "note": "Delivery notes for the month-end"}]}))
        await step("invoices-to-you, ADM-02 asking ADM-01", self.a2.call("flow.create", {
            "name": "invoices-to-you", "source_pc_id": pc["FIN-01"], "source_path": str(HOME / "FIN-01" / "Invoices"), "stages": [], "confirm_collisions": True,
            "destinations": [{"destination_pc_id": pc["ADM-01"], "destination_path": "", "let_them_choose": True, "note": "Invoices for the audit"}]}))
        await asyncio.sleep(6)
        shutil.rmtree(HOME / "WS-D3" / "Old", ignore_errors=True)
        (HOME / "WS-D1" / "Reports" / "sales-november.csv").write_text("Region,Sales\nNorth,1300\nSouth,950\n", encoding="utf-8")
        said("WS-D3's Old folder taken away, and a new report on WS-D1")

    # --- Tasks ---------------------------------------------------------------------------------------------------------------------------
    async def tasks(self) -> None:
        print("Tasks", flush=True)
        for who, what, name, folder, hours, then in TASKS:
            w = self.d.state["workers"][who]
            made = await step(what, self.a.call("task.create", {
                "assignee_account_id": w["account_id"], "description": f"{what}: {name}", "verification_mode": "stack",
                "items": [{"target_type": "file", "intent": "create", "name": name, "path": str(HOME / folder)}],
                "soft_deadline_at": when(hours * 0.7) if hours > 1 else None, "final_deadline_at": when(hours)}))
            if not made or then == "leave":
                continue
            tid = made["task"]["id"]
            person = await self.as_person(who)
            try:
                await step("  started by them", person.call("task.start", {"task_id": tid}))
            finally:
                await person.close()
            if then in ("hand_in", "complete"):
                (HOME / folder / name).write_text(f"{what}\n", encoding="utf-8")

                async def found(t: int = tid) -> bool:
                    return all(i["status"] == "passed" for i in (await self.a.call("task.stack", {"task_id": t}))["items"])
                ok = await wait_for(found, 40)
                said("  its file turned up", ok)
                if ok and then == "complete":
                    await step("  verified complete", self.a.call("task.verify", {"task_id": tid, "outcome": "complete"}))

    # --- Detective -----------------------------------------------------------------------------------------------------------------------
    async def detective(self) -> None:
        print("Detective", flush=True)
        cfg = self.d.engine_cfg
        for host, scenario, answer in CASES:
            w = self.d.state["workers"].get(host)
            if not w:
                continue
            args = [str(ENGINE_PY), str(ROOT / "scripts" / "detective_demo.py"), "--engine", f"{cfg['engine_host']}:{cfg['engine_port']}",
                    "--client-id", w["client_id"], "--client-key", w["client_key"], "--scenario", scenario, "--speed", "120", "--yes"]
            args += ["--ca", cfg["ca_cert"]] if cfg.get("tls") else ["--plaintext"]
            got = await asyncio.to_thread(subprocess.run, args, cwd=ROOT, capture_output=True, text=True, timeout=240)
            said(f"{scenario} played on {host}", got.returncode == 0, got.stderr.strip().splitlines()[-1][:140] if got.returncode and got.stderr.strip() else "")
            if answer is None:
                continue

            async def new(host: str = host) -> list[dict[str, Any]]:
                return [c for c in (await self.a.call("detective.cases", {"include_noted": True}))["cases"] if c["host"] == host]
            await wait_for(lambda: _nonempty(new()), 30)
            for c in await new():
                body = {"case_id": c["id"], "outcome": answer, "note": {"explained": "Esi cleared out last year's files; she told us first.",
                                                                       "accepted": "Seen it; Kofi has been spoken to.",
                                                                       "dismissed": "The snipping tool is part of her job."}[answer]}
                if answer == "dismissed":
                    body["remember"] = {"kind": "program"}
                await step(f"  answered: {answer}", self.a.call("detective.review", body))
                break

    # --- Messages, announcements, to-dos -------------------------------------------------------------------------------------------------
    async def messages(self) -> None:
        print("Messages", flush=True)
        a, w1 = self.a, self.d.state["workers"]["WS-D1"]
        convo = await step("a conversation with Kojo Asante", a.call("chat.open", {"account_id": w1["account_id"]}))
        if convo:
            cid = convo["conversation"]["conversation_id"] if "conversation" in convo else convo["conversation_id"]
            await step("  a message to him", a.call("chat.send", {"conversation_id": cid, "body": "Morning. Is the October sales report in the Reports folder yet?"}))
            person = await self.as_person("WS-D1")
            try:
                await step("  his answer", person.call("chat.send", {"conversation_id": cid, "body": "Yes, sales-october.csv is there. Visits too."}))
            finally:
                await person.close()
        me = (await a.call("hierarchy.tree"))["viewer"]["account_id"]
        pair = await step("ADM-02 writes to ADM-01", self.a2.call("chat.open", {"account_id": me}))
        if pair:
            cid = pair["conversation"]["conversation_id"] if "conversation" in pair else pair["conversation_id"]
            await step("  about the invoices flow", self.a2.call("chat.send", {"conversation_id": cid, "body": "I've asked you for a folder for the audit invoices. Any of yours is fine."}))
        group = await step("the group of every Admin", self.a2.call("chat.open", {"admins": True}))
        if group:
            cid = group["conversation"]["conversation_id"] if "conversation" in group else group["conversation_id"]
            await step("  a message to every Admin", self.a2.call("chat.send", {"conversation_id": cid, "body": "Reminder: the Friday restarts are off until the move is done."}))
        for host, line, then in (("WS-D2", "The stock count sheet will not open on my machine", None),
                                 ("FIN-01", "Can someone look at the printer on the second floor?", "accept"),
                                 ("LOG-01", "My second screen is flickering", None)):
            person = await self.as_person(host)
            try:
                await step(f"a request to talk from {host}", person.call("chat.ask", {"line": line}))
            finally:
                await person.close()
            if then == "accept":
                req = next((r for r in (await a.call("chat.requests")).get("requests", []) if r.get("line") == line), None)
                if req:
                    await step("  accepted", a.call("chat.request_accept", {"request_id": req.get("request_id") or req.get("id")}))

    async def announcements_and_todos(self) -> None:
        print("Announcements and to-dos", flush=True)
        a = self.a
        await step("an announcement to everyone", a.call("alerts.create", {"type": "announcement", "audience": "all_users", "title": "Printer moved",
                                                                             "body": "The second-floor printer is now by the kitchen."}))
        await step("one to Finance", a.call("alerts.create", {"type": "announcement", "audience": "department", "department_id": self.dept["Finance"],
                                                               "title": "Month-end", "body": "Please have the invoices in by Thursday."}))
        await step("one waiting to go out on Friday", a.call("alerts.create", {"type": "routine", "audience": "all_users", "title": "Backups this weekend",
                                                                                 "body": "Leave your machine on Friday night; the backup runs from 22:00.",
                                                                                 "deliver_at": when(70)}))
        took = await step("one to be taken back", a.call("alerts.create", {"type": "routine", "audience": "all_users", "title": "Office closed Monday",
                                                                             "body": "The office is closed on Monday.", "deliver_at": when(40)}))
        if took:
            aid = (took.get("alert") or {}).get("id") or took.get("alert_id") or took.get("id")
            if aid:
                await step("  taken back", a.call("alerts.cancel", {"alert_id": aid}))
        done = None
        for text, hours in (("Order toner for the second floor", -3), ("Check the new starter's machine", 26), ("Renew the antivirus licences", 120),
                            ("Label the new laptops", -20)):
            got = await step(f"to-do: {text}", a.call("todo.add", {"text": text, "due_at": when(hours)}))
            if text == "Label the new laptops":
                done = got
        if done:
            tid = (done.get("todo") or {}).get("id") or done.get("todo_id") or done.get("id")
            if tid:
                await step("  done", a.call("todo.done", {"todo_id": tid}))

    async def was_on(self) -> None:
        for host, _, _, what in MACHINES:
            if what == "was_on":
                self.d.stop_worker(host)
                said(f"{host} switched off")


async def _nonempty(coro: Any) -> bool:
    return bool(await coro)


async def main(stop_after: bool) -> int:
    refuse_test_database()
    s = Seed()
    await s.d.start()
    if s.d.state["workers"]:
        print("data/drill/state.json already names machines: run scripts/fresh_dev.py first for a fresh start; adding to what is there", flush=True)
    await s.organisation()
    await s.waiting_machine()
    s.files()
    await s.machines()
    await s.actions()
    await s.automation()
    await s.protected()
    await s.flows()
    await s.tasks()
    await s.runs()
    await s.was_on()
    await s.detective()
    await s.messages()
    await s.announcements_and_todos()
    if s.a2 is not None:
        await s.a2.close()
    await asyncio.sleep(5)
    print("\nSeeded. The console shows it now; refresh a page if it was already open.", flush=True)
    if stop_after:
        await s.d.stop()
        print("The machines are stopped, so they show as offline.")
        return 0
    print("The machines keep running so they show as online. Press Ctrl+C here to stop them.", flush=True)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await s.d.stop()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main("--stop" in sys.argv[1:])))
    except KeyboardInterrupt:
        sys.exit(0)
