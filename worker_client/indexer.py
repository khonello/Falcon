"""The indexer as its own program: the file watcher and the idle-time sweep, under the service.

    python -m worker_client.indexer '<json: roots, poll_seconds, hash_limit, idle_after, native>'

It owns no connection: what it reports goes to the service over stdin/stdout (`worker_client.childproc`), which sends it to the
Engine. It runs at low priority so a sweep never competes with the person's work, and it ends when the service's end closes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from worker_client.childproc import Link
from worker_client.watcher import Watcher

log = logging.getLogger("worker_client.indexer")


def lower_priority() -> None:
    try:
        import psutil

        me = psutil.Process()
        me.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 10)
    except Exception:
        log.debug("could not lower the priority", exc_info=True)


async def run(cfg: dict) -> None:
    link = Link()
    watcher = Watcher(cfg.get("roots") or [], link.report, poll_seconds=float(cfg.get("poll_seconds", 5.0)),
                      hash_limit=int(cfg.get("hash_limit", 64 << 20)), idle_after=float(cfg.get("idle_after", 300.0)),
                      native=bool(cfg.get("native", True)),
                      state_path=Path(cfg["state_path"]) if cfg.get("state_path") else None,
                      reconcile_seconds=float(cfg.get("reconcile_seconds", 1800.0)))

    def show() -> dict:
        return {"mode": watcher.mode, "events_reported": watcher.events_reported,
                "sweeps_completed": watcher.sweeps_completed}

    async def sweep(_args: dict) -> dict:
        n = await watcher.sweep()
        link.status(**show())
        return {"n": n}

    async def status(_args: dict) -> dict:
        return show()

    async def reconcile(_args: dict) -> dict:
        res = await watcher.reconcile()
        link.status(**show())
        return res

    link.command("reconcile", reconcile)
    link.command("sweep", sweep)
    link.command("status", status)
    served = asyncio.create_task(link.serve())
    await watcher.start()
    link.status(**show())

    async def tell() -> None:
        last: dict = {}
        while True:
            await asyncio.sleep(2)
            now = show()
            if now != last:
                link.status(**now)
                last = now

    teller = asyncio.create_task(tell())
    try:
        await served
    finally:
        teller.cancel()
        await watcher.stop()


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    lower_priority()
    asyncio.run(run(json.loads(argv[0]) if argv else {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
