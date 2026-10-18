"""People, not scripts: regular, careless and smart actors run through Detective many times with the dice rolled differently each time.

    environ-engine\\Scripts\\python.exe scripts\\detective_actors.py [--runs 30] [--seed 1] [name ...]

Each actor has a normal day of its own (saving, filing, deleting, backing up ... "ambient" noise) and, for the ones with a purpose, the things they do about it. The
purposes are what a person with that temperament would plausibly do, written BEFORE looking at what Detective makes of them, and the results are reported as they come
out: what was caught, what was a false alarm, and what was missed (the smart ones are meant to be hard; a miss is information, not an embarrassment).

Levels: 0 quiet (on the record, nobody told), 1 noted, 2 case (people are told), 3 urgent. A regular actor is expected to stay below 2. A malicious one is "seen"
at 1 and "alerted" at 2.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.detective import Context, Detective, Sig

R = frozenset({"restricted"})
RS = frozenset({"restricted", "own_scope"})            # restricted, and belonging to this person's own department: their job is made of it
RO = frozenset({"restricted", "outside_role"})
DAY = 86400.0
PC = 7
LEVEL = {"quiet": 0, "noted": 1, "case": 2, "urgent": 3}
T0 = 1_792_000_000.0                                    # a Tuesday morning


@dataclass
class Actor:
    name: str
    kind: str                       # regular | careless | smart
    intent: str                     # what they are doing, in a line
    bad: bool                       # is there something to find
    build: Callable[[random.Random], tuple[list[Sig], Context]]
    expect: str = ""                # what the owner of the design hopes for, in a line (for the report)


class Day:
    """A person's day, built forward in time."""

    def __init__(self, rng: random.Random, start: float = T0 + 9 * 3600) -> None:
        self.rng, self.t, self.out = rng, start, []

    def gap(self, lo: float, hi: float) -> Day:
        self.t += self.rng.uniform(lo, hi)
        return self

    def do(self, verb: str, path: str = "", **kw) -> Day:
        kw.setdefault("by", "hand")
        self.out.append(Sig(self.t, PC, verb, path, **kw))
        return self

    def ambient(self, n: int, user: str = "ama") -> Day:
        """The ordinary traffic of a working person: saves, filing, a download, a PDF, an old file deleted."""
        r = self.rng
        for i in range(n):
            self.gap(30, 600)
            pick = r.random()
            doc = rf"C:\Users\{user}\Documents\Work\file{r.randint(1, 40)}.docx"
            if pick < 0.40:
                self.do("modified", doc, thing=f"a{r.randint(1, 60)}", program="winword.exe")
            elif pick < 0.60:
                self.do("copied", rf"C:\Users\{user}\Documents\Work\spec{i}.docx", old=rf"C:\Users\{user}\Downloads\spec{i}.docx", thing=f"d{i}", program="explorer.exe")
            elif pick < 0.75:
                self.do("created", rf"C:\Users\{user}\Documents\Work\report{i}.pdf", thing=f"p{i}", program="winword.exe")
            elif pick < 0.85:
                self.do("renamed", rf"C:\Users\{user}\Documents\Work\notes{i}.md", old=rf"C:\Users\{user}\Documents\Work\notes{i}.txt", thing=f"n{i}", program="explorer.exe")
            elif pick < 0.95:
                self.do("deleted", rf"C:\Users\{user}\Downloads\old{i}.zip", thing=f"o{i}", program="explorer.exe", tags=frozenset({"only_copy"}))
            else:
                self.do("created", rf"C:\Users\{user}\Documents\Work\pack{i}.zip", thing=f"z{i}", by="started", program="7z.exe")
        return self


def drive(d: Day, letter: str = "E:\\") -> Day:
    return d.gap(5, 40).do("attached", letter, device=letter, by="alone")


# --- regular -----------------------------------------------------------------------------------------------------------

def clerk(rng):
    d = Day(rng).ambient(rng.randint(40, 90))
    return d.out, Context()


