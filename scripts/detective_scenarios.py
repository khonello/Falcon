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


SCENARIOS: dict[str, Callable[[], Scenario]] = {f.__name__: f for f in (leak, backup_twin, patient, one_hidden_file, flow_to_drive, covered_by_task, snooping)}


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
