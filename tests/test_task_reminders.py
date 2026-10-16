"""A task nobody started comes back: the reminder list, and the Worker service showing it, never more than one at a time, never for what is done."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import requires_db
from tests.test_worker_client import _admin, _start
from worker_client.reminders import FIRST_AFTER_CONNECT, INTERVALS, TaskReminders


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
    assert r._due[1] == FIRST_AFTER_CONNECT * 60
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


class Handle:
    def __init__(self, answer):
        self._answer = answer

    async def answer(self):
        return self._answer

    def close(self):
        pass


@requires_db
async def test_a_task_nobody_started_comes_back_as_a_quiet_note_never_a_window(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    shown = []
    answers = [{"later": True}]                                  # the task's own window, closed without starting

    async def fake_open(kind, spec):
        shown.append((kind, spec))
        return Handle(answers.pop(0) if answers else {"seen": True})

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
        assert [k for k, _ in shown] == ["task"] and svc.reminders.waiting() == [tid]
        await svc._remind(tid)                                   # the reminder: a note for the program, no window
        assert [k for k, _ in shown] == ["task"]
        assert list(svc.toasts) == [f"t{tid}"] and svc.toasts[f"t{tid}"]["text"] == "Still waiting to be started"
        assert svc.reminders.waiting() == [tid]                 # and it will come back again, later
        await svc.app_start_task(tid)                            # started from the program
        assert svc.reminders.waiting() == []
        assert (await admin.call("task.get", {"task_id": tid}))["task"]["started_at"]
        svc.toasts.clear()
        await svc._remind(tid)                                   # started: nothing more is said
        assert svc.toasts == {}
    finally:
        await admin.close()
        await svc.stop()


def test_reminders_are_spaced_to_be_unobtrusive():
    assert INTERVALS[0] >= 60 and INTERVALS[-1] >= 240          # not minutes apart: an hour at first, then hours
