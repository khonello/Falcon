"""Detective's matcher, kept apart from the Engine's loop (the user, 12 Nov 2026): in its own process, so however long it thinks, the Engine keeps answering
sign-ins, pushes and sessions, and if it ever falls over the Engine does not.

This file is that process. It imports only `common.detective` (no Engine, no database, no event loop) and is run as a script by `engine/detective/host.py`:
it reads one request at a time from stdin and writes one reply to stdout, each a 4-byte length and a pickle. `Brain` is the same thing in-process, for
`FALCON_DETECTIVE_PROCESS=0` and for the host's own use; both answer with `CaseView`s, plain snapshots of a case, never the live case.

What the matcher asks of the rest of the system (does a task cover this file? how familiar is this drive? what did a reviewer say is fine?) comes with
each event, for that event's machine (`feed`'s `ctx`), so the process holds nothing it must ask the Engine for.
"""

from __future__ import annotations

import pickle
import struct
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

if __package__ in (None, ""):                                          # run as a script: the repository (or the installed app) is two folders up
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.detective import Case, Context, Detective, Memory, Sig


@dataclass
class CaseView:
    """A case as it stands after an event, with what the Engine keeps of it: the row's values and the findings it has not been told are saved."""
    key: int                                   # the matcher's own name for the case (a case has no id until the Engine saves it)
    id: int | None
    pc: int
    level: str
    weight: float
    intent: str
    stage: tuple[int, str, str | None]
    not_yet: str | None
    behaviours: list[str]
    headline: str
    story: list[str]
    first_at: float
    last_at: float
    findings_from: int                         # `findings` are the case's findings from this place on
    findings: list[Any] = field(default_factory=list)
    total: int = 0


def view_of(c: Case, key: int = 0, start: int = 0) -> CaseView:
    """A case as the Engine keeps it, with its findings from `start` on."""
    return CaseView(key, c.id, c.pc, c.level, c.weight, c.intent, c.stage, c.not_yet(), sorted(c.behaviours), c.headline(), c.story(), c.first_at, c.last_at,
                    start, c.findings[start:], len(c.findings))


@dataclass
class UpdateView:
    case: CaseView
    created: bool
    raised: bool


class Brain:
    def __init__(self) -> None:
        self.tasks: dict[int, set[str]] = {}
        self.uses: dict[int, dict[str, int]] = {}           # machine -> drive (by where it is mounted, or its own name) -> times seen before
        self.rules: dict[int, list[Any]] = {}
        self.det = Detective(Context(task_things=lambda pc: self.tasks.get(pc, set()), known_device=lambda pc, dev: self.uses.get(pc, {}).get(dev, 0),
                                     rules=lambda pc: self.rules.get(pc, [])))
        self.keys: dict[int, int] = {}                      # id(case) -> key
        self.cases: dict[int, Case] = {}                    # key -> case
        self.saved: dict[int, int] = {}                     # key -> findings the Engine has saved
        self.next_key = 1

    # --- requests -----------------------------------------------------------------------------------------------

    def feed(self, sig: Sig, ctx: dict[str, Any] | None = None) -> tuple[list[UpdateView], bool]:
        if ctx is not None:
            self.tasks[sig.pc] = set(ctx.get("tasks") or ())
            self.uses[sig.pc] = dict(ctx.get("uses") or {})
            self.rules[sig.pc] = list(ctx.get("rules") or ())
        views: dict[int, CaseView] = {}
        out: list[UpdateView] = []
        for u in self.det.feed(sig):
            key = self._key(u.case)
            if key not in views:
                views[key] = self._view(key, u.case)
            out.append(UpdateView(views[key], u.created, u.raised))
        return out, self.has_drives(sig.pc)

    def remember(self, sigs: list[Sig]) -> dict[int, bool]:
        for s in sigs:
            self.det.remember(s)
        return {pc: self.has_drives(pc) for pc in {s.pc for s in sigs}}

    def know_drive(self, pc: int, device: str, at: float) -> bool:
        self.det.know_drive(pc, device, at)
        return self.has_drives(pc)

    def has_drives(self, pc: int) -> bool:
        m = self.det.mem.get(pc)
        return bool(m is not None and m.devices)

    def close(self, case_id: int) -> None:
        for key, c in list(self.cases.items()):
            if c.id == case_id:
                self._forget(key)
        self.det.close(case_id)

    def restore(self, case: Case) -> int:
        """A case read back from the database after a restart: it carries on, with every finding already saved."""
        self.det.cases.append(case)
        key = self._key(case)
        self.saved[key] = len(case.findings)
        return key

    def saved_as(self, key: int, case_id: int, n: int) -> None:
        c = self.cases.get(key)
        if c is not None:
            c.id = case_id
            self.saved[key] = max(self.saved.get(key, 0), n)

    def memory(self, pc: int) -> Memory | None:
        """A machine's memory, for the tests and for a person looking into Detective itself."""
        return self.det.mem.get(pc)

    def ping(self) -> str:
        return "pong"

    # --- inside -----------------------------------------------------------------------------------------------------

    def _key(self, case: Case) -> int:
        key = self.keys.get(id(case))
        if key is None:
            key = self.keys[id(case)] = self.next_key
            self.next_key += 1
            self.cases[key] = case
        if len(self.cases) > len(self.det.cases) + 200:
            live = {id(c) for c in self.det.cases}
            for k in [k for k, c in self.cases.items() if id(c) not in live]:
                self._forget(k)                              # cases the matcher has let go of
        return key

    def _forget(self, key: int) -> None:
        c = self.cases.pop(key, None)
        if c is not None:
            self.keys.pop(id(c), None)
        self.saved.pop(key, None)

    def _view(self, key: int, c: Case) -> CaseView:
        return view_of(c, key, self.saved.get(key, 0))

    def handle(self, op: str, args: tuple[Any, ...]) -> Any:
        if op.startswith("_") or not callable(getattr(self, op, None)) or op in ("handle",):
            raise ValueError(f"no such request: {op}")
        return getattr(self, op)(*args)


# --- the process -------------------------------------------------------------------------------------------------------

def read_frame(stream: BinaryIO) -> bytes | None:
    head = stream.read(4)
    if len(head) < 4:
        return None
    (n,) = struct.unpack(">I", head)
    body = stream.read(n)
    return body if len(body) == n else None


def write_frame(stream: BinaryIO, data: bytes) -> None:
    stream.write(struct.pack(">I", len(data)) + data)
    stream.flush()


def serve(inp: BinaryIO, out: BinaryIO) -> None:
    """Requests in, replies out, one at a time, until the Engine closes the pipe (which it also does by dying)."""
    brain = Brain()
    while (frame := read_frame(inp)) is not None:
        rid, op, args = pickle.loads(frame)                  # trusted: the only writer is the Engine that started this process
        try:
            reply = (rid, True, brain.handle(op, args))
        except Exception:                                    # noqa: BLE001 -- said back to the Engine, which logs it; the matcher carries on
            reply = (rid, False, traceback.format_exc(limit=8))
        write_frame(out, pickle.dumps(reply, protocol=pickle.HIGHEST_PROTOCOL))


if __name__ == "__main__":
    # The Engine reads these classes as `engine.detective.brain.*`: run as a script they live in __main__, so this module answers to that name too.
    sys.modules["engine.detective.brain"] = sys.modules["__main__"]
    for _cls in (CaseView, UpdateView):
        _cls.__module__ = "engine.detective.brain"
    _out = sys.stdout.buffer
    sys.stdout = sys.stderr                                 # anything printed goes to the log, never into the replies
    serve(sys.stdin.buffer, _out)
