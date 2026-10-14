"""Restricted marks: a file or folder marked where it is, kept to the machine or to its place; copies become issues (WP3)."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


async def _index(client, *files):
    ids = []
    for path, digest in files:
        ids.append((await client.ok("index.event", {"event": {"op": "create", "path": path, "hash": digest}}))["file_index_id"])
    return ids


async def test_marking_where_it_is_and_what_the_mark_remembers(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    await _index(a1, ("C:/Finance/budget.xlsx", "B1"), ("C:/HR/Payroll/p1.csv", "P1"), ("C:/HR/Payroll/p2.csv", "P2"))

    tree = await a1.ok("marks.tree")
    assert tree["hostname"] == "FIN-ADM" and tree["truncated"] is False
    assert {f["path"]: (f["marked"], f["covered_by"]) for f in tree["files"]}["C:/Finance/budget.xlsx"] == (None, None)
    assert {f["path"]: f["files"] for f in tree["folders"]}["C:/HR/Payroll"] == 2
    assert await w1.err("marks.tree") == "forbidden"

    # nothing is moved; a file and a folder are marked in place, each with where it is allowed
    one = (await a1.ok("marks.create", {"paths": ["C:/Finance/budget.xlsx"], "keep": "machine"}))
    [budget] = one["marks"]
    assert budget["kind"] == "file" and budget["host"] == "FIN-ADM" and budget["keep_label"] == "Anywhere on the PC"
    assert (budget["files"], budget["versions"], budget["copies"]) == (1, 1, 0) and budget["by"]["you"] is True
    [payroll] = (await a1.ok("marks.create", {"paths": ["C:/HR/Payroll"], "keep": "path"}))["marks"]
    assert payroll["kind"] == "folder" and (payroll["files"], payroll["versions"]) == (2, 2) and payroll["name"] == "Payroll"
    tree = await a1.ok("marks.tree")
    state = {f["path"]: (f["marked"], f["covered_by"]) for f in tree["files"]}
    assert state["C:/Finance/budget.xlsx"] == (budget["id"], None) and state["C:/HR/Payroll/p1.csv"] == (None, payroll["id"])

    # what cannot be marked
    assert await a1.err("marks.create", {"paths": ["C:/nowhere/x.txt"], "keep": "path"}) == "not_found"
    assert await a1.err("marks.create", {"paths": ["C:/Finance/budget.xlsx"], "keep": "path"}) == "conflict"
    assert await a1.err("marks.create", {"paths": ["C:/HR/Payroll/p1.csv"], "keep": "path"}) == "conflict"          # covered by its folder
    assert await a1.err("marks.create", {"paths": [], "keep": "path"}) == "invalid"
    assert await a1.err("marks.create", {"paths": ["C:/Finance/budget.xlsx"], "keep": "everywhere"}) == "invalid"
    assert await w1.err("marks.create", {"paths": ["C:/x"], "keep": "path"}) == "forbidden"

    # versions: editing the original adds a hash; a file added to a marked folder later is covered too
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/Finance/budget.xlsx", "hash": "B2"}})
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/HR/Payroll/p3.csv", "hash": "P3"}})
    listing = {m["name"]: m for m in (await a1.ok("marks.list"))["marks"]}
    assert listing["budget.xlsx"]["versions"] == 2 and (listing["Payroll"]["files"], listing["Payroll"]["versions"]) == (3, 3)

    # nobody else reads it
    assert await a2.err("marks.get", {"mark_id": budget["id"]}) == "not_found"
    assert (await a2.ok("marks.list"))["marks"] == [] and await a2.err("marks.list", {"scope": "all"}) == "forbidden"


async def test_a_copy_where_the_mark_does_not_allow_it_is_an_issue_and_every_version_is_caught(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    await _index(a1, ("C:/Finance/budget.xlsx", "B1"), ("C:/HR/Payroll/p1.csv", "P1"))
    [budget] = (await a1.ok("marks.create", {"paths": ["C:/Finance/budget.xlsx"], "keep": "machine"}))["marks"]
    [payroll] = (await a1.ok("marks.create", {"paths": ["C:/HR/Payroll"], "keep": "path"}))["marks"]
    await su.drain_pushes()

    # kept to the machine: another place on the same PC is fine; another machine is not
    await a1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/me/Documents/budget-copy.xlsx", "hash": "B1"}})
    assert (await a1.ok("marks.get", {"mark_id": budget["id"]}))["copies"] == []
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Desktop/budget.xlsx", "hash": "B1"}})
    got = await a1.ok("marks.get", {"mark_id": budget["id"]})
    [copy] = got["copies"]
    assert copy["host"] == "FIN-01" and copy["file"] == "budget.xlsx" and copy["severity"] == "high" and copy["signed_in"]
    assert "issue.raised" in su.push_types(await su.drain_pushes())
    page = await a1.ok("issues.get", {"issue_id": copy["issue_id"]})
    assert page["issue"]["owner"]["you"] is True                                                         # the one who marked it
    assert "the machine FIN-ADM" in page["lead"] and any(f[0] == "Allowed only on" and f[1] == "FIN-ADM" for f in page["facts"])
    assert any(f[0] == "Marked by" for f in page["facts"]) and {o["key"] for o in page["options"]} >= {"delete", "allow"}

    # kept to its place: even the same PC, elsewhere, is a copy (medium: it did not leave the machine)
    await a1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/me/Desktop/p1.csv", "hash": "P1"}})
    [same_pc] = (await a1.ok("marks.get", {"mark_id": payroll["id"]}))["copies"]
    assert same_pc["host"] == "FIN-ADM" and same_pc["severity"] == "medium"

    # an older version of the original is still recognised after it is edited
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/Finance/budget.xlsx", "hash": "B2"}})
    await w2.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/kofi/budget-old.xlsx", "hash": "B1"}})
    await w2.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/kofi/budget-new.xlsx", "hash": "B2"}})
    assert sorted(c["file"] for c in (await a1.ok("marks.get", {"mark_id": budget["id"]}))["copies"]) == [
        "budget-new.xlsx", "budget-old.xlsx", "budget.xlsx"]

    # a copy that leaves the department is critical; and HR's own mark of something HR does not hold is not Finance's business
    await _index(a2, ("C:/HR/secret.docx", "S1"))
    [secret] = (await a2.ok("marks.create", {"paths": ["C:/HR/secret.docx"], "keep": "path"}))["marks"]
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/secret.docx", "hash": "S1"}})
    [leak] = (await a2.ok("marks.get", {"mark_id": secret["id"]}))["copies"]
    assert leak["severity"] == "critical" and leak["host"] == "FIN-01"
    assert (await a2.ok("issues.list"))["issues"] == []                       # the copy is in Finance's department: Finance's issue
    assert any(i["code"] == leak["code"] for i in (await a1.ok("issues.list"))["issues"])
    assert any(i["code"] == leak["code"] for i in (await su.ok("issues.list"))["issues"])

    # the Super User reads every mark; the list counts copies
    everything = await su.ok("marks.list", {"scope": "all"})
    assert everything["summary"]["marks"] == 3 and everything["summary"]["with_copies"] == 3 and everything["summary"]["copies"] == 5
    assert (await su.ok("marks.list"))["marks"] == []                          # "mine" is the Super User's own: none yet
    assert (await a1.ok("marks.list", {"scope": "department"}))["summary"]["marks"] == 2
    assert {e["action_type"] for e in (await su.ok("audit.events", {"kinds": ["violation"]}))["events"]} >= {"mark.created"}


async def test_an_existing_copy_is_found_at_marking_and_changing_where_it_is_allowed_says_what_it_does(engine, org, connect):
    a1 = await connect("cid-a1")
    w2 = await connect("cid-w2")
    await w2.ok("index.event", {"event": {"op": "create", "path": "C:/Users/kofi/plan.docx", "hash": "PLAN"}})
    await _index(a1, ("C:/Finance/plan.docx", "PLAN"))
    made = await a1.ok("marks.create", {"paths": ["C:/Finance/plan.docx"], "keep": "machine"})
    assert made["copies_found"] == 1 and made["marks"][0]["copies"] == 1                  # found at once, not only on the next event
    [mark] = made["marks"]

    await a1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/me/Documents/plan.docx", "hash": "PLAN"}})
    page = await a1.ok("marks.get", {"mark_id": mark["id"]})
    assert page["change"]["keep"] == "path" and page["change"]["effect"] == {"would_flag": 1, "would_clear": 0}
    assert (await a1.ok("marks.keep_effect", {"mark_id": mark["id"], "keep": "path"}))["effect"]["would_flag"] == 1
    assert await a1.err("marks.change_keep", {"mark_id": mark["id"], "keep": "machine"}) == "conflict"
    assert await a1.err("marks.keep_effect", {"mark_id": mark["id"], "keep": "x"}) == "invalid"

    tightened = await a1.ok("marks.change_keep", {"mark_id": mark["id"], "keep": "path"})
    assert tightened["flagged"] == 1 and tightened["mark"]["keep"] == "path" and tightened["mark"]["copies"] == 2
    loosened = await a1.ok("marks.change_keep", {"mark_id": mark["id"], "keep": "machine"})
    assert loosened["cleared"] == 1 and loosened["mark"]["copies"] == 1                       # the same-PC copy is allowed again
    resolved = (await a1.ok("marks.get", {"mark_id": mark["id"]}))["resolved_copies"]
    assert len(resolved) == 1 and resolved[0]["resolution"].startswith("Allowed now")

    # unmarking closes what is open and keeps the history; the file is no longer restricted
    out = await a1.ok("marks.unmark", {"mark_id": mark["id"]})
    assert out["copies_closed"] == 1 and (await a1.ok("marks.list"))["marks"] == []
    assert await a1.err("marks.unmark", {"mark_id": mark["id"]}) == "conflict"
    assert (await a1.ok("issues.list", {"type": "file"}))["summary"]["open"] == 0
    await w2.ok("index.event", {"event": {"op": "modify", "path": "C:/Users/kofi/plan.docx", "hash": "PLAN"}})
    assert (await a1.ok("issues.list", {"type": "file"}))["summary"]["open"] == 0           # not restricted any more
    assert await engine.db.pool.fetchval("SELECT count(*) FROM resource_marks WHERE unmarked_at IS NOT NULL") == 1


async def test_the_marked_original_moving_is_not_a_copy_but_a_copy_beside_it_still_is(engine, org, connect):
    """Found trying Restricted live: renaming a marked file, or dragging it into a sub-folder, raised a copy issue against the original itself."""
    a1 = await connect("cid-a1")
    await _index(a1, ("C:/Finance/memo.txt", "M1"), ("C:/Finance/Contracts/one.txt", "K1"))
    [memo] = (await a1.ok("marks.create", {"paths": ["C:/Finance/memo.txt"], "keep": "path"}))["marks"]
    [folder] = (await a1.ok("marks.create", {"paths": ["C:/Finance/Contracts"], "keep": "path"}))["marks"]

    async def open_copies() -> int:
        return len([i for i in (await a1.ok("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"])

    # renamed in place: a move event, with where it was
    await a1.ok("index.event", {"event": {"op": "move", "path": "C:/Finance/memo-final.txt", "old_path": "C:/Finance/memo.txt", "hash": "M1"}})
    assert await open_copies() == 0
    got = next(m for m in (await a1.ok("marks.list"))["marks"] if m["id"] == memo["id"])
    assert got["path"] == "C:/Finance/memo-final.txt" and got["name"] == "memo-final.txt"            # the mark went with it
    # dragged into a sub-folder: some moves arrive as a delete and then a create
    await a1.ok("index.event", {"event": {"op": "delete", "path": "C:/Finance/memo-final.txt"}})
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/Finance/Archive/memo-final.txt", "hash": "M1"}})
    assert await open_copies() == 0
    assert next(m for m in (await a1.ok("marks.list"))["marks"] if m["id"] == memo["id"])["path"] == "C:/Finance/Archive/memo-final.txt"
    # a COPY made while the original stays is still caught
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/Finance/copy-of-memo.txt", "hash": "M1"}})
    assert await open_copies() == 1
    # a folder renamed: the mark and what it marks follow it, and its files are not copies
    await a1.ok("index.event", {"event": {"op": "move", "path": "C:/Finance/Deals", "old_path": "C:/Finance/Contracts", "is_dir": True}})
    await a1.ok("index.event", {"event": {"op": "move", "path": "C:/Finance/Deals/one.txt", "old_path": "C:/Finance/Contracts/one.txt", "hash": "K1"}})
    assert await open_copies() == 1
    assert next(m for m in (await a1.ok("marks.list"))["marks"] if m["id"] == folder["id"])["path"] == "C:/Finance/Deals"


async def test_allowing_a_copy_allows_that_content_there_and_not_whatever_else_is_saved_at_that_path(engine, org, connect):
    """Found trying Restricted live: an allowance matched by path alone let any other restricted file saved at that path through."""
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await _index(a1, ("C:/Finance/a.txt", "A1"), ("C:/Finance/b.txt", "B1"))
    await a1.ok("marks.create", {"paths": ["C:/Finance/a.txt"], "keep": "path"})
    await a1.ok("marks.create", {"paths": ["C:/Finance/b.txt"], "keep": "path"})
    await w1.ok("index.event", {"event": {"op": "create", "path": "C:/Users/p/docs/x.txt", "hash": "A1"}})
    [issue] = [i for i in (await a1.ok("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"]
    await a1.ok("issues.act", {"issue_id": issue["id"], "key": "allow", "reason": "the clerk needs it"})
    await w1.ok("index.event", {"event": {"op": "create", "path": "C:/Users/p/docs/x.txt", "hash": "A1"}})
    assert [i for i in (await a1.ok("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"] == []          # allowed: not reported again
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/Users/p/docs/x.txt", "hash": "B1"}})                   # other restricted content, same path
    assert len([i for i in (await a1.ok("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"]) == 1