def finance_analyst(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "fin")
    for i in range(rng.randint(6, 14)):                                          # their own restricted files, in their own folder, for their own work
        d.gap(20, 300).do("copied", rf"C:\Users\fin\Documents\Close\q3-{i}.xlsx", old=rf"C:\Finance\Close\q3-{i}.xlsx", thing=f"fq{i}", program="excel.exe", tags=RS)
    drive(d).gap(30, 120)                                                         # the Friday backup of their own work, to the drive they always use
    for i in range(rng.randint(3, 8)):
        d.gap(2, 8).do("copied", rf"E:\backup\q3-{i}.xlsx", old=rf"C:\Users\fin\Documents\Close\q3-{i}.xlsx", thing=f"fq{i}", program="explorer.exe", tags=RS)
    return d.out, Context(known_device=lambda pc, dev: 60)


def it_admin(rng):
    d = Day(rng, T0 + 2 * 3600).ambient(rng.randint(10, 20), "it")
    for i in range(rng.randint(14, 40)):                                         # the nightly backup and the clean-up of old logs and temp files
        d.gap(1, 4).do("copied", rf"D:\Staging\db{i}.bak", old=rf"C:\Data\db{i}.bak", thing=f"db{i}", by="alone", program="robocopy.exe")
    for i in range(rng.randint(80, 220)):
        d.gap(0.2, 1).do("deleted", rf"C:\Users\it\AppData\Local\Temp\t{i}.tmp", thing=f"t{i}", by="alone", program="cleanmgr.exe")
    if rng.random() < 0.5:
        d.gap(60, 300).do("cleared", info={"what": "the Application log", "log": "Application"}, by="started", program="wevtutil.exe")
    return d.out, Context(known_device=lambda pc, dev: 99)


def developer(rng):
    d = Day(rng).ambient(rng.randint(30, 60), "dev")
    for i in range(rng.randint(30, 120)):                                         # a build: lots of files made, renamed and deleted by a program
        d.gap(0.5, 3).do("created", rf"C:\src\app\build\out{i}.dll", thing=f"b{i}", by="started", program="msbuild.exe")
    d.gap(10, 60).do("created", r"C:\src\app\release\app.zip", thing="rel", by="started", program="7z.exe")
    d.gap(10, 60).do("uploaded", program="git.exe", by="unknown", info={"bytes": rng.randint(20, 90) * 1_000_000, "to": "140.82.112.3", "destinations": 1, "seconds": 60})
    return d.out, Context()


def new_starter(rng):
    d = Day(rng).ambient(rng.randint(30, 60), "new")
    for i in range(rng.randint(15, 40)):                                          # reads everything they are allowed to, to find their feet
        d.gap(20, 120).do("opened", rf"\\fileserver\team\docs\guide{i}.docx", thing=f"g{i}", program="winword.exe")
    return d.out, Context()


def manager(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "mgr")
    for _ in range(rng.randint(2, 6)):
        d.gap(600, 3000).do("uploaded", program="teams.exe", by="unknown", info={"bytes": rng.randint(30, 200) * 1_000_000, "to": "52.112.0.1", "destinations": 4, "seconds": 60})
    for _ in range(rng.randint(1, 4)):
        d.gap(60, 600).do("launched", program="snippingtool.exe", by="hand")
    return d.out, Context()


def leaving_tidy(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "lea")
    for i in range(rng.randint(30, 90)):                                          # clearing out their own old files the week they leave
        d.gap(0.5, 3).do("deleted", rf"C:\Users\lea\Documents\Old\d{i}.docx", thing=f"ol{i}", program="explorer.exe", tags=frozenset({"only_copy"}))
    drive(d).gap(30, 90)
    for i in range(rng.randint(5, 20)):                                           # and takes their own photos and personal documents on a drive
        d.gap(1, 5).do("copied", rf"E:\mine\photo{i}.jpg", old=rf"C:\Users\lea\Pictures\photo{i}.jpg", thing=f"ph{i}", program="explorer.exe")
    return d.out, Context()


