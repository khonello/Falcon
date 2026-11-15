"""The machine snapshot (proposals item 3): a loose picture of the whole machine, compared by the Engine with the last one, for Detective alone.
What changed becomes a light Detective signal; a part that could not be read is never taken for "everything was removed"; storage is read through
the places, so a person's own Documents shrinking is not the Recycle Bin being emptied."""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

from common.anchors import ANCHORS
from common.detective import SYSTEM_CHANGES, Detective, Sig
from engine.detective.snapshot import changes
from tests.conftest import requires_db
from worker_client import machine_snapshot as ms
from worker_client.snapshot import Snapshot

GIB = 1024 ** 3


def _pic(**over) -> dict:
    base = {
        "admins": ["PC\\Administrator", "PC\\it-admin"], "accounts": ["Administrator", "ama"],
        "startup": ["the machine: Run: Teams = teams.exe"], "services": ["Spooler = spoolsv.exe"], "tasks": ["Adobe Update"],
        "programs": ["7-Zip 24.09", "Microsoft Office 16.0"], "shares": ["ADMIN$ = C:\\Windows", "C$ = C:\\"],
        "defender": {"realtime_off": False, "firewall_off_domain": False, "firewall_off_public": False},
        "logs": {"Security": 20_000_000, "System": 20_000_000},
        "places": [{"kind": "documents", "user": "ama", "path": r"C:\Users\ama\Documents", "bytes": 12 * GIB, "files": 9000, "partial": False},
                   {"kind": "temp", "user": "ama", "path": r"C:\Users\ama\AppData\Local\Temp", "bytes": 6 * GIB, "files": 4000, "partial": False},
                   {"kind": "recycle_bin", "user": "", "path": r"C:\$Recycle.Bin", "bytes": 20 * GIB, "files": 300, "partial": False}],
    }
    base.update(over)
    return base


def _kinds(found: list[dict]) -> list[str]:
    return [c["change"] for c in found]


# --- what counts as a change ------------------------------------------------------------------------------------------

def test_nothing_changed_says_nothing():
    assert changes(_pic(), _pic()) == []


def test_each_kind_of_change_is_found_and_said_in_words():
    now = _pic(admins=["PC\\Administrator", "PC\\it-admin", "PC\\ama"], accounts=["Administrator", "ama", "backup2"],
               startup=["the machine: Run: Teams = teams.exe", "ama: Run: sync = C:\\Users\\ama\\s.vbs"], services=["Spooler = spoolsv.exe", "Copier = c.exe"],
               tasks=["Adobe Update", "nightly-copy"], programs=["7-Zip 24.09", "Microsoft Office 16.0", "Eraser 6.2", "VeraCrypt 1.26", "Zoom 6.0"],
               shares=["ADMIN$ = C:\\Windows", "C$ = C:\\", "Payroll = C:\\Finance\\Payroll", "D$ = D:\\"],
               defender={"realtime_off": True, "firewall_off_domain": True, "firewall_off_public": False}, logs={"Security": 69_632, "System": 20_000_000})
    found = changes(_pic(), now)
    assert sorted(_kinds(found)) == sorted(["admin_added", "account_added", "starts_by_itself", "service_added", "task_added", "wiper_installed",
                                            "encryptor_installed", "share_added", "protection_off", "firewall_off", "log_shrank"])
    words = {c["change"]: c["words"] for c in found}
    assert words["admin_added"] == "PC\\ama was made an administrator of the machine"
    assert words["share_added"] == "a folder was shared on the network: C:\\Finance\\Payroll"            # D$ is Windows' own and says nothing
    assert words["wiper_installed"].startswith("Eraser was installed") and "Zoom" not in str(found)
    assert "domain" in words["firewall_off"] and "emptied" in words["log_shrank"]
    assert all(c in SYSTEM_CHANGES for c in _kinds(found))


def test_a_part_that_could_not_be_read_is_never_taken_for_everything_removed():
    gone = _pic()
    del gone["admins"], gone["programs"], gone["places"]
    assert changes(_pic(), gone) == []
    assert changes(gone, _pic()) == []                    # ... nor, read again, for everything new
    assert _kinds(changes(_pic(admins=["PC\\Administrator"]), _pic())) == ["admin_added"]      # (the one present before is not "added" again)
    assert changes(_pic(), _pic(admins=["PC\\Administrator"])) == []                             # someone losing power is nothing to read


