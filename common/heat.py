"""Hot and cold: what is being worked on now goes first (stdlib only).

Indexing, catching up, healing and the rest of the system's own background work could go through everything in whatever order it was found, and for a big machine or
a big organisation that would take a long time to reach the one file, program or machine somebody is using right now. So anything that happens to a thing marks it HOT,
and work that is waiting looks at the hot things first. Cold things are not neglected: they still get done, after, in the order they always did. Heat only decides who goes
first, never who is skipped.

    heat.touch(key)            something just happened to it: hot now
    heat.temperature(key)      1.0 just now, falling to 0 over `ttl` seconds
    heat.hottest(keys)         the same keys, hottest first; the cold ones keep their order
    heat.hot(key)              above `threshold`

A key is any string (a path, "pc:7", "flow:3"); paths are folded to one spelling. Touching a file also warms the folders above it a little, so the files beside the one in use are
the next to be reached and a walk finds the hot folder first. It is bounded (`cap` keys; the coldest are forgotten first), so a flood of events cannot make it grow.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")

MAX_ANCESTORS = 16


def fold(key: str) -> str:
    return key.replace("\\", "/").rstrip("/").casefold()


def parent(key: str) -> str:
    folded = fold(key)
    return folded.rsplit("/", 1)[0] if "/" in folded else ""


class Heat:
    def __init__(self, *, ttl: float = 900.0, cap: int = 50000, threshold: float = 0.05, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl, self.cap, self.threshold, self._clock = ttl, cap, threshold, clock
        self._at: OrderedDict[str, float] = OrderedDict()           # key -> (when it was last warm) scaled so that 1.0 is "just now"

    def touch(self, key: str, *, folder: bool = True) -> None:
        """Something happened to this: it is hot now. Its folder warms too (half as much), so its neighbours come next."""
        now = self._clock()
        k = fold(key)
        self._warm(k, now)
        if folder:
            # every folder above it, so a walk that goes hot-first dives straight to it instead of finishing the cold folders on the way (half as warm: it reads
            # as touched half a ttl ago)
            for _ in range(MAX_ANCESTORS):
                k = k.rsplit("/", 1)[0] if "/" in k else ""
                if not k:
                    break
                self._warm(k, now - self.ttl * 0.5)
        while len(self._at) > self.cap:
            self._at.popitem(last=False)

    def _warm(self, k: str, when: float) -> None:
        if self._at.get(k, -1e18) < when:
            self._at[k] = when
            self._at.move_to_end(k)

    def temperature(self, key: str) -> float:
        at = self._at.get(fold(key))
        if at is None:
            return 0.0
        return max(0.0, 1.0 - (self._clock() - at) / self.ttl)

    def hot(self, key: str) -> bool:
        return self.temperature(key) > self.threshold

    def hottest(self, keys: Iterable[T], key: Callable[[T], str] = str) -> list[T]:  # type: ignore[assignment]
        """The same things, hottest first; things equally cold stay in the order they came."""
        items = list(keys)
        return sorted(items, key=lambda x: -self.temperature(key(x)))

    def hot_keys(self, limit: int = 1000) -> list[str]:
        """The keys that are hot now, hottest first (at most `limit`)."""
        now = self._clock()
        live = [(1.0 - (now - at) / self.ttl, k) for k, at in self._at.items()]
        live = [(t, k) for t, k in live if t > self.threshold]
        live.sort(key=lambda tk: -tk[0])
        return [k for _, k in live[:limit]]

    def forget_cold(self) -> int:
        """Drop what has cooled right down (called now and then; the cap does the job in a flood)."""
        now = self._clock()
        cold = [k for k, at in self._at.items() if 1.0 - (now - at) / self.ttl <= 0.0]
        for k in cold:
            self._at.pop(k, None)
        return len(cold)

    def __len__(self) -> int:
        return len(self._at)