# --- careless -----------------------------------------------------------------------------------------------------------

def clumsy_thief(rng):
    d = Day(rng).ambient(rng.randint(10, 30), "kojo")
    drive(d).gap(20, 80)
    for i in range(rng.randint(8, 25)):                                           # straight onto the drive, in plain sight, by hand
        d.gap(1, 6).do("copied", rf"E:\p{i}.xlsx", old=rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"pay{i}", program="explorer.exe", tags=R)
    return d.out, Context(known_device=lambda pc, dev: 0)


def careless_deleter(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "pat")
    for i in range(rng.randint(1, 3)):                                            # picked the wrong folder and pressed delete
        d.gap(5, 60).do("deleted", rf"C:\Legal\contracts\c{i}.docx", thing=f"lc{i}", program="explorer.exe", tags=frozenset({"restricted", "only_copy"}))
    return d.out, Context()


def accidental_uploader(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "sam")
    d.gap(600, 3000).do("uploaded", program="chrome.exe", by="unknown", info={"bytes": rng.randint(100, 400) * 1_000_000, "to": "142.250.0.1", "destinations": 1, "seconds": 60})
    return d.out, Context()


def open_snoop(rng):
    d = Day(rng).ambient(rng.randint(10, 30), "nos")
    for i in range(rng.randint(6, 18)):                                           # wanders the HR share, opening what is not theirs
        d.gap(10, 90).do("opened", rf"\\hr\files\staff\person{i}.docx", thing=f"hrp{i}", program="winword.exe", tags=RO)
    return d.out, Context()


def printscreen_fan(rng):
    d = Day(rng).ambient(rng.randint(10, 30), "pic")
    d.gap(30, 90).do("opened", r"C:\Finance\Payroll\payroll-q3.xlsx", thing="pq3", program="excel.exe", tags=R)
    for _ in range(rng.randint(4, 12)):
        d.gap(10, 60).do("captured", program="excel.exe", info={"kind": "screen"})
    return d.out, Context()


def ransomware_clicker(rng):
    d = Day(rng).ambient(rng.randint(10, 30), "oops")
    d.gap(60, 600)
    for i in range(rng.randint(40, 150)):
        d.gap(0.2, 1).do("renamed", rf"C:\Users\oops\Documents\Work\f{i}.docx.locked", old=rf"C:\Users\oops\Documents\Work\f{i}.docx", thing=f"rw{i}", by="alone", program="invoice.exe")
    return d.out, Context()


# --- smart --------------------------------------------------------------------------------------------------------------

def patient_dripper(rng):
    d = Day(rng, T0)
    weeks = rng.randint(3, 5)
    for w in range(weeks):                                                        # one restricted file a week into a folder that looks like nothing
        d.t = T0 + w * 7 * DAY + 10 * 3600 + rng.uniform(0, 3600)
        d.ambient(rng.randint(8, 15), "kojo")
        d.gap(10, 90).do("copied", rf"C:\Users\kojo\Misc\r{w}.xlsx", old=rf"C:\Finance\Payroll\r{w}.xlsx", thing=f"dr{w}", program="explorer.exe", tags=R)
    d.t = T0 + weeks * 7 * DAY + 21 * 3600
    d.gap(10, 60).do("created", r"C:\Users\kojo\Misc\holiday.zip", thing="dz", by="started", program="7z.exe")
    d.gap(60, 240).do("uploaded", program="chrome.exe", by="unknown", info={"bytes": rng.randint(9, 14) * 1_000_000, "to": "198.51.100.7", "destinations": 1, "seconds": 60})
    return d.out, Context()


def drip_under_the_line(rng):
    """The same, but the upload goes in pieces that never reach the volume that is reported."""
    sigs, ctx = patient_dripper(rng)
    return [s for s in sigs if s.verb != "uploaded"], ctx


