"""The Engine for a load run (scripts/load_run.py): the real Engine, settings from the environment, run until <out>/stop appears, measuring its own loop.

    python scripts/load_engine.py <out> [--profile]

A timer asks to be woken every 50 ms; how late it wakes is the loop lag (nothing should ever hold the loop for long). Written to <out>/lag.json.
With --profile the whole run is under cProfile: <out>/engine.prof, and the top 30 by own time in <out>/engine.top.txt.
"""

from __future__ import annotations

import asyncio
import cProfile
import io
import json
import logging
import pstats
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import dotenv

dotenv.load()

from engine.config import Settings
from engine.server import Engine


def count_queries() -> dict[str, int]:
    """Every statement that reaches PostgreSQL, counted by its text (cProfile counts each resume of a coroutine as a call, so it cannot)."""
    import asyncpg

    seen: dict[str, int] = {}
    for name in ("fetch", "fetchrow", "fetchval", "execute"):
        for cls in (asyncpg.connection.Connection,):                  # (the pool's calls end in these)
            real = getattr(cls, name)

            def counted(self, query, *args, _real=real, **kw):
                key = " ".join(str(query).split())[:110]
                seen[key] = seen.get(key, 0) + 1
                return _real(self, query, *args, **kw)

            setattr(cls, name, counted)
    return seen


async def run(out: Path) -> None:
    seen = count_queries()
    if "--no-event-reads" in sys.argv:                       # to measure what one event's reads save (engine/database.py, event_reads)
        import contextlib

        from engine.database import Database

        Database.event_reads = lambda self: contextlib.nullcontext()          # type: ignore[method-assign]
    if "--slow" in sys.argv:                                 # name every step that held the loop for 100 ms or more (asyncio's debug mode)
        loop = asyncio.get_running_loop()
        loop.set_debug(True)
        loop.slow_callback_duration = 0.1
        logging.getLogger("asyncio").setLevel(logging.WARNING)
    eng = Engine(Settings.from_env())
    await eng.start()
    started = sum(seen.values())
    lags: list[float] = []
    stop = out / "stop"
    while not stop.exists():
        t0 = time.perf_counter()
        await asyncio.sleep(0.05)
        lags.append(time.perf_counter() - t0 - 0.05)
    await eng.stop()
    total = sum(seen.values()) - started
    top = sorted(seen.items(), key=lambda kv: -kv[1])[:25]
    lines = [f"{total} statements while serving"] + [f"{n:7d}  {q}" for q, n in top]
    (out / "queries.txt").write_text("\n".join(lines), encoding="utf-8")
    settled = lags[200:]                                     # after the first 10 s: every machine has connected and signed in
    lags.sort()
    n = len(lags)
    (out / "lag.json").write_text(json.dumps({"p50": lags[n // 2], "p99": lags[int(n * .99)], "max": lags[-1], "over100": sum(x > 0.1 for x in lags), "n": n,
                                              "max_settled": max(settled or [0.0])}))


def main() -> None:
    out = Path(sys.argv[1])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("engine.audit").setLevel(logging.WARNING)
    if "--profile" in sys.argv:
        prof = cProfile.Profile()
        prof.enable()
        asyncio.run(run(out))
        prof.disable()
        prof.dump_stats(str(out / "engine.prof"))
        s = io.StringIO()
        pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(30)
        (out / "engine.top.txt").write_text(s.getvalue())
    else:
        asyncio.run(run(out))


if __name__ == "__main__":
    main()
