"""The event tracker as its own program: programs starting and stopping, files opened, drives, network, sign-ins.

    python -m worker_client.tracker '<json: native>'

It holds the kernel trace (`etw.py`) and the Windows notifications (`ossignals.py`), and owns no Engine connection: what it
reports goes to the service over stdin/stdout (`worker_client.childproc`). If it dies the service starts it again, and what
the Engine wants watched is asked for again from the start, so nothing is left switched off.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from worker_client.childproc import Link
from worker_client.ossignals import OsSignals

log = logging.getLogger("worker_client.tracker")


async def run(cfg: dict) -> None:
    link = Link()
    signals = OsSignals(link.report)

    def show() -> dict:
        return {"native": bool(signals.native), "etw": signals.etw is not None,
                "programs_live": bool(signals.etw is not None and signals.etw.programs_live)}

    async def refresh(_args: dict) -> dict:
        await signals.refresh()
        link.status(**show())
        return {}

    async def status(_args: dict) -> dict:
        return show()

    link.command("refresh", refresh)
    link.command("status", status)
    served = asyncio.create_task(link.serve())      # reading first: an answer to a question can only arrive if someone reads
    await signals.start(native=bool(cfg.get("native", True)))
    try:
        await signals.refresh()                # ask what the Engine wants watched, now and not at the next push
    except Exception as exc:  # noqa: BLE001 -- the service is not connected yet: it sends "refresh" when it is
        log.info("not asked yet: %s", exc)
    link.status(**show())
    try:
        await served
    finally:
        await signals.stop()


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(run(json.loads(argv[0]) if argv else {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
