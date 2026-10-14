"""Task, tried live: the Admin proposes with the real local model, the person's PC does the work, only the Admin completes it."""
from __future__ import annotations

import asyncio
import contextlib
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAG = str(int(time.time()))


def when(**kw) -> str:
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


async def run(d, check, say, wait_for) -> None:
    from live_drill import connect

    say("Task drill: the Admin (ADM-01) gives WS-D1 tasks; the person's PC is a real Worker")
    await d.worker_account("WS-D1")
    await d.worker_account("WS-D2")
    work = d.folder("WS-D1", "tasks")
    for child in work.iterdir():
        child.unlink() if child.is_file() else None
    d.start_worker("WS-D1", [work])
    d.start_worker("WS-D2", [d.folder("WS-D2", "tasks")])
    check("the person's PC is online", await d.online("WS-D1", "WS-D2"))
    admin, su = d.admin, d.su
    me = d.state["workers"]["WS-D1"]
    person = await connect({**d.engine_cfg, "client_id": me["client_id"], "client_key": me["client_key"]})
    pushes: list[tuple[str, dict]] = []
    admin_pushes: list[tuple[str, dict]] = []

    async def mine(t, p):
        pushes.append((t, p))

    async def theirs(t, p):
        admin_pushes.append((t, p))

    person.on_push(mine)
    admin.on_push(theirs)
    assignee = me["account_id"]

    # --- T1: proposing with the real model ------------------------------------------------------------------------------
    started = time.monotonic()
    prop = await admin.call("task.propose", {"description": f"Write the quarterly summary into summary-{TAG}.txt by tomorrow evening.",
                                             "assignee_account_id": assignee})
    took = time.monotonic() - started
    check("T1  the local model is up", bool(prop["llm_available"]), "the Engine says the model is not available: set FALCON_LLM_MODEL_PATH")
    names = [i.get("name") for i in prop["items"]]
    check(f"T1  it finds the file named in the description ({took:.0f}s)", any(n and f"summary-{TAG}" in n for n in names), str(prop["items"]))
    check("T1  and a deadline phrase is read, not guessed", bool(prop["final_deadline"] or prop["soft_deadline"] or prop["flags"]), str(prop))
    item = next((i for i in prop["items"] if i.get("name") and f"summary-{TAG}" in i["name"]), None)
    check("T1  a file to be written is a Create item", bool(item and item["intent"] == "create"), str(item))

    # --- T2: committing it ---------------------------------------------------------------------------------------------------
    items = [{"target_type": "file", "intent": "create", "name": f"summary-{TAG}.txt", "path": str(work)},
             {"target_type": "program", "intent": "used_with_file", "name": "python", "linked_item_index": 0}]
    res = await admin.call("task.create", {"assignee_account_id": assignee, "description": f"Write summary-{TAG}.txt", "verification_mode": "stack",
                                           "items": items, "soft_deadline_at": when(minutes=30), "final_deadline_at": when(hours=1)})
    tid = res["task"]["id"]
    check("T2  the assigner commits it", res["task"]["status"] == "active" and len(res["task"]["items"]) == 2)
    check("T2  the person is told, and sees it in their list",
          await wait_for(lambda: any(t == "task.assigned" for t, _ in pushes), 10)
          and tid in [t["id"] for t in (await person.call("task.list"))["tasks"]])
    other = await admin.call("task.list")
    check("T2  the assigner lists it too", tid in [t["id"] for t in other["tasks"]])
    try:
        await su.call("task.get", {"task_id": tid})
        saw = True
    except Exception:                                              # noqa: BLE001
        saw = False
    check("T2  the Super User can read it (always visible upward)", saw)

    # --- T3: doing it -----------------------------------------------------------------------------------------------------------
    await person.call("task.start", {"task_id": tid})
    check("T3  the assigner is told it has started", await wait_for(lambda: any(t == "task.started" for t, _ in admin_pushes), 10))
    target = work / f"summary-{TAG}.txt"
    target.write_text("Q3 summary\n", encoding="utf-8")

    async def stack_status():
        return [i["status"] for i in (await admin.call("task.stack", {"task_id": tid}))["items"]]

    ok = await wait_for(lambda: _first_passed(stack_status), 40)
    check("T3  the file appearing where it was asked passes its check (found by the real watcher)", ok, str(await stack_status()))

    holder = await asyncio.to_thread(subprocess.Popen, [sys.executable, "-c", f"import time; f=open(r'{target}','a'); time.sleep(120)"])
    try:
        ok = await wait_for(lambda: _all_passed(stack_status), 60)
        check("T3  a program running with that file open passes its check (a real process, seen by the Worker)", ok, str(await stack_status()))
    finally:
        holder.kill()
    check("T3  both checks passing does NOT complete the task", (await admin.call("task.get", {"task_id": tid}))["task"]["status"] == "in_progress")

    # --- T4: only the assigner closes it --------------------------------------------------------------------------------------------
    try:
        await person.call("task.verify", {"task_id": tid, "outcome": "complete"})
        refused = False
    except Exception:                                              # noqa: BLE001
        refused = True
    check("T4  the person cannot mark their own task complete", refused)
    await admin.call("task.verify", {"task_id": tid, "outcome": "incomplete"})
    check("T4  'incomplete' sends it back to the person", await wait_for(lambda: any(t == "task.incomplete" for t, _ in pushes), 10))
    await admin.call("task.verify", {"task_id": tid, "outcome": "complete"})
    check("T4  'complete' by the assigner closes it, and tells the person", await wait_for(lambda: any(t == "task.completed" for t, _ in pushes), 10))
    done = (await admin.call("task.get", {"task_id": tid}))["task"]
    check("T4  and it is recorded as completed by manual verification", done["status"] == "completed" and done["manual_verification"]["outcome"] == "complete")

    # --- T5: a deadline reaching ---------------------------------------------------------------------------------------------------
    quick = await admin.call("task.create", {"assignee_account_id": assignee, "description": "quick one", "verification_mode": "none",
                                             "confirm_none": True, "soft_deadline_at": when(seconds=4), "final_deadline_at": when(seconds=8)})
    ok = await wait_for(lambda: sum(1 for t, p in pushes if t == "task.deadline" and p.get("task_id") == quick["task"]["id"]) >= 2, 25)
    check("T5  the soft and the final deadline each reach the person, in real time", ok, str([p for t, p in pushes if t == "task.deadline"]))
    check("T5  and the assigner", sum(1 for t, p in admin_pushes if t == "task.deadline" and p.get("task_id") == quick["task"]["id"]) >= 2)

    # --- T6: a task about a file that exists --------------------------------------------------------------------------------------------
    existing = work / f"budget-{TAG}.txt"
    existing.write_text("v1\n", encoding="utf-8")
    seen = await wait_for(lambda: _indexed(admin, f"budget-{TAG}.txt"), 40)
    check("T6  the file index sees an existing file on the person's PC", seen)
    found = (await admin.call("index.search", {"query": f"budget-{TAG}"}))
    fid = next((f["id"] for f in found["results"] if f["filename"] == f"budget-{TAG}.txt"), None)
    if fid:
        upd = await admin.call("task.create", {"assignee_account_id": assignee, "description": f"update budget-{TAG}.txt", "verification_mode": "stack",
                                               "items": [{"target_type": "file", "intent": "update", "name": f"budget-{TAG}.txt", "file_index_id": fid}]})
        await person.call("task.start", {"task_id": upd["task"]["id"]})
        existing.write_text("v2, edited as asked\n", encoding="utf-8")
        ok = await wait_for(lambda: _first_passed_for(admin, upd["task"]["id"]), 40)
        check("T6  editing an existing file passes an Update check", ok)
    else:
        check("T6  the existing file can be searched for to bind an Update", False, str(found)[:200])

    # --- T7: a name collision is surfaced, never overwritten silently ----------------------------------------------------------------------
    try:
        await admin.call("task.create", {"assignee_account_id": assignee, "description": "write budget again", "verification_mode": "stack",
                                         "items": [{"target_type": "file", "intent": "create", "name": f"budget-{TAG}.txt"}]})
        said = False
    except Exception as exc:                                       # noqa: BLE001
        said = "collision" in str(exc) or "conflict" in str(exc)
    check("T7  asking for a file that already exists is refused until the assigner decides (new name or path)", said)

    # --- T8: scope -------------------------------------------------------------------------------------------------------------------------------
    try:
        await person.call("task.create", {"assignee_account_id": assignee, "description": "x", "verification_mode": "none", "confirm_none": True})
        blocked = False
    except Exception:                                              # noqa: BLE001
        blocked = True
    check("T8  a person cannot give tasks", blocked)

    # --- T9: the Super User gives a department a task -----------------------------------------------------------------------------------------
    tree = await su.call("hierarchy.tree")
    dept = next(x for x in tree["departments"] if any(a["hostname"] == "ADM-01" for a in x["admins"]))
    dt = await su.call("task.dept_create", {"department_id": dept["department_id"], "title": f"Hand in the Q3 figures {TAG}", "deadline_at": when(hours=2)})
    dtid = dt["task"]["id"]
    check("T9  a department task is announced to the department's Admin", await wait_for(lambda: any(t == "task.dept_assigned" for t, _ in admin_pushes), 10))
    await admin.call("task.dept_mark", {"task_id": dtid, "state": "seen"})
    await admin.call("task.dept_mark", {"task_id": dtid, "state": "ongoing"})
    await admin.call("task.dept_mark", {"task_id": dtid, "state": "done"})
    got = await su.call("task.dept_get", {"task_id": dtid})
    check("T9  the Admin marks seen, ongoing, done (a mark is not completion)", got["task"]["standing"] != "complete", str(got["task"].get("standing")))
    await su.call("task.dept_complete", {"task_id": dtid})
    got = await su.call("task.dept_get", {"task_id": dtid})
    check("T9  only the Super User completes it", got["task"]["standing"] == "complete", str(got["task"].get("standing")))
    with contextlib.suppress(Exception):
        await person.close()


async def _first_passed(stack_status) -> bool:
    return (await stack_status())[0] == "passed"


async def _all_passed(stack_status) -> bool:
    return all(s == "passed" for s in await stack_status())


async def _first_passed_for(admin, task_id: int) -> bool:
    items = (await admin.call("task.stack", {"task_id": task_id}))["items"]
    return bool(items) and items[0]["status"] == "passed"


async def _indexed(admin, name: str) -> bool:
    found = await admin.call("index.search", {"query": name.rsplit(".", 1)[0]})
    return any(f["filename"] == name for f in found["results"])


_ = asyncio
_ = Path
