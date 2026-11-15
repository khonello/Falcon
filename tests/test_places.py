"""Windows' own places (docs/design/proposals-core-features.md, item 2): read from each profile's registry, told to the Engine, given to every event
Detective reads. A Desktop in OneDrive or a Temp on another drive is only known from what the machine said; without it, the usual layout is assumed."""

from __future__ import annotations

import asyncio

from common.detective import Detective, Sig, filing, out_of_sight, where
from common.places import Place, Places, clean, guess
from tests.conftest import requires_db
from worker_client.places import PlacesReporter, expand, read

AMA = "S-1-5-21-111-222-333-1001"
KOJO = "S-1-5-21-111-222-333-1002"
ENTRA = "S-1-12-1-444-555-666-777"
PL = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
USF = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"


class FakeRegistry:
    def __init__(self, keys: dict[tuple[str, str], dict[str, str]], loaded: list[str]) -> None:
        self.keys = {(r, k.lower()): v for (r, k), v in keys.items()}
        self.loaded = loaded

    def values(self, root: str, key: str) -> dict[str, str]:
        return dict(self.keys.get((root, key.lower()), {}))

    def subkeys(self, root: str, key: str) -> list[str]:
        if root == "HKU" and key == "":
            return [*self.loaded, ".DEFAULT", "S-1-5-18"]
        if root == "HKLM" and key == PL:
            return ["S-1-5-18", "S-1-5-19", AMA, KOJO, ENTRA]
        return []