def trusted_drive_abuser(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "kojo")
    drive(d).gap(60, 300)
    d.do("copied", r"E:\notes\customers-master.xlsx", old=r"C:\Finance\Sales\customers-master.xlsx", thing="cm", program="explorer.exe", tags=R)
    return d.out, Context(known_device=lambda pc, dev: 80)


def disguiser(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "kojo")
    d.gap(30, 120).do("copied", r"C:\Users\kojo\Pictures\beach.jpg", old=r"C:\Finance\Payroll\payroll-q3.xlsx", thing="pq3", program="explorer.exe", tags=R)
    d.gap(5, 30).do("renamed", r"C:\Users\kojo\Pictures\beach2.jpg", old=r"C:\Users\kojo\Pictures\beach.jpg", thing="pq3", program="explorer.exe", tags=R)
    d.gap(5, 30).do("hid", r"C:\Users\kojo\Pictures\beach2.jpg", thing="pq3", program="explorer.exe", tags=R)
    drive(d).gap(900, 1500)                                                       # waits twenty minutes before the drive
    d.do("copied", r"E:\beach2.jpg", old=r"C:\Users\kojo\Pictures\beach2.jpg", thing="pq3", program="explorer.exe", tags=R)
    return d.out, Context(known_device=lambda pc, dev: 0)


def task_cover(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "kojo")
    drive(d).gap(60, 300)
    for i in range(6):                                                            # one file is what the task asked for; five more go with it
        d.gap(1, 5).do("copied", rf"E:\pack{i}.xlsx", old=rf"C:\Finance\Board\pack{i}.xlsx", thing=f"bp{i}", program="explorer.exe", tags=R)
    return d.out, Context(task_things=lambda pc: {"bp0"}, known_device=lambda pc, dev: 0)


def sole_copy_remover(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "kojo")
    d.gap(60, 600).do("deleted", r"C:\Legal\contracts\amendment-7.docx", thing="am7", program="explorer.exe", tags=frozenset({"restricted", "only_copy"}))
    return d.out, Context()


def sync_client_abuser(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "kojo")
    for i in range(rng.randint(5, 15)):
        d.gap(1, 4).do("copied", rf"C:\Users\kojo\OneDrive\work\p{i}.xlsx", old=rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"od{i}", program="explorer.exe", tags=R)
    d.gap(30, 120).do("uploaded", program="onedrive.exe", by="unknown", info={"bytes": rng.randint(40, 90) * 1_000_000, "to": "13.107.42.12", "destinations": 3, "seconds": 60})
    return d.out, Context()


def slow_poison(rng):
    d = Day(rng, T0)
    for day in range(rng.randint(8, 14)):                                         # a couple of figures changed a day in a sheet people trust
        d.t = T0 + day * DAY + 14 * 3600
        d.ambient(rng.randint(8, 15), "kojo")
        d.gap(30, 300).do("modified", r"C:\Finance\Budget\forecast.xlsx", thing=f"fc{day}", program="excel.exe", tags=R)
    return d.out, Context()


def leak_then_tidy(rng):
    d = Day(rng).ambient(rng.randint(10, 20), "kojo")
    d.gap(30, 120).do("created", r"C:\Users\kojo\Staging\q3.zip", thing="z", by="started", program="7z.exe")
    for i in range(rng.randint(4, 10)):
        d.gap(1, 5).do("copied", rf"C:\Users\kojo\Staging\p{i}.xlsx", old=rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"lp{i}", program="explorer.exe", tags=R)
    drive(d).gap(20, 60)
    d.do("copied", r"E:\q3.zip", old=r"C:\Users\kojo\Staging\q3.zip", thing="z", program="explorer.exe", tags=R)
    d.gap(20, 90).do("deleted", r"C:\Users\kojo\Staging\q3.zip", thing="z", program="explorer.exe")
    return d.out, Context(known_device=lambda pc, dev: 0)


def outside_the_roots(rng):
    """Does everything in a folder the Worker is not watching: nothing reaches Detective at all."""
    d = Day(rng).ambient(rng.randint(15, 30), "kojo")
    return d.out, Context()