def test_documents_shrinking_is_read_and_the_recycle_bin_emptying_is_not():
    shrunk = _pic(places=[{"kind": "documents", "user": "ama", "path": r"C:\Users\ama\Documents", "bytes": 2 * GIB, "files": 1200, "partial": False},
                          {"kind": "temp", "user": "ama", "path": r"C:\Users\ama\AppData\Local\Temp", "bytes": 0, "files": 0, "partial": False},
                          {"kind": "recycle_bin", "user": "", "path": r"C:\$Recycle.Bin", "bytes": 0, "files": 0, "partial": False}])
    (c,) = changes(_pic(), shrunk)
    assert c["change"] == "documents_shrank" and c["scale"] == 1.5 and "ama's Documents holds 10.0 GB less" in c["words"] and "7800 fewer files" in c["words"]
    cleanup = _pic(places=[_pic()["places"][0], {**_pic()["places"][1], "bytes": 0}, {**_pic()["places"][2], "bytes": 0}])
    assert changes(_pic(), cleanup) == []                  # 26 GB freed in Temp and the Recycle Bin: a clean-up
    small = _pic(places=[{**_pic()["places"][0], "bytes": 11 * GIB}])
    assert changes(_pic(), small) == []                    # 1 GB of 12 is ordinary
    half_seen = _pic(places=[{**_pic()["places"][0], "bytes": 1 * GIB, "partial": True}])
    assert changes(_pic(), half_seen) == []                # measured only partly: nothing can be said
    filled = _pic(places=[{**_pic()["places"][0], "bytes": 30 * GIB}])
    assert _kinds(changes(_pic(), filled)) == ["filled_up"]


def test_a_reimaged_machine_cannot_flood_detective():
    now = _pic(tasks=[f"task {i}" for i in range(500)])
    assert len(changes(_pic(), now)) == 40


# --- Detective reads them ---------------------------------------------------------------------------------------------

def _sys(change: str, **info) -> Sig:
    return Sig(1_700_000_000.0, 3, "system", thing=f"system:{change}", info={"change": change, "words": f"{change} happened", **info})


def test_every_change_falls_in_an_area_detective_has():
    for behaviour, area, w in SYSTEM_CHANGES.values():
        assert area in [a.name for a in ANCHORS[behaviour]] and 0 < w <= 0.35
    assert next(a for a in ANCHORS["evasion"] if a.name == "Dodge").seen and next(a for a in ANCHORS["erasure"] if a.name == "Switch off the record").seen


def test_a_new_administrator_is_noted_and_reads_in_words():
    det = Detective()
    ups = det.feed(_sys("admin_added", words="PC\\ama was made an administrator of the machine"))
    assert ups and ups[0].finding.behaviour == "reach" and ups[0].finding.weight >= 0.3
    assert "PC\\ama was made an administrator of the machine" in " ".join(det.cases[0].story())
    assert det.cases[0].level in ("quiet", "noted")                        # alone it is not a case


def test_falcons_own_actions_in_that_stretch_weigh_half():
    alone = Detective().feed(_sys("protection_off"))[0].finding.weight
    near = Detective().feed(_sys("protection_off", falcon_ran=2))
    assert not near or near[0].finding.weight < alone


def test_a_new_administrator_beside_a_taking_out_adds_to_the_case():
    det = Detective()
    t = 1_700_000_000.0
    for i in range(6):
        det.feed(Sig(t + i, 3, "copied", rf"C:\Users\ama\Staging\p{i}.xlsx", rf"C:\Finance\Payroll\p{i}.xlsx", f"h{i}", tags=frozenset({"restricted"})))
    before = max(c.weight for c in det.cases)
    det.feed(Sig(t + 60, 3, "system", thing="system:admin_added", info={"change": "admin_added", "words": "PC\\ama was made an administrator"}))
    det.feed(Sig(t + 61, 3, "system", thing="system:protection_off", info={"change": "protection_off", "words": "Defender was turned off"}))
    assert max(c.weight for c in det.cases) > before


# --- the Worker reads the machine -------------------------------------------------------------------------------------

