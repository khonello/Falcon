"""The spine: one stream of events that the whole system is built around.

Something happens -- a file is moved, a drive is plugged in, a task is assigned, a flow writes a file, a mark is made, a case is raised -- and it is an EVENT: from the OS
(reported by a Worker), from Falcon itself, or from a person at a console. Every feature hears the events it cares about, and no feature looks at the disk or at the others on
its own. The features are not independent programs that happen to read the same tables; they are stages that an event passes through, each adding what it knows.

    heat    first: whatever the event happened to is now HOT (common/heat.py), so everything after it, and any work still waiting, reaches it first
    guard   what is it? is it restricted, is it a copy of something marked, where is it allowed? (Resource, Restricted)
    act     what must be done about it? (Flow carries it, Task binds it, automations fire, issues are raised)
    judge   what does it mean? (Detective, reading everything the earlier stages found)
    tell    who must hear? (reports, notices)

The stages run in that order for every event, so a later stage can rely on what an earlier one decided: Flow acts only after Resource has judged the file, Detective judges only
after it knows whether a flow wrote the file and whether a task asked for it. What each stage finds is written onto the event as FACTS (`event.facts`), which travel with it:
the shared context is the event itself, not a table each feature queries for itself. A handler may publish a further event with the one it is handling as its `cause`; the chain
is kept, and one that gets longer than MAX_DEPTH is dropped (a loop between features must not run away).

A handler that fails is logged and the event carries on to the others: one feature's bug is never another feature's missed event. Nothing here waits: handlers run inline, in
order, as they always did; what changes is that the order is stated, and the knowledge is shared.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

STAGES = ("heat", "guard", "act", "judge", "tell")
MAX_DEPTH = 6
SLOW_SECONDS = 2.0                                   # a handler slower than this is said so in the log: a stage that holds the spine up is a worst case


@dataclass
class Event:
    kind: str                                         # "file.move", "os.signal", "task.assigned", "flow.synced", "mark.created", "case.raised" ...
    data: dict[str, Any]
    source: str = "system"                            # "os" (a Worker reported it), "system" (Falcon did it), "human" (a person at a console)
    pc: int | None = None
    at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    cause: Event | None = None
    depth: int = 0
    facts: dict[str, Any] = field(default_factory=dict)          # what the stages found out, for the stages after them

    def chain(self) -> list[str]:
        out, e = [], self
        while e is not None:
            out.append(e.kind)
            e = e.cause
        return list(reversed(out))


Handler = Callable[[Event], Awaitable[None]]


@dataclass
class _Sub:
    kinds: tuple[str, ...]
    fn: Handler
    stage: str
    name: str

    def hears(self, kind: str) -> bool:
        return any(k == kind or (k.endswith("*") and kind.startswith(k[:-1])) for k in self.kinds)


class Bus:
    def __init__(self) -> None:
        self._subs: dict[str, list[_Sub]] = {s: [] for s in STAGES}
        self.counts: dict[str, int] = defaultdict(int)       # events published, by kind
        self.failures: dict[str, int] = defaultdict(int)     # handler failures, by handler
        self.dropped = 0                                     # events not published because their chain was too long

    def on(self, kinds: str | tuple[str, ...], fn: Handler, *, stage: str = "act", name: str = "") -> None:
        """Hear these kinds of event at this stage. A kind ending in * hears everything that starts so ("file.*"). Within a stage, in the order registered."""
        if stage not in self._subs:
            raise ValueError(f"no stage {stage!r}: {STAGES}")
        self._subs[stage].append(_Sub((kinds,) if isinstance(kinds, str) else tuple(kinds), fn, stage, name or getattr(fn, "__name__", "handler")))

    async def publish(self, kind: str, data: dict[str, Any] | None = None, *, source: str = "system", pc: int | None = None,
                      cause: Event | None = None, facts: dict[str, Any] | None = None) -> Event | None:
        """Send an event through every stage, in order. Returns it (with its facts), or None if its chain was too long."""
        depth = 0 if cause is None else cause.depth + 1
        if depth > MAX_DEPTH:
            self.dropped += 1
            log.warning("event %s dropped: it is %d causes deep (%s)", kind, depth, " > ".join(cause.chain() if cause else []))
            return None
        event = Event(kind, data if data is not None else {}, source, pc, cause=cause, depth=depth, facts=facts if facts is not None else {})
        self.counts[kind] += 1
        for stage in STAGES:
            for sub in self._subs[stage]:
                if not sub.hears(kind):
                    continue
                began = time.monotonic()
                try:
                    await sub.fn(event)
                except Exception:
                    self.failures[sub.name] += 1
                    log.exception("handler %s failed on %s", sub.name, kind)
                took = time.monotonic() - began
                if took > SLOW_SECONDS:
                    log.warning("handler %s took %.1fs on %s", sub.name, took, kind)
        return event

    def handlers(self) -> dict[str, list[str]]:
        """Who listens at each stage (for the log, the docs and the tests)."""
        return {s: [f"{sub.name}:{','.join(sub.kinds)}" for sub in subs] for s, subs in self._subs.items()}