# --- held out: written after the weights were tuned against the actors above, and run once before anything was changed -----------------------

def hr_officer(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "hr")
    for i in range(rng.randint(8, 25)):                                           # reads and exports staff files, all within their own department's restricted scope
        d.gap(30, 400).do("opened", rf"\\hr\files\staff\person{i}.docx", thing=f"hs{i}", program="winword.exe", tags=RS)
        if rng.random() < 0.3:
            d.gap(5, 20).do("created", rf"C:\Users\hr\Documents\export{i}.pdf", thing=f"he{i}", program="winword.exe", tags=RS)
    return d.out, Context()


def designer(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "des")
    for i in range(rng.randint(3, 10)):
        d.gap(30, 300).do("created", rf"C:\Users\des\Projects\shoot{i}.psd", thing=f"ps{i}", program="photoshop.exe")
    d.gap(60, 300).do("created", r"C:\Users\des\Projects\delivery.zip", thing="dl", by="started", program="7z.exe")
    d.gap(60, 300).do("uploaded", program="chrome.exe", by="unknown", info={"bytes": rng.randint(200, 600) * 1_000_000, "to": "108.177.0.1", "destinations": 1, "seconds": 60})
    drive(d).gap(30, 90)
    for i in range(rng.randint(3, 8)):
        d.gap(5, 20).do("copied", rf"E:\shoot{i}.psd", old=rf"C:\Users\des\Projects\shoot{i}.psd", thing=f"ps{i}", program="explorer.exe")
    return d.out, Context(known_device=lambda pc, dev: 30)


def contractor_wrap_up(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "con")
    drive(d).gap(60, 300)
    for i in range(rng.randint(10, 30)):                                          # the last day of a project: their own project documents, on a drive, with a note to the client
        d.gap(1, 6).do("copied", rf"E:\project\doc{i}.docx", old=rf"C:\Users\con\Documents\Project\doc{i}.docx", thing=f"pj{i}", program="explorer.exe")
    return d.out, Context()


def disgruntled_wrecker(rng):
    d = Day(rng, T0 + 13 * 3600).ambient(rng.randint(10, 20), "kojo")
    for i in range(2):
        d.gap(30, 120).do("deleted", rf"D:\Backups\nightly-{i}.vhdx", thing=f"bk{i}", program="explorer.exe")
    for i in range(rng.randint(3, 6)):
        d.gap(20, 90).do("deleted", rf"C:\Projects\core\design{i}.xlsx", thing=f"cd{i}", program="explorer.exe", tags=frozenset({"restricted", "only_copy"}))
    return d.out, Context()


def browser_drip(rng):
    d = Day(rng).ambient(rng.randint(10, 20), "kojo")
    for i in range(rng.randint(6, 12)):                                           # one restricted file at a time, small enough never to be a volume
        d.gap(300, 900).do("copied", rf"C:\Users\kojo\Desktop\f{i}.xlsx", old=rf"C:\Finance\Payroll\f{i}.xlsx", thing=f"bd{i}", program="explorer.exe", tags=R)
        # (the uploads themselves, a few MB each, are never a volume the Worker reports: nothing is sent for them)
    return d.out, Context()


def flow_misuse(rng):
    """An Admin has built a flow that carries a folder to a share they control: the files arrive written by Falcon itself."""
    d = Day(rng).ambient(rng.randint(10, 20), "adm")
    for i in range(rng.randint(10, 40)):
        d.gap(1, 4).do("copied", rf"\\share\mine\p{i}.xlsx", old=rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"fl{i}", by="falcon", program="falcon.exe", tags=R)
    return d.out, Context()


def tmp_then_zip_then_drive(rng):
    d = Day(rng).ambient(rng.randint(10, 20), "kojo")
    for i in range(rng.randint(8, 14)):
        d.gap(2, 10).do("copied", rf"C:\Users\kojo\Misc\x{i}.tmp", old=rf"C:\Finance\Payroll\p{i}.xlsx", thing=f"tz{i}", program="explorer.exe", tags=R)
    d.gap(20, 60).do("created", r"C:\Users\kojo\Misc\x.zip", thing="tzz", by="started", program="7z.exe")
    drive(d).gap(30, 90)
    d.do("copied", r"E:\x.zip", old=r"C:\Users\kojo\Misc\x.zip", thing="tzz", program="explorer.exe")
    return d.out, Context(known_device=lambda pc, dev: 0)