class Reg:
    def __init__(self, keys: dict[tuple[str, str], dict], subs: dict[tuple[str, str], list[str]]) -> None:
        self.keys = {(r, k.lower()): v for (r, k), v in keys.items()}
        self.subs = {(r, k.lower()): v for (r, k), v in subs.items()}

    def values(self, root: str, key: str) -> dict:
        return dict(self.keys.get((root, key.lower()), {}))

    def subkeys(self, root: str, key: str) -> list[str]:
        return list(self.subs.get((root, key.lower()), []))


SID = "S-1-5-21-1-2-3-1001"
PL = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"


def _reg() -> Reg:
    svc = r"SYSTEM\CurrentControlSet\Services"
    keys = {
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"): {"Teams": "teams.exe", "FalconProgram": r"C:\Program Files\Falcon\falcon.exe"},
        ("HKU", SID + r"\Software\Microsoft\Windows\CurrentVersion\Run"): {"sync": r"C:\Users\ama\s.vbs"},
        ("HKLM", PL + "\\" + SID): {"ProfileImagePath": r"C:\Users\ama"},
        ("HKLM", svc + r"\Spooler"): {"Type": 16, "Start": 2, "ImagePath": "spoolsv.exe"},
        ("HKLM", svc + r"\Manual"): {"Type": 16, "Start": 3, "ImagePath": "m.exe"},
        ("HKLM", svc + r"\disk"): {"Type": 1, "Start": 0, "ImagePath": "disk.sys"},
        ("HKLM", svc + r"\FalconWorker"): {"Type": 16, "Start": 2, "ImagePath": "python.exe -m worker_client"},
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\7z"): {"DisplayName": "7-Zip", "DisplayVersion": "24.09"},
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\kb"): {"DisplayName": "An update", "SystemComponent": 1},
        ("HKU", SID + r"\Software\Microsoft\Windows\CurrentVersion\Uninstall\z"): {"DisplayName": "Zoom", "DisplayVersion": "6.0"},
        ("HKLM", r"SYSTEM\CurrentControlSet\Services\LanmanServer\Shares"): {"Payroll": ["CSCFlags=0", "Path=C:\\Finance\\Payroll", "Type=0"]},
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows Defender"): {"DisableAntiSpyware": 1},
        ("HKLM", r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\PublicProfile"): {"EnableFirewall": 0},
        ("HKLM", r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\DomainProfile"): {"EnableFirewall": 1},
    }
    subs = {("HKLM", PL): ["S-1-5-18", SID], ("HKU", ""): [SID], ("HKLM", svc): ["Spooler", "Manual", "disk", "FalconWorker"],
            ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"): ["7z", "kb"],
            ("HKU", SID + r"\Software\Microsoft\Windows\CurrentVersion\Uninstall"): ["z"]}
    return Reg(keys, subs)


def test_the_worker_reads_what_starts_by_itself_and_what_is_installed_leaving_falcon_out(tmp_path):
    reg = _reg()
    startup_dir = tmp_path / "Startup"
    startup_dir.mkdir()
    (startup_dir / "copy.bat").write_text("x")
    (startup_dir / "desktop.ini").write_text("x")
    got = ms.startup_entries(reg, [{"kind": "startup", "user": "ama", "path": str(startup_dir)}])
    assert got == ["ama: Run: sync = C:\\Users\\ama\\s.vbs", "ama: Startup folder: copy.bat", "the machine: Run: Teams = teams.exe"]
    assert ms.services(reg) == ["Spooler = spoolsv.exe"]                         # not the manual one, not a driver, not Falcon's own
    assert ms.programs(reg) == ["7-Zip 24.09", "Zoom 6.0"]
    assert ms.shares(reg) == ["Payroll = C:\\Finance\\Payroll"]
    assert ms.defender(reg) == {"realtime_off": True, "firewall_off_domain": False, "firewall_off_public": True}


def test_a_persons_own_places_are_summed_from_the_watchers_record_and_the_rest_walked(tmp_path):
    docs = tmp_path / "ama" / "Documents"
    temp = tmp_path / "elsewhere" / "Temp"                                    # a Temp moved outside the watched folders: walked
    for d in (docs, temp):
        d.mkdir(parents=True)
    (temp / "a.tmp").write_bytes(b"x" * 1000)
    (temp / "sub").mkdir()
    (temp / "sub" / "b.tmp").write_bytes(b"x" * 500)
    state = Snapshot(tmp_path / "index-state.db")
    state.upsert([(str(docs / "budget.xlsx"), 4000, 1, "h"), (str(docs / "q" / "notes.docx"), 6000, 1, "h2"), (str(tmp_path / "other.txt"), 9, 1, None)])
    state.set_baselined()
    places = [{"kind": "documents", "user": "ama", "path": str(docs)}, {"kind": "temp", "user": "ama", "path": str(temp)}]
    got = {p["kind"]: p for p in ms.place_sizes(places, [], str(tmp_path / "nowin"), lambda: False, [str(tmp_path / "ama")], str(tmp_path / "index-state.db"))}
    assert got["documents"] == {"kind": "documents", "user": "ama", "path": str(docs), "bytes": 10000, "files": 2, "partial": False, "from": "index"}
    assert got["temp"]["bytes"] == 1500 and got["temp"]["files"] == 2 and got["temp"]["from"] == "walk"
    state.close()
    # someone is back: the walk stops and says it was cut short; what the index can say is still said
    busy = {p["kind"]: p for p in ms.place_sizes(places, [], str(tmp_path / "nowin"), lambda: True, [str(tmp_path / "ama")], str(tmp_path / "index-state.db"))}
    assert busy["temp"]["partial"] and busy["documents"]["from"] == "index"


async def test_the_picture_is_sent_by_the_engine_call_and_a_failure_is_quiet():
    sent: list[tuple[str, dict]] = []

    async def call(t: str, p: dict) -> dict:
        sent.append((t, p))
        return {}

    snaps = ms.Snapshots(call, taker=lambda: {"admins": ["PC\\a"]})
    assert await snaps.send() and sent[0][0] == "detective.snapshot" and sent[0][1]["snapshot"] == {"admins": ["PC\\a"]}

    async def away(t: str, p: dict) -> dict:
        raise ConnectionError("away")

    assert not await ms.Snapshots(away, taker=lambda: {"admins": []}).send()
    assert not await ms.Snapshots(call, taker=dict).send()                         # nothing could be read: nothing sent


@pytest.mark.skipif(sys.platform != "win32", reason="reads this Windows machine")
def test_this_machine_can_be_pictured():
    got = ms.take(busy=lambda: True)                                                 # (no walk: the test does not time a folder walk)
    assert {"drives", "admins", "accounts", "services", "programs", "defender"} <= set(got)
    assert got["admins"] and all("\\" in a for a in got["admins"])
    assert len(json.dumps(got)) < 512 * 1024


# --- the Engine keeps the last picture and feeds Detective ------------------------------------------------------------

@requires_db
async def test_the_engine_compares_each_picture_with_the_last_and_detective_hears_what_changed(engine, org, connect):
    from engine import detective

    w1 = await connect("cid-w1")
    t = 1_763_000_000.0
    assert (await w1.ok("detective.snapshot", {"at": t, "snapshot": _pic()}))["changes"] == 0          # the first is the baseline
    assert (await w1.ok("detective.snapshot", {"at": t + 10, "snapshot": _pic()}))["changes"] == 0
    now = _pic(admins=[*_pic()["admins"], "PC\\ama"], defender={"realtime_off": True, "firewall_off_domain": False, "firewall_off_public": False})
    assert (await w1.ok("detective.snapshot", {"at": t + 20, "snapshot": now}))["changes"] == 2
    assert (await w1.ok("detective.snapshot", {"at": t + 5, "snapshot": _pic()}))["changes"] == 0      # an older picture arriving late is not compared
    row = await engine.db.detective.snapshot(org["w1_pc"])
    assert "PC\\ama" in row["data"]["admins"]                                                          # ... and does not replace the newer one
    for _ in range(50):
        m = await detective.memory(org["w1_pc"])
        said = [x for x in (m.since(0, "system") if m else [])]
        if len(said) >= 2:
            break
        await asyncio.sleep(0.05)
    assert sorted(x.info["change"] for x in said) == ["admin_added", "protection_off"]
    assert await w1.err("detective.snapshot", {"snapshot": {"nothing": 1}}) == "invalid"
    assert await w1.err("detective.snapshot", {"snapshot": {"tasks": ["x" * 1000] * 1000}}) == "invalid"   # too big to be a picture
