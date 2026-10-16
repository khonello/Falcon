"""Reminders for a task its person has not started.

A task's window opens once, when it is given. If the person closes it, or never sees it (away from the desk, on a call), nothing else would ever
bring it back. So the Worker keeps a small list of tasks that are waiting to be started and shows each one's window again, a little later each
time, until the person starts it or it is no longer theirs to start. Never more than one at a time, never while a superior is using the machine,
and never for a task that is already started, finished or gone.

The list is rebuilt from the Engine at every connect (`task.list`), so a restart of the service or the machine forgets nothing.
"""

from __future__ import annotations

import time
from collections.abc import Callable

# minutes between a window being dismissed and the next reminder: soon, then less often, then hourly for as long as it takes
INTERVALS = (15, 30, 60)
FIRST_AFTER_CONNECT = 5          # a task found waiting at connect is mentioned five minutes later, not the instant the machine starts


class TaskReminders:
    def __init__(self, clock: Callable[[], float] = time.monotonic, intervals: tuple[float, ...] = INTERVALS) -> None:
        self._clock = clock
        self._intervals = tuple(m * 60 for m in intervals)
        self._due: dict[int, float] = {}
        self._count: dict[int, int] = {}

    def waiting(self) -> list[int]:
        return sorted(self._due)

    def track(self, task_id: int, *, in_minutes: float | None = None) -> None:
        """The task is waiting to be started: remind about it after the next interval (or `in_minutes`)."""
        n = self._count.get(task_id, 0)
        wait = in_minutes * 60 if in_minutes is not None else self._intervals[min(n, len(self._intervals) - 1)]
        self._due[task_id] = self._clock() + wait
        self._count[task_id] = n + 1

    def track_new(self, task_id: int, *, in_minutes: float = FIRST_AFTER_CONNECT) -> None:
        """A task found waiting (not one just dismissed): keep its place if it is already being reminded."""
        if task_id not in self._due:
            self._due[task_id] = self._clock() + in_minutes * 60
            self._count.setdefault(task_id, 0)

    def postpone(self, task_id: int, minutes: float = 5) -> None:
        if task_id in self._due:
            self._due[task_id] = self._clock() + minutes * 60

    def clear(self, task_id: int) -> None:
        self._due.pop(task_id, None)
        self._count.pop(task_id, None)

    def keep_only(self, task_ids: set[int]) -> None:
        for gone in set(self._due) - task_ids:
            self.clear(gone)

    def due(self) -> list[int]:
        """The tasks whose reminder time has come, the longest-waiting first."""
        now = self._clock()
        return sorted((t for t, at in self._due.items() if at <= now), key=lambda t: self._due[t])

    def times_reminded(self, task_id: int) -> int:
        return max(0, self._count.get(task_id, 0) - 1)