def curious_it(rng):
    d = Day(rng, T0 + 21 * 3600).ambient(rng.randint(5, 10), "it")
    for i in range(rng.randint(12, 30)):
        d.gap(10, 60).do("opened", rf"\\hr\files\{rng.choice(['staff', 'payroll', 'reviews'])}\f{i}.docx", thing=f"ci{i}", program="winword.exe", tags=RO)
    return d.out, Context()


def one_file_by_email(rng):
    """Takes the one file by attaching it to a message: nothing about it leaves a trace Detective can see."""
    d = Day(rng).ambient(rng.randint(15, 30), "kojo")
    d.gap(60, 600).do("opened", r"C:\Finance\Sales\customers-master.xlsx", thing="cm", program="excel.exe", tags=R)
    return d.out, Context()


# --- a second held-out set: written after the fixes the first one exposed, run once, before any change -----------------------------------------

def sales_rep(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "sal")
    for i in range(rng.randint(4, 12)):
        d.gap(60, 600).do("opened", rf"C:\CRM\customers\c{i}.xlsx", thing=f"cr{i}", program="excel.exe", tags=RS)
        d.gap(5, 30).do("created", rf"C:\Users\sal\Desktop\export{i}.csv", thing=f"ex{i}", program="excel.exe", tags=RS)
    drive(d).gap(30, 90)
    for i in range(rng.randint(2, 6)):
        d.gap(2, 8).do("copied", rf"E:\export{i}.csv", old=rf"C:\Users\sal\Desktop\export{i}.csv", thing=f"ex{i}", program="explorer.exe", tags=RS)
    return d.out, Context(known_device=lambda pc, dev: 20)


def auditor_with_a_task(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "aud")
    n = rng.randint(15, 40)
    for i in range(n):                                                            # the audit asks them to read other departments' restricted files
        d.gap(30, 300).do("opened", rf"\\fin\ledgers\l{i}.xlsx", thing=f"au{i}", program="excel.exe", tags=RO)
    return d.out, Context(task_things=lambda pc: {f"au{i}" for i in range(n)})


def devops_at_night(rng):
    d = Day(rng, T0 + 2 * 3600).ambient(rng.randint(5, 10), "ops")
    for i in range(rng.randint(100, 300)):
        d.gap(0.2, 1).do("deleted", rf"D:\builds\old\b{i}.zip", thing=f"ob{i}", by="alone", program="powershell.exe")
    d.gap(10, 60).do("created", r"D:\builds\release.zip", thing="rz", by="alone", program="7z.exe")
    d.gap(10, 60).do("uploaded", program="curl.exe", by="unknown", info={"bytes": rng.randint(200, 500) * 1_000_000, "to": "52.1.1.1", "destinations": 1, "seconds": 60})
    d.gap(10, 60).do("cleared", info={"what": "the Application log", "log": "Application"}, by="started", program="wevtutil.exe")
    return d.out, Context()


def intern_friday_backup(rng):
    d = Day(rng).ambient(rng.randint(20, 40), "int")
    drive(d).gap(30, 90)
    for i in range(rng.randint(60, 200)):
        d.gap(0.5, 3).do("copied", rf"E:\mine\f{i}.docx", old=rf"C:\Users\int\Documents\f{i}.docx", thing=f"if{i}", program="explorer.exe")
    return d.out, Context(known_device=lambda pc, dev: 12)