def _machine(extra: dict[tuple[str, str], dict[str, str]] | None = None) -> FakeRegistry:
    keys = {
        ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"): {"SystemRoot": r"C:\WINDOWS"},
        ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion"): {"ProgramFilesDir": r"C:\Program Files", "ProgramFilesDir (x86)": r"C:\Program Files (x86)"},
        ("HKLM", PL): {"ProgramData": r"%SystemDrive%\ProgramData"},
        ("HKLM", PL + "\\S-1-5-18"): {"ProfileImagePath": r"%systemroot%\system32\config\systemprofile"},
        ("HKLM", PL + "\\" + AMA): {"ProfileImagePath": r"C:\Users\ama"},
        ("HKLM", PL + "\\" + KOJO): {"ProfileImagePath": r"D:\Profiles\kojo"},
        ("HKLM", PL + "\\" + ENTRA): {"ProfileImagePath": r"C:\Users\efua.mensah"},
        ("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"): {"TEMP": r"%SystemRoot%\TEMP"},
        # Ama is signed in: her Desktop and Documents were moved into OneDrive, her Temp to another drive
        ("HKU", AMA + "\\" + USF): {"Desktop": r"%USERPROFILE%\OneDrive - Acme\Desktop", "Personal": r"%USERPROFILE%\OneDrive - Acme\Documents",
                                    "{374DE290-123F-4565-9164-39C4925E467B}": r"%USERPROFILE%\Downloads", "AppData": r"%USERPROFILE%\AppData\Roaming",
                                    "Local AppData": r"%USERPROFILE%\AppData\Local", "Startup": r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"},
        ("HKU", AMA + "\\Environment"): {"TEMP": r"E:\Scratch\ama", "OneDrive": r"C:\Users\ama\OneDrive - Acme"},
        # Efua (an Entra account) is signed in too, with nothing redirected and no Environment key
        ("HKU", ENTRA + "\\" + USF): {"Personal": r"%USERPROFILE%\Documents"},
    }
    keys.update(extra or {})
    return FakeRegistry(keys, loaded=[AMA, AMA + "_Classes", ENTRA])


def _by(places: list[dict], user: str) -> dict[str, dict]:
    return {p["kind"]: p for p in places if p["user"] == user}


# --- the usual layout ---------------------------------------------------------------------------------------------

def test_the_usual_layout_is_read_out_of_a_path_and_says_it_guessed():
    assert guess(r"C:\Users\ama\Downloads\x.pdf") == Place("downloads", "ama", True)
    assert guess(r"C:\Users\ama\AppData\Local\Temp\x.tmp").kind == "temp"            # the deepest: Temp, not AppData
    assert guess(r"C:\Users\ama\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\run.bat").kind == "startup"
    assert guess(r"C:\Users\ama\OneDrive - Acme\Documents\b.docx") == Place("documents", "ama", True)
    assert guess("C:/Users/Public/Documents/x.txt") == Place("documents", "", True)
    assert guess(r"D:\$Recycle.Bin\S-1-5-21\$R1.docx").kind == "recycle_bin"
    assert guess(r"C:\Windows\Temp\a").kind == "temp" and guess(r"C:\Windows\System32\a.dll").kind == "windows"
    assert guess(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\x.lnk").kind == "startup"
    assert guess(r"C:\Finance\Payroll\q3.xlsx") is None and guess(r"C:\Users\ama\Projects\a.py") is None and guess("") is None


def test_what_a_machine_said_wins_and_the_deepest_place_is_the_one():
    places = Places([{"kind": "documents", "path": r"D:\Work\Docs\\", "user": "ama"}, {"kind": "temp", "path": "E:/Scratch/ama", "user": "ama"},
                     {"kind": "appdata_local", "path": r"C:\Users\ama\AppData\Local", "user": "ama"},
                     {"kind": "temp", "path": r"C:\Users\ama\AppData\Local\Temp", "user": "ama"}])
    assert places.of(r"d:\work\docs\budget.xlsx") == Place("documents", "ama")
    assert places.of(r"E:\Scratch\ama\x\y.docx") == Place("temp", "ama")
    assert places.of(r"C:\Users\ama\AppData\Local\Temp\a.tmp").kind == "temp"
    assert places.of(r"C:\Users\ama\AppData\Local\Microsoft\a").kind == "appdata_local"
    assert places.of(r"D:\Work\Docsx\a.txt") is None                                  # a folder whose name only begins the same is not inside it
    assert places.of(r"C:\Users\kojo\Downloads\a.pdf") == Place("downloads", "kojo", True)   # not said: the usual layout
    assert places.entries()[0]["path"] in (r"D:\Work\Docs\\", "E:/Scratch/ama", r"C:\Users\ama\AppData\Local", r"C:\Users\ama\AppData\Local\Temp")


def test_what_a_worker_sends_is_kept_to_what_is_understood_and_bounded():
    got = clean([{"kind": "documents", "path": r"C:\Users\a\Documents", "user": "a"}, {"kind": "elsewhere", "path": r"C:\x"},
                 {"kind": "temp", "path": "C:"}, "nonsense", {"kind": "desktop", "path": r"C:\Users\a\Desktop", "user": "a" * 500}])
    assert [p["kind"] for p in got] == ["documents", "desktop"] and len(got[1]["user"]) == 120
    assert len(clean([{"kind": "temp", "path": rf"C:\t{i}"} for i in range(1000)])) == 400
    assert clean("not a list") == []


# --- the Worker reads them from each profile's own hive -------------------------------------------------------------

def test_each_persons_folders_are_read_from_their_own_hive_with_their_own_profile():
    places = read(_machine())
    ama = _by(places, "ama")
    assert ama["desktop"]["path"] == r"C:\Users\ama\OneDrive - Acme\Desktop" and not ama["desktop"]["guessed"]
    assert ama["documents"]["path"] == r"C:\Users\ama\OneDrive - Acme\Documents"
    assert ama["temp"]["path"] == r"E:\Scratch\ama" and ama["onedrive"]["path"] == r"C:\Users\ama\OneDrive - Acme"
    assert ama["startup"]["path"] == r"C:\Users\ama\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"    # %APPDATA% is hers, not the service's
    assert ama["pictures"]["guessed"] and ama["pictures"]["path"] == r"C:\Users\ama\Pictures"                          # the hive did not say
    # Kojo is not signed in: his profile is on D:, and the usual layout under it is assumed
    kojo = _by(places, "kojo")
    assert kojo["documents"] == {"kind": "documents", "path": r"D:\Profiles\kojo\Documents", "user": "kojo", "guessed": True}
    assert kojo["temp"]["path"] == r"D:\Profiles\kojo\AppData\Local\Temp"
    # an Entra (Azure AD) account is a person too; the service accounts are not
    efua = _by(places, "efua.mensah")
    assert efua["documents"]["path"] == r"C:\Users\efua.mensah\Documents" and not efua["documents"]["guessed"]
    assert efua["temp"]["path"] == r"C:\Users\efua.mensah\AppData\Local\Temp" and efua["temp"]["guessed"]
    assert "systemprofile" not in str(places)
    machine = _by(places, "")
    assert machine["windows"]["path"] == r"C:\WINDOWS" and machine["temp"]["path"] == r"C:\WINDOWS\TEMP"
    assert machine["programdata"]["path"] == r"C:\ProgramData" and machine["startup"]["path"] == r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    assert {p["path"] for p in places if p["kind"] == "program_files"} == {r"C:\Program Files", r"C:\Program Files (x86)"}


def test_a_name_that_cannot_be_expanded_is_not_taken_for_somewhere_else():
    assert expand(r"%USERPROFILE%\Docs", {"userprofile": r"C:\Users\a"}) == r"C:\Users\a\Docs"
    assert expand(r"%NOPE%\Docs", {}) == r"%NOPE%\Docs"
    odd = _machine({("HKU", AMA + "\\" + USF): {"Personal": r"%SOMETHING%\Documents"}})
    assert _by(read(odd), "ama")["documents"]["guessed"]                              # not "%SOMETHING%\Documents": the usual place instead


def test_startup_follows_a_moved_appdata():
    moved = _machine({("HKU", AMA + "\\" + USF): {"AppData": r"H:\Roaming\ama", "Startup": r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"}})
    ama = _by(read(moved), "ama")
    assert ama["appdata_roaming"]["path"] == r"H:\Roaming\ama"
    assert ama["startup"]["path"] == r"H:\Roaming\ama\Microsoft\Windows\Start Menu\Programs\Startup" and not ama["startup"]["guessed"]


async def test_the_worker_tells_them_at_every_connect_and_again_only_when_they_change():
    calls: list[tuple[str, dict]] = []

    async def call(type_: str, payload: dict) -> dict:
        calls.append((type_, payload))
        return {"accepted": len(payload["places"])}

    reg = _machine()
    rep = PlacesReporter(call, reg)
    assert await rep.send(force=True) and calls[-1][0] == "index.places"
    assert not await rep.send()                                                         # nothing changed: nothing said
    assert await rep.send(force=True)                                                   # a new connect: said again, a restarted Engine forgot
    reg.keys[("HKU", (AMA + "\\" + USF).lower())]["Desktop"] = r"D:\Desk"
    assert await rep.send() and _by(calls[-1][1]["places"], "ama")["desktop"]["path"] == r"D:\Desk"
    n = len(calls)

    async def away(type_: str, payload: dict) -> dict:
        raise ConnectionError("engine away")

    rep2 = PlacesReporter(away, reg)
    assert not await rep2.send(force=True) and rep2.sent is None and len(calls) == n    # told again next time, not lost
    rep.stop()


# --- Detective reads the real places ---------------------------------------------------------------------------------

def _sig(verb: str, path: str, old: str = "", **info) -> Sig:
    return Sig(1_000_000.0, 7, verb, path, old, thing="h-" + path[-12:], info=info)


def test_a_temp_on_another_drive_is_out_of_sight_only_when_the_machine_said_so():
    said = _sig("moved", r"E:\Scratch\ama\budget-2026.xlsx", r"C:\Users\ama\Documents\budget-2026.xlsx", place="temp", place_user="ama", was="documents", was_user="ama")
    unsaid = _sig("moved", r"E:\Scratch\ama\budget-2026.xlsx", r"C:\Users\ama\Documents\budget-2026.xlsx")
    assert out_of_sight(said) and not out_of_sight(said, old=True)
    assert not out_of_sight(unsaid)                                                      # E:\Scratch means nothing by its name
    det = Detective()
    graphs = [u.finding.graph for u in det.feed(said) if u.finding]
    assert "buried" in graphs
    case = next(c for c in det.cases if any(f.graph == "buried" for f in c.findings))
    buried = next(f for f in case.findings if f.graph == "buried")
    assert "moved into Temp" in buried.why[0]
    assert "buried" not in [u.finding.graph for u in Detective().feed(unsaid) if u.finding]


def test_filing_between_ones_own_places_is_housekeeping_wherever_they_live():
    # Downloads on C:, Documents redirected to D:\Work\Docs: the same person's own places, so filing, though the paths share no profile folder
    s = _sig("moved", r"D:\Work\Docs\invoice.pdf", r"C:\Users\ama\Downloads\invoice.pdf", place="documents", place_user="ama", was="downloads", was_user="ama")
    assert filing(s)
    assert not filing(_sig("moved", r"D:\Work\Docs\invoice.pdf", r"C:\Users\ama\Downloads\invoice.pdf"))       # unsaid: nothing ties them
    other = _sig("moved", r"D:\Work\Docs\invoice.pdf", r"C:\Users\kojo\Downloads\invoice.pdf", place="documents", place_user="ama", was="downloads", was_user="kojo")
    assert not filing(other)                                                              # somebody else's Downloads is not filing
    assert filing(_sig("moved", r"C:\Users\ama\Documents\a.pdf", r"C:\Users\ama\Downloads\a.pdf"))                 # the usual layout, as before


def test_a_place_the_machine_said_is_none_is_not_guessed_again():
    s = _sig("moved", r"C:\Users\ama\Downloads\x.docx", r"C:\Users\ama\Documents\x.docx", place="", was="")
    assert where(s) is None and where(s, old=True) is None
    assert where(_sig("moved", r"C:\Users\ama\Downloads\x.docx")) == Place("downloads", "ama", True)     # said nothing at all: the usual layout


# --- the Engine keeps them and gives them to Detective ---------------------------------------------------------------

@requires_db
async def test_a_machine_tells_its_places_an_admin_reads_them_and_detective_gets_them(engine, org, connect):
    from engine import detective, places

    w1 = await connect("cid-w1")
    told = [{"kind": "temp", "path": r"E:\Scratch\ama", "user": "ama"}, {"kind": "documents", "path": r"D:\Work\Docs", "user": "ama"},
            {"kind": "downloads", "path": r"C:\Users\ama\Downloads", "user": "ama", "guessed": True}]
    assert (await w1.ok("index.places", {"places": told + [{"kind": "nowhere", "path": "C:\\x"}]}))["accepted"] == 3
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    got = await a1.ok("index.places_get", {"pc_id": org["w1_pc"]})
    assert got["as_of"] and got["hostname"] == "FIN-01" and {p["path"] for p in got["places"]} == {p["path"] for p in told}
    assert await a2.err("index.places_get", {"pc_id": org["w1_pc"]}) == "forbidden"      # another department's machine
    assert await w1.err("index.places_get", {"pc_id": org["w1_pc"]}) == "forbidden"
    assert (await a1.ok("index.places_get", {"pc_id": org["w2_pc"]}))["as_of"] is None    # FIN-02 has said nothing
    assert places.place_of(org["w2_pc"], r"C:\Users\x\Downloads\a.pdf") == Place("downloads", "x", True)
    audit = await engine.db.audit.recent(action_prefix="index.places")
    assert audit and audit[0]["detail"]["places"] == 3
    # the same list again is not a new entry in the audit trail
    await w1.ok("index.places", {"places": told})
    assert len(await engine.db.audit.recent(action_prefix="index.places")) == len(audit)
    # a file event on that machine reaches Detective with its place
    await engine.file_index.ingest_event(org["w1_pc"], {"op": "move", "path": r"E:\Scratch\ama\budget.xlsx", "name": "budget.xlsx",
                                                         "old_path": r"D:\Work\Docs\budget.xlsx", "hash": "h-budget"})
    for _ in range(50):
        m = await detective.memory(org["w1_pc"])
        seen = [x for x in (m.since(0) if m else []) if x.path.endswith("budget.xlsx")]
        if seen:
            break
        await asyncio.sleep(0.05)
    assert seen and seen[-1].info["place"] == "temp" and seen[-1].info["place_user"] == "ama" and seen[-1].info["was"] == "documents"
