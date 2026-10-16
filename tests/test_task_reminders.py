"""A task nobody started comes back: the reminder list, and the Worker service showing it, never more than one at a time, never for what is done."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import requires_db
from tests.test_worker_client import _admin, _start
from worker_client.reminders import INTERVALS, TaskReminders


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_a_dismissed_task_comes_back_later_each_time_less_often():
    clock = Clock()
    r = TaskReminders(clock)
    r.track(1)
    assert r.due() == []
    clock.t = INTERVALS[0] * 60
    assert r.due() == [1]
    r.track(1)                                              # dismissed again
    clock.t += INTERVALS[1] * 60 - 1
    assert r.due() == []
    clock.t += 1
    assert r.due() == [1]
    for _ in range(5):
        r.track(1)
    assert r._due[1] - clock.t == INTERVALS[-1] * 60        # hourly from then on, however long it takes


def test_a_task_found_waiting_keeps_its_place_and_a_started_one_is_forgotten():
    clock = Clock()
    r = TaskReminders(clock)
    r.track_new(1)
    clock.t = 60
    r.track_new(1)                                          # found again at the next refresh: not pushed back
    assert r._due[1] == 5 * 60
    r.track_new(2)
    r.keep_only({2})                                        # task 1 was started elsewhere, or taken away
    assert r.waiting() == [2]
    r.clear(2)
    assert r.waiting() == [] and r.due() == []


def test_the_longest_waiting_is_reminded_first_and_postponing_moves_it_back():
    clock = Clock()
    r = TaskReminders(clock)
    r.track(1, in_minutes=10)
    r.track(2, in_minutes=5)
    clock.t = 11 * 60
    assert r.due() == [2, 1]
    r.postpone(2, 5)
    assert r.due() == [1]


@requires_db
async def test_the_service_shows_a_waiting_task_again_until_it_is_started(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    shown = []
    answers = [{"later": True}, None, {"start": True}]          # closed, closed without answering, then started

    class Handle:
        def __init__(self, answer):
            self._answer = answer

        async def answer(self):
            return self._answer

        def close(self):
            pass

    async def fake_open(kind, spec):
        shown.append((kind, spec))
        return Handle(answers.pop(0) if kind == "task" and answers else {"seen": True})

    monkeypatch.setattr(spawn, "open_window", fake_open)
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        res = await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "tidy up the desk. then wave",
                                               "verification_mode": "none", "confirm_none": True})
        tid = res["task"]["id"]
        await svc._refresh_tasks()
        assert svc.reminders.waiting() == [tid]                 # found waiting
        await svc._show_task(tid)                                # its window opens when it is given; closed with "later"
        assert shown[0][0] == "task" and not shown[0][1].get("reminder")
        assert svc.reminders.waiting() == [tid]
        await svc._show_task(tid, reminder=True)                 # the reminder: closed without an answer
        assert shown[1][1]["reminder"] is True and shown[1][1]["times"] >= 1
        assert svc.reminders.waiting() == [tid]
        await svc._show_task(tid, reminder=True)                 # and at last started
        assert svc.reminders.waiting() == []
        assert (await admin.call("task.get", {"task_id": tid}))["task"]["started_at"]
        count = len(shown)
        await svc._show_task(tid, reminder=True)                 # started: nothing is shown again
        assert len(shown) == count
    finally:
        await admin.close()
        await svc.stop()


@requires_db
async def test_the_list_window_shows_what_is_assigned_and_start_works_from_it(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    shown = []

    class Handle:
        def __init__(self, answer):
            self._answer = answer

        async def answer(self):
            return self._answer

        def close(self):
            pass

    async def fake_open(kind, spec):
        shown.append((kind, spec))
        return Handle({"start": spec["tasks"][0]["id"]} if kind == "tasks" else {"seen": True})

    monkeypatch.setattr(spawn, "open_window", fake_open)
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        a = (await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "first thing",
                                              "verification_mode": "none", "confirm_none": True,
                                              "final_deadline_at": "2030-01-02T10:00:00+00:00"}))["task"]["id"]
        await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "second thing",
                                         "verification_mode": "none", "confirm_none": True})
        await svc.show_my_tasks()
        kind, spec = shown[0]
        assert kind == "tasks" and [t["title"] for t in spec["tasks"]] == ["first thing", "second thing"]      # soonest due first, undated last
        assert spec["tasks"][0]["id"] == a and spec["tasks"][0]["started"] is False
        assert (await admin.call("task.get", {"task_id": a}))["task"]["started_at"]                              # Start in the list started it
        assert a not in svc.reminders.waiting()
    finally:
        await admin.close()
        await svc.stop()