def resentful_leaver(rng):
    d = Day(rng, T0 + 12 * 3600).ambient(rng.randint(10, 20), "kojo")
    d.gap(30, 120).do("copied", r"C:\Users\kojo\Desktop\holiday.jpg", old=r"C:\CRM\customers\master.xlsx", thing="cm", program="explorer.exe", tags=R)
    d.gap(5, 20).do("hid", r"C:\Users\kojo\Desktop\holiday.jpg", thing="cm", program="explorer.exe", tags=R)
    d.t = T0 + 19 * 3600
    drive(d).gap(20, 60)
    d.do("copied", r"E:\holiday.jpg", old=r"C:\Users\kojo\Desktop\holiday.jpg", thing="cm", program="explorer.exe", tags=R)
    d.gap(10, 40).do("deleted", r"C:\Users\kojo\Desktop\holiday.jpg", thing="cm", program="explorer.exe")
    return d.out, Context(known_device=lambda pc, dev: 0)


def support_screenshots(rng):
    d = Day(rng).ambient(rng.randint(15, 30), "sup")
    for _ in range(rng.randint(2, 5)):
        d.gap(30, 300).do("captured", program="chrome.exe", info={"kind": "region"})
    return d.out, Context()


def vindictive_folder_delete(rng):
    d = Day(rng, T0 + 17 * 3600).ambient(rng.randint(5, 15), "kojo")
    for i in range(rng.randint(30, 70)):                                          # deletes a team's shared project folder, by hand, on the way out
        d.gap(0.5, 2).do("deleted", rf"\\fileserver\team\project-atlas\task{i}.xlsx", thing=f"at{i}", program="explorer.exe", tags=frozenset({"only_copy"}))
    return d.out, Context()


