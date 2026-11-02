"""Private: only the people the owner names may open it, and Windows itself refuses everyone else (ENGINE-GAPS #3; engine/resource/private.py,
worker_client/privacy.py)."""

from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import requires_db

windows_only = pytest.mark.skipif(os.name != "nt", reason="Private is Windows' own permissions")


async def _private_mark(engine, org, a1, readers: list[int], allow_system: bool = True) -> dict:
    await engine.db.file_index.upsert(org["a1_pc"], "C:/Users/a1/Documents/pay.xlsx", "pay.xlsx", "hpay", None, None, "event")
    made = await a1.ok("marks.create", {"paths": ["C:/Users/a1/Documents/pay.xlsx"], "keep": "machine", "protection": "private",
                                        "readers": readers, "allow_system": allow_system})
    return made["marks"][0]


@requires_db
@pytest.mark.organisation
async def test_a_private_mark_tells_its_machine_who_may_open_it_and_hears_who_was_refused(engine, org, connect):
    for pc, who in ((org["a1_pc"], "FIN\\anna"), (org["w1_pc"], "FIN\\kofi")):
        await engine.db.accounts.set_windows_user(pc, who)
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    mark = await _private_mark(engine, org, a1, [org["w1"]], allow_system=False)
    assert mark["protection"] == "private" and {r["account_id"] for r in mark["readers"]} == {org["a1"], org["w1"]}
    order = next(p for p in await a1.drain_pushes() if p.type == "private.apply").payload
    assert order["readers"] == ["FIN\\anna", "FIN\\kofi"] and order["owner"] == "FIN\\anna" and order["allow_system"] is False

    # what the machine did is kept on the mark
    await a1.ok("private.applied", {"mark_id": mark["id"], "ok": True, "granted": ["FIN\\anna", "FIN\\kofi"]})
    assert (await engine.db.marks.get(mark["id"]))["applied"]["ok"] is True

    # a private item is not a restricted one: no flow is held at it, no copy of it is caught
    from engine.flow import guard

    assert await guard.blockers(engine, org["a1_pc"], "C:/Users/a1/Documents/pay.xlsx", "hpay") == []
    assert await engine.db.marks.active_with_hash("hpay") == []

    # Windows refused someone: noted on the mark, told to its owner, matched to the person when their Windows name is known
    said = await a1.ok("private.refused", {"path": "C:\\Users\\a1\\Documents\\pay.xlsx", "who": "FIN\\kofi", "process": "C:\\Windows\\explorer.exe",
                                           "at": "2026-11-02T10:00:00Z"})
    assert said["mark_id"] == mark["id"]
    told = next(p for p in await a1.drain_pushes() if p.type == "private.refused")
    assert told.payload["account_id"] == org["w1"]
    got = (await a1.ok("marks.get", {"mark_id": mark["id"]}))
    assert got["mark"]["refusals"][0]["who"] == "FIN\\kofi"

    # only the owner changes who is named; nobody can ask to be added
    assert await a2.err("marks.readers", {"mark_id": mark["id"], "readers": [org["a2"]]}) == "forbidden"
    changed = await a1.ok("marks.readers", {"mark_id": mark["id"], "readers": [], "allow_system": True})
    assert changed["readers"] == [org["a1"]] and changed["applied_now"] is True
    assert next(p for p in await a1.drain_pushes() if p.type == "private.apply").payload["readers"] == ["FIN\\anna"]

    # a machine that comes back is told again (applying is idempotent there); unmarking puts the permissions back
    from engine.resource import private

    await private.on_pc_online(engine, org["a1_pc"])
    assert "private.apply" in a1.push_types(await a1.drain_pushes())
    await a1.ok("marks.unmark", {"mark_id": mark["id"]})
    assert next(p for p in await a1.drain_pushes() if p.type == "private.lift").payload["mark_id"] == mark["id"]


@windows_only
def test_windows_permissions_are_set_for_the_people_named_and_put_back_exactly(tmp_path: Path):
    from worker_client.privacy import Privacy

    item = tmp_path / "pay.xlsx"
    item.write_text("salaries", encoding="utf-8")

    def acl() -> str:
        return subprocess.run(["icacls", str(item)], capture_output=True, text=True, check=False).stdout

    before = acl()
    p = Privacy(tmp_path / "state", audit=False)
    me = getpass.getuser()
    done = p.apply({"mark_id": 7, "path": str(item), "kind": "file", "owner": me, "readers": [me, "NoSuchPerson-Falcon-Test"], "allow_system": False})
    assert done["ok"] is True and done["granted"] == [me] and done["missing"] == ["NoSuchPerson-Falcon-Test"]
    now = acl()
    assert me.lower() in now.lower() and "(I)" not in now                       # only what was set here; nothing inherited
    assert "Users:" not in now and "Everyone" not in now
    assert item.read_text(encoding="utf-8") == "salaries"                      # the owner still opens it
    assert p.paths == {7: str(item)}
    assert p.lift(7, str(item)) is True
    assert acl() == before and p.paths == {}                                   # exactly as it was


@windows_only
def test_nothing_changes_when_nobody_named_is_known_here(tmp_path: Path):
    from worker_client.privacy import Privacy

    item = tmp_path / "x.txt"
    item.write_text("x", encoding="utf-8")
    before = subprocess.run(["icacls", str(item)], capture_output=True, text=True, check=False).stdout
    done = Privacy(tmp_path / "state", audit=False).apply({"mark_id": 8, "path": str(item), "owner": None, "readers": ["NoSuchPerson-Falcon-Test"]})
    assert done["ok"] is False and "nothing was changed" in done["error"]
    assert subprocess.run(["icacls", str(item)], capture_output=True, text=True, check=False).stdout == before


def test_a_refused_open_is_read_from_windows_security_log():
    from worker_client.privacy import parse_refusals

    xml = """<Events><Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><EventID>4656</EventID>
      <TimeCreated SystemTime='2026-11-02T10:00:01.5Z'/><EventRecordID>9001</EventRecordID></System><EventData>
      <Data Name='SubjectUserName'>kofi</Data><Data Name='SubjectDomainName'>FIN</Data>
      <Data Name='ObjectName'>C:\\Users\\a1\\Documents\\Payroll\\march.xlsx</Data><Data Name='ProcessName'>C:\\Windows\\explorer.exe</Data>
      </EventData></Event><Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System><EventID>4656</EventID>
      <EventRecordID>9002</EventRecordID></System><EventData><Data Name='ObjectName'>C:\\Other\\file.txt</Data></EventData></Event></Events>"""
    found, newest = parse_refusals(xml.replace("'", '"'), ["C:/Users/a1/Documents/Payroll"])
    assert newest == 9002
    assert found == [{"path": "C:\\Users\\a1\\Documents\\Payroll\\march.xlsx", "who": "FIN\\kofi", "process": "C:\\Windows\\explorer.exe",
                      "at": "2026-11-02T10:00:01.5Z"}]
