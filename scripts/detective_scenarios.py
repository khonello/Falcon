"""Scripted scenarios for Detective: what people do, as the signals a machine would send, and what the detector should make of it.

    environ-engine\\Scripts\\python.exe scripts\\detective_scenarios.py [name ...]      # play them and print what Detective saw, as it saw it

Each scenario is a list of `Sig`s on one machine (pc 7, "FIN-07") plus the Context the Engine would supply. The tests (tests/test_detective.py) assert what
should come out; this prints it as a story, which is also how a case reads on the Detective page. Malicious AND benign ones live here on purpose: the point
is that the same moves with a different context stay quiet.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.detective import Context, Detective, Sig, Update

PC = 7
R = frozenset({"restricted"})
DAY = 86400.0


def clock(day: int = 14, hour: int = 18, minute: int = 41) -> float:
    return time.mktime((2026, 10, day, hour, minute, 0, 0, 0, -1))


@dataclass
class Scenario:
    name: str
    says: str
    sigs: list[Sig]
    ctx: Context = field(default_factory=Context)


class Script:
    """Builds a scenario by walking forward in time."""

    def __init__(self, t0: float) -> None:
        self.t, self.out = t0, []

    def after(self, seconds: float) -> Script:
        self.t += seconds
        return self

    def add(self, verb: str, path: str = "", **kw) -> Script:
        self.out.append(Sig(self.t, kw.pop("pc", PC), verb, path, **kw))
        return self


def leak() -> Scenario:
    s = Script(clock())
    p = r"C:\Finance\Payroll"
    s.add("opened", rf"{p}\payroll-q3.xlsx", thing="h-q3", by="hand", program="excel.exe", tags=R)
    s.after(180).add("moved", r"C:\Windows\Temp\notes.txt.dll", old=rf"{p}\payroll-q3.xlsx", thing="h-q3", by="started", program="powershell.exe", tags=R)
    s.after(5).add("hid", r"C:\Windows\Temp\notes.txt.dll", thing="h-q3", by="started", program="powershell.exe", tags=R)
    for i in range(14):
        s.after(4).add("copied", rf"C:\Users\kojo\Staging\payroll-{i:02d}.xlsx", old=rf"{p}\payroll-{i:02d}.xlsx", thing=f"h-p{i}", by="started", program="powershell.exe", tags=R)
    s.after(20).add("created", r"C:\Users\kojo\Staging\q3.zip", thing="h-zip", by="started", program="powershell.exe")
    s.after(90).add("attached", "E:\\", device="E:\\", by="alone")
    s.after(25).add("copied", r"E:\q3.zip", old=r"C:\Users\kojo\Staging\q3.zip", thing="h-zip", by="started", program="powershell.exe")
    s.after(60).add("deleted", r"C:\Users\kojo\Staging\q3.zip", thing="h-zip", by="started", program="powershell.exe")
    s.after(8).add("cleared", info={"what": "the list of recent files"}, by="started", program="powershell.exe")
    return Scenario("leak", "A Finance worker hides a payroll file, packs fourteen payroll files, plugs in a new drive, copies the archive and erases the trail.", s.out)


def backup_twin() -> Scenario:
    s = Script(clock(15, 2, 0))
    for i in range(14):
        s.after(2).add("copied", rf"D:\Staging\payroll-{i:02d}.xlsx", old=rf"C:\Finance\Payroll\payroll-{i:02d}.xlsx", thing=f"h-p{i}", by="alone", program="robocopy.exe", tags=R)
    s.after(10).add("created", r"D:\Staging\nightly.zip", thing="h-night", by="alone", program="veeam.exe")
    s.after(30).add("attached", "E:\\", device="E:\\", by="alone")
    s.after(20).add("copied", r"E:\nightly.zip", old=r"D:\Staging\nightly.zip", thing="h-night", by="alone", program="robocopy.exe")
    s.after(60).add("deleted", r"D:\Staging\nightly.zip", thing="h-night", by="alone", program="veeam.exe")
    ctx = Context(known_device=lambda pc, dev: 40)
    return Scenario("backup_twin", "The same moves as the leak, at 02:00, by the backup program, to a drive this machine has used forty times, with nothing hidden.", s.out, ctx)


def patient() -> Scenario:
    s = Script(clock(12, 10, 5))
    s.add("hid", r"C:\Users\kojo\Documents\salaries-notes.xlsx", thing="h-notes", by="hand", program="explorer.exe")
    s.after(2 * DAY).add("moved", r"C:\ProgramData\cache\ledger.xlsx", old=r"C:\Users\kojo\Documents\ledger.xlsx", thing="h-ledger", by="hand", program="explorer.exe")
    s.after(2 * DAY).add("attached", "F:\\", device="F:\\", by="alone")
    s.after(30).add("copied", r"F:\salaries-notes.xlsx", old=r"C:\Users\kojo\Documents\salaries-notes.xlsx", thing="h-notes", by="hand", program="explorer.exe")
    return Scenario("patient", "Three small things over four days, none enough alone; the same file ties them together on the last one.", s.out)


def one_hidden_file() -> Scenario:
    s = Script(clock(13, 11, 0))
    s.add("hid", r"C:\Users\ama\Documents\birthday-plans.docx", thing="h-bd", by="hand", program="explorer.exe")
    return Scenario("one_hidden_file", "A person hides a personal document in their own folder.", s.out)


def flow_to_drive() -> Scenario:
    s = Script(clock(13, 15, 0))
    s.add("attached", "E:\\", device="E:\\", by="alone")
    for i in range(20):
        s.after(3).add("copied", rf"E:\reports\r{i}.xlsx", old=rf"C:\Finance\r{i}.xlsx", thing=f"h-r{i}", by="falcon", tags=R)
    return Scenario("flow_to_drive", "Falcon's own flow copies reports to a drive: not behaviour at all.", s.out)


def covered_by_task() -> Scenario:
    s = Script(clock(13, 9, 0))
    s.add("attached", "E:\\", device="E:\\", by="alone")
    s.after(20).add("copied", r"E:\board-pack.zip", old=r"C:\Users\kojo\board-pack.zip", thing="h-board", by="hand", program="explorer.exe", tags=R)
    ctx = Context(task_things=lambda pc: {"h-board"})
    return Scenario("covered_by_task", "A restricted archive goes to a drive, and a task assigned to this person asks for exactly that.", s.out, ctx)


def snooping() -> Scenario:
    s = Script(clock(13, 14, 0))
    for i in range(20):
        s.after(20).add("opened", rf"\\hr\files\dept{i % 4}\doc{i}.docx", thing=f"h-o{i}", by="hand", program="winword.exe", tags=frozenset({"outside_role"}))
    return Scenario("snooping", "A worker opens twenty files across four folders that are not part of their work, in seven minutes.", s.out)


def screenshots() -> Scenario:
    s = Script(clock(13, 16, 0))
    s.add("opened", r"C:\Finance\Payroll\payroll-q3.xlsx", thing="h-q3", by="hand", program="excel.exe", tags=R)
    s.after(40).add("launched", program="snippingtool.exe", by="hand")
    s.after(300).add("launched", program="snippingtool.exe", by="hand")
    return Scenario("screenshots", "A worker has a restricted payroll sheet open and starts the snipping tool, twice, five minutes apart.", s.out)


def printscreens() -> Scenario:
    s = Script(clock(13, 16, 30))
    s.add("opened", r"C:\Finance\Payroll\payroll-q3.xlsx", thing="h-q3", by="hand", program="excel.exe", tags=R)
    for _ in range(4):
        s.after(25).add("captured", by="hand", program="excel.exe", info={"kind": "screen"})
    return Scenario("printscreens", "A worker has a restricted payroll sheet open and presses PrintScreen four times in two minutes: no screenshot tool at all.", s.out)


def printscreen_of_nothing() -> Scenario:
    s = Script(clock(13, 16, 30))
    s.add("captured", by="hand", program="chrome.exe", info={"kind": "region"})
    return Scenario("printscreen_of_nothing", "A picture is put on the clipboard on a machine where nothing restricted is being worked on.", s.out)


def upload_after_packing() -> Scenario:
    s = Script(clock(13, 20, 0))
    for i in range(10):
        s.after(5).add("opened", rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"h-p{i}", by="hand", program="excel.exe", tags=R)
    s.after(30).add("created", r"C:\Users\kojo\Staging\q3.zip", thing="h-zip", by="started", program="7z.exe")
    s.after(60).add("uploaded", program="python.exe", by="unknown", info={"bytes": 180_000_000, "to": "203.0.113.9", "destinations": 1, "seconds": 60})
    return Scenario("upload_after_packing", "A restricted payroll set is opened, packed into an archive, and a script then sends 180 MB out to one address.", s.out)


def sync_client_upload() -> Scenario:
    s = Script(clock(13, 11, 0))
    s.add("uploaded", program="onedrive.exe", by="unknown", info={"bytes": 300_000_000, "to": "13.107.42.12", "destinations": 3, "seconds": 60})
    return Scenario("sync_client_upload", "The company's sync client sends 300 MB out in a minute, as it does.", s.out)


def zip_one_file_then_upload() -> Scenario:
    s = Script(clock(13, 19, 0))
    s.add("copied", r"C:\Users\kojo\Desktop\customers-master.xlsx", old=r"C:\Finance\Sales\customers-master.xlsx", thing="h-cm", by="hand", program="explorer.exe", tags=R)
    s.after(40).add("created", r"C:\Users\kojo\Desktop\invoice.zip", thing="h-inv", by="started", program="7z.exe")
    s.after(120).add("uploaded", program="chrome.exe", by="unknown", info={"bytes": 12_000_000, "to": "198.51.100.7", "destinations": 1, "seconds": 60})
    return Scenario("zip_one_file_then_upload", "One restricted file is copied to the desktop, packed into a zip called invoice.zip, and 12 MB goes out through the browser.", s.out)


def convert_then_drive() -> Scenario:
    s = Script(clock(13, 17, 0))
    s.add("attached", "E:\\", device="E:\\", by="alone")
    s.after(30).add("created", r"C:\Users\ama\Documents\board-minutes.pdf", thing="h-pdf", by="hand", program="winword.exe", tags=R)
    s.add("modified", r"C:\Users\ama\Documents\board-minutes.docx", thing="h-docx", by="hand", program="winword.exe", tags=R)
    s.after(25).add("copied", r"E:\board-minutes.pdf", old=r"C:\Users\ama\Documents\board-minutes.pdf", thing="h-pdf", by="hand", program="explorer.exe", tags=R)
    return Scenario("convert_then_drive", "A restricted document is saved as a PDF and the PDF goes on a drive that was just plugged in.", s.out)


def one_file_to_a_share() -> Scenario:
    s = Script(clock(13, 15, 0))
    s.add("copied", r"\\fileserver\public\salary-bands.xlsx", old=r"C:\HR\salary-bands.xlsx", thing="h-sb", by="hand", program="explorer.exe", tags=R)
    return Scenario("one_file_to_a_share", "One restricted file is copied to a public share on the network.", s.out)


def sole_copy_deleted() -> Scenario:
    s = Script(clock(13, 16, 45))
    s.add("deleted", r"C:\Legal\contract-amendment-7.docx", thing="h-ca", by="hand", program="explorer.exe", tags=frozenset({"restricted", "only_copy"}))
    return Scenario("sole_copy_deleted", "One deletion: the only copy of a restricted contract amendment.", s.out)


def ordinary_delete() -> Scenario:
    s = Script(clock(13, 16, 45))
    s.add("deleted", r"C:\Users\ama\Documents\notes-old.txt", thing="h-no", by="hand", program="explorer.exe", tags=frozenset({"only_copy"}))
    return Scenario("ordinary_delete", "One deletion of an ordinary old note that nothing else says matters.", s.out)


def lock_out() -> Scenario:
    s = Script(clock(13, 14, 30))
    s.add("permissions", r"C:\Shared\Projects\plan.xlsx", thing="h-pl", by="hand", program="explorer.exe")
    return Scenario("lock_out", "Who may open a shared project file is changed by hand.", s.out)


def backups_then_files() -> Scenario:
    s = Script(clock(13, 23, 0))
    for i in range(2):
        s.after(5).add("deleted", rf"D:\Backups\nightly-{i}.vhdx", thing=f"h-b{i}", by="hand", program="explorer.exe")
    for i in range(4):
        s.after(5).add("deleted", rf"C:\Shared\Projects\plan{i}.xlsx", thing=f"h-p{i}", by="hand", program="explorer.exe", tags=R)
    return Scenario("backups_then_files", "Two backup images are deleted, then four restricted project files.", s.out)


def weekly_collector() -> Scenario:
    s = Script(clock(1, 10, 0))
    for week in range(3):
        s.t = clock(1 + week * 7, 10, 0)
        s.add("copied", rf"C:\Users\kojo\Misc\r{week}.xlsx", old=rf"C:\Finance\Payroll\r{week}.xlsx", thing=f"h-w{week}", by="hand", program="explorer.exe", tags=R)
    s.t = clock(22, 21, 0)
    s.add("attached", "E:\\", device="E:\\", by="alone")
    s.after(20).add("created", r"C:\Users\kojo\Misc\misc.zip", thing="h-misc", by="started", program="7z.exe")
    s.after(30).add("copied", r"E:\misc.zip", old=r"C:\Users\kojo\Misc\misc.zip", thing="h-misc", by="hand", program="explorer.exe")
    return Scenario("weekly_collector", "One restricted file a week for three weeks into a folder called Misc; on day 22 the folder is zipped and the zip goes to a drive.", s.out)


def one_look_at_the_director() -> Scenario:
    s = Script(clock(13, 15, 30))
    s.add("opened", r"\\hr\files\director\pay-review.docx", thing="h-dr", by="hand", program="winword.exe", tags=frozenset({"outside_role", "restricted"}))
    return Scenario("one_look_at_the_director", "A worker opens one restricted file in the director's folder, which is not part of their work.", s.out)


def ordinary_day() -> Scenario:
    s = Script(clock(13, 11, 0))
    s.add("renamed", r"C:\Users\ama\Documents\notes.md", old=r"C:\Users\ama\Documents\notes.txt", thing="h-n", by="hand", program="explorer.exe")
    s.after(60).add("copied", r"C:\Users\ama\Documents\Project\spec.docx", old=r"C:\Users\ama\Downloads\spec.docx", thing="h-sp", by="hand", program="explorer.exe")
    s.after(120).add("created", r"C:\Users\ama\Documents\spec.pdf", thing="h-spp", by="hand", program="winword.exe")
    s.after(300).add("deleted", r"C:\Users\ama\Downloads\old-installer.zip", thing="h-oi", by="hand", program="explorer.exe")
    return Scenario("ordinary_day", "An ordinary morning: a note renamed, a download filed, a PDF made, an old installer deleted.", s.out)


def screenshot_of_nothing() -> Scenario:
    s = Script(clock(13, 16, 0))
    s.add("launched", program="snippingtool.exe", by="hand")
    return Scenario("screenshot_of_nothing", "The snipping tool is started on a machine where nothing restricted is being worked on.", s.out)


def goes_dark() -> Scenario:
    s = Script(clock(13, 23, 0))
    s.add("moved", r"C:\Windows\Temp\notes.txt.dll", old=r"C:\Finance\Payroll\payroll-q3.xlsx", thing="h-q3", by="started", program="powershell.exe", tags=R)
    s.after(5).add("hid", r"C:\Windows\Temp\notes.txt.dll", thing="h-q3", by="started", program="powershell.exe", tags=R)
    s.after(120).add("silent", by="alone")
    return Scenario("goes_dark", "Something is hidden, and two minutes later the machine stops reporting while still switched on.", s.out)


def laptop_lid() -> Scenario:
    s = Script(clock(13, 17, 30))
    s.add("silent", by="alone")
    return Scenario("laptop_lid", "A machine stops reporting with nothing else having happened on it.", s.out)


def ransom() -> Scenario:
    s = Script(clock(13, 3, 0))
    for i in range(30):
        s.after(2).add("renamed", rf"C:\Users\kojo\Documents\doc{i}.docx.locked", old=rf"C:\Users\kojo\Documents\doc{i}.docx", thing=f"h-d{i}", by="alone", program="unknown.exe")
    return Scenario("ransom", "Thirty documents are renamed to end in .locked in a minute, by a program, at 03:00.", s.out)


def big_clean_up_by_hand() -> Scenario:
    s = Script(clock(13, 10, 0))
    for i in range(60):
        s.after(1).add("deleted", rf"C:\Users\ama\Documents\old{i}.docx", thing=f"h-o{i}", by="hand", program="explorer.exe")
    return Scenario("big_clean_up_by_hand", "A person selects sixty old documents and deletes them.", s.out)


def restricted_wiped_by_hand() -> Scenario:
    s = Script(clock(13, 21, 30))
    for i in range(60):
        s.after(1).add("deleted", rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"h-p{i}", by="hand", program="explorer.exe", tags=frozenset({"restricted", "outside_role"}))
    return Scenario("restricted_wiped_by_hand", "A person deletes sixty restricted files that are not part of their work, with their own hands, in the evening.", s.out)


def leak_then_clean_up_by_hand() -> Scenario:
    sc = leak()
    last = sc.sigs[-1].at
    s = Script(last + 600)
    for i in range(30):
        s.after(1).add("deleted", rf"C:\Users\ama\Documents\old{i}.docx", thing=f"h-o{i}", by="hand", program="explorer.exe")
    return Scenario("leak_then_clean_up_by_hand", "After the leak, the person deletes thirty documents by hand: the same act that is tidying elsewhere is covering up here.",
                    sc.sigs + s.out, sc.ctx)


def wiped() -> Scenario:
    s = Script(clock(13, 2, 0))
    for i in range(60):
        s.after(1).add("deleted", rf"C:\Users\kojo\Documents\d{i}.docx", thing=f"h-d{i}", by="alone", program="cleaner.exe")
    return Scenario("wiped", "Sixty documents are deleted in a minute by a program, in the small hours.", s.out)


def log_cleared() -> Scenario:
    s = Script(clock(13, 19, 0))
    s.add("cleared", info={"what": "the Security log"}, by="started", program="wevtutil.exe")
    return Scenario("log_cleared", "The machine's security log is cleared.", s.out)


SCENARIOS: dict[str, Callable[[], Scenario]] = {f.__name__: f for f in (leak, backup_twin, patient, one_hidden_file, flow_to_drive, covered_by_task, snooping, screenshots, screenshot_of_nothing, printscreens, printscreen_of_nothing, upload_after_packing, sync_client_upload, zip_one_file_then_upload, convert_then_drive, one_file_to_a_share, sole_copy_deleted, ordinary_delete, lock_out,
                                                                  backups_then_files, weekly_collector, one_look_at_the_director, ordinary_day, goes_dark,
                                                                  laptop_lid, ransom, big_clean_up_by_hand, restricted_wiped_by_hand, leak_then_clean_up_by_hand, wiped, log_cleared)}


def play(sc: Scenario) -> tuple[Detective, list[Update]]:
    det = Detective(sc.ctx)
    updates: list[Update] = []
    for sig in sc.sigs:
        updates.extend(det.feed(sig))
    return det, updates


def show(sc: Scenario) -> None:
    det, updates = play(sc)
    print(f"\n=== {sc.name}: {sc.says}")
    for u in updates:
        if u.raised or u.created and u.now != "quiet":
            n, latest, _ = u.stage
            tag = "RAISED" if u.raised else "started"
            at = time.strftime("%a %H:%M", time.localtime(u.finding.at))
            print(f"  >> {tag} at {at} by: {u.finding.summary}")
            print(f"       now {u.intent} ({u.now}, {u.weight:.2f}), stage {n} of 5: {latest}" + (f" | {u.not_yet}" if u.not_yet else ""))
    cases = det.open_cases()
    if not cases:
        print("  (nothing: no case)")
    for c in cases:
        print(f"  case: {c.intent} -- {c.level} {c.weight:.2f} -- {', '.join(sorted(c.behaviours))}")
        for line in c.story()[:14]:
            print("     ", line)
        print("  said:", c.headline())


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SCENARIOS)
    for name in wanted:
        show(SCENARIOS[name]())