ACTORS: list[Actor] = [
    Actor("clerk", "regular", "an ordinary working day", False, clerk, "quiet"),
    Actor("finance_analyst", "regular", "restricted files in their own work, a Friday backup to the usual drive", False, finance_analyst, "quiet or noted at most"),
    Actor("it_admin", "regular", "nightly backup, clears old temp files, clears an event log", False, it_admin, "quiet or noted"),
    Actor("developer", "regular", "a build, a release zip, an artifact upload", False, developer, "quiet"),
    Actor("new_starter", "regular", "reads every document they are allowed to", False, new_starter, "quiet"),
    Actor("manager", "regular", "video calls, screenshots of their own screen", False, manager, "quiet"),
    Actor("leaving_tidy", "regular", "deletes their own old drafts and takes their photos on a drive", False, leaving_tidy, "quiet or noted"),
    Actor("clumsy_thief", "careless", "copies payroll files straight onto a new drive, in plain sight", True, clumsy_thief, "case"),
    Actor("careless_deleter", "careless", "deletes the wrong contracts by mistake", True, careless_deleter, "noted: an accident worth knowing about"),
    Actor("accidental_uploader", "careless", "uploads a personal video, nothing to do with work", False, accidental_uploader, "quiet"),
    Actor("open_snoop", "careless", "wanders through the HR share opening people's files", True, open_snoop, "noted or case"),
    Actor("printscreen_fan", "careless", "presses PrintScreen over the payroll sheet again and again", True, printscreen_fan, "case"),
    Actor("ransomware_clicker", "careless", "opens an attachment that scrambles their documents", True, ransomware_clicker, "case"),
    Actor("patient_dripper", "smart", "a restricted file a week for weeks, zipped and sent in one go", True, patient_dripper, "noted at least"),
    Actor("drip_under_the_line", "smart", "the same, but sent in pieces too small to be seen", True, drip_under_the_line, "unknowable by volume"),
    Actor("trusted_drive_abuser", "smart", "one restricted file on the drive everyone uses", True, trusted_drive_abuser, "noted"),
    Actor("disguiser", "smart", "renames, hides, waits twenty minutes, then the drive", True, disguiser, "case"),
    Actor("task_cover", "smart", "has a task for one file and takes five more with it", True, task_cover, "noted"),
    Actor("sole_copy_remover", "smart", "deletes the one contract amendment, nothing else", True, sole_copy_remover, "case"),
    Actor("sync_client_abuser", "smart", "copies payroll into the company's sync folder", True, sync_client_abuser, "noted"),
    Actor("slow_poison", "smart", "changes a figure or two a day in a sheet people trust", True, slow_poison, "noted"),
    Actor("leak_then_tidy", "smart", "packs, takes it out, deletes the pack", True, leak_then_tidy, "case"),
    Actor("outside_the_roots", "smart", "works where the Worker does not look", True, outside_the_roots, "invisible by design"),
    # held out
    Actor("hr_officer", "held-out", "reads and exports staff files in their own department's scope", False, hr_officer, "quiet or noted"),
    Actor("designer", "held-out", "big media files, a 500 MB delivery to a client, a drive they always use", False, designer, "quiet or noted"),
    Actor("contractor_wrap_up", "held-out", "puts their own project documents on a drive on the last day", False, contractor_wrap_up, "quiet or noted"),
    Actor("disgruntled_wrecker", "held-out", "deletes two backups and the only copies of the core designs", True, disgruntled_wrecker, "case"),
    Actor("browser_drip", "held-out", "a restricted file at a time, each sent in a few MB through the browser", True, browser_drip, "noted at least"),
    Actor("flow_misuse", "held-out", "an Admin's own flow carries the payroll to a share", True, flow_misuse, "invisible by construction"),
    Actor("tmp_then_zip_then_drive", "held-out", "renames payroll to .tmp, zips, drive", True, tmp_then_zip_then_drive, "case"),
    Actor("curious_it", "held-out", "an admin opens many HR files at night", True, curious_it, "noted or case"),
    Actor("one_file_by_email", "held-out", "opens the one file and e-mails it", True, one_file_by_email, "invisible by design"),
    # held out, second set
    Actor("sales_rep", "held-out-2", "opens customer lists in their own scope, exports CSVs, backs a few up to their usual drive", False, sales_rep, "quiet or noted"),
    Actor("auditor_with_a_task", "held-out-2", "reads other departments' ledgers because the audit task says to", False, auditor_with_a_task, "quiet or noted"),
    Actor("devops_at_night", "held-out-2", "a night deploy: deletes hundreds of old builds, uploads a release by curl, clears the app log", False, devops_at_night, "quiet or noted"),
    Actor("intern_friday_backup", "held-out-2", "copies a hundred or so of their own documents to a drive they use every week", False, intern_friday_backup, "quiet or noted"),
    Actor("resentful_leaver", "held-out-2", "copies the customer master as a .jpg, hides it, takes it out in the evening, deletes the copy", True, resentful_leaver, "case"),
    Actor("support_screenshots", "held-out-2", "screenshots an error dialog for a ticket", False, support_screenshots, "quiet"),
    Actor("vindictive_folder_delete", "held-out-2", "deletes a team's shared project folder by hand on the way out", True, vindictive_folder_delete, "case"),
]


def run(actor: Actor, seed: int) -> tuple[int, float, list[str]]:
    rng = random.Random(seed)
    sigs, ctx = actor.build(rng)
    sigs.sort(key=lambda s: s.at)
    det = Detective(ctx)
    for s in sigs:
        det.feed(s)
    top = max(det.cases, key=lambda c: c.weight, default=None)
    if top is None:
        return 0, 0.0, []
    return LEVEL[top.level], top.weight, sorted(top.behaviours)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("names", nargs="*")
    args = ap.parse_args(argv)
    chosen = [a for a in ACTORS if not args.names or a.name in args.names]
    print(f"{'actor':22} {'kind':9} {'quiet':>5} {'noted':>5} {'case':>5} {'urgent':>6}   hoped for")
    for a in chosen:
        levels = [run(a, args.seed * 1000 + i)[0] for i in range(args.runs)]
        n = len(levels)
        pct = [round(100 * levels.count(k) / n) for k in range(4)]
        print(f"{a.name:22} {a.kind:9} {pct[0]:>4}% {pct[1]:>4}% {pct[2]:>4}% {pct[3]:>5}%   {a.expect}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
