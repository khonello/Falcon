"""Show Detective working, live, against a running Engine -- without anyone doing anything wrong.

    environ-engine\\Scripts\\python.exe scripts\\detective_demo.py --engine 127.0.0.1:7400 --client-id <a demo Worker's id> --client-key <its key> --ca data/engine.crt \\
        [--scenario leak] [--speed 30] [--yes]
    environ-engine\\Scripts\\python.exe scripts\\detective_demo.py --list

It signs in as the Worker you name and sends the same messages a real Worker would send while a scripted person does what the scenario says (hides a
payroll file, packs fourteen files, plugs in a drive, copies the archive, erases the trail). Detective reads them exactly as it reads real ones, so the case
appears on the Detective page, with the story and the picture, as it happens. Nothing is touched on any machine: only messages are sent.

Use a machine set up for the demo. What is sent becomes part of that machine's history (the file index and event history keep everything), and the cases it
raises are real cases that people will be told about; they can be reviewed and dismissed like any other. The scenario is played at --speed times real time.
Scenarios that take days (the patient actor) cannot be played live; the others can.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from detective_scenarios import SCENARIOS, Scenario

from common.connection import EngineConnection
from common.detective import Sig

# what cannot be shown live: it spans days, or needs a person to have the files open (the Worker does not report an open as a file event)
NOT_LIVE = {"patient", "snooping"}
OPS = {"created": "create", "modified": "modify", "copied": "copy", "deleted": "delete", "moved": "move", "renamed": "move"}


def messages_for(s: Sig) -> list[tuple[str, dict]]:
    """What a real Worker would send for this: (message type, payload)."""
    if s.verb in OPS:
        event = {"op": OPS[s.verb], "path": s.path, "name": s.path.replace("\\", "/").rsplit("/", 1)[-1], "hash": s.thing or None, "witness": {"by": s.by if s.by != "falcon" else "unknown"}}
        if s.old:
            event["old_path"] = s.old
        if "restricted" in s.tags:
            event["resource_tag"] = "restricted"
        if s.program:
            event["witness"]["program"] = s.program
        return [("index.event", {"event": event})]
    if s.verb == "hid":
        event = {"op": "attrib", "path": s.path, "name": s.path.replace("\\", "/").rsplit("/", 1)[-1], "detail": {"hidden": True, "was_hidden": False},
                 "witness": {"by": s.by}}
        if "restricted" in s.tags:
            event["resource_tag"] = "restricted"
        return [("index.event", {"event": event})]
    if s.verb == "attached":
        return [("control.signal", {"type": "usb.inserted", "data": {"device": s.device, "path": s.device, **{k: v for k, v in s.info.items() if k in ("serial", "label")}}})]
    if s.verb == "detached":
        return [("control.signal", {"type": "usb.removed", "data": {"device": s.device, "path": s.device}})]
    if s.verb == "launched":
        return [("control.signal", {"type": "program.launched", "data": {"process": s.program}})]
    if s.verb == "uploaded":
        return [("control.signal", {"type": "network.upload", "data": {"process": s.program, **{k: v for k, v in s.info.items() if k in ("bytes", "to", "destinations", "seconds")}}})]
    if s.verb == "captured":
        return [("control.signal", {"type": "screen.captured", "data": {"kind": str(s.info.get("kind") or "screen"), "process": s.program}})]
    if s.verb == "cleared":
        return [("control.signal", {"type": "log.cleared", "data": {"log": str(s.info.get("log") or "Security")}})]
    return []


async def play_live(conn: EngineConnection, sc: Scenario, *, speed: float = 30.0, say=print) -> int:
    """Send the scenario to the Engine as a Worker would; returns how many messages went. A machine "going silent" ends the connection."""
    sent = 0
    previous = sc.sigs[0].at if sc.sigs else 0.0
    for s in sc.sigs:
        await asyncio.sleep(min(2.0, max(0.0, (s.at - previous) / speed)))
        previous = s.at
        if s.by == "falcon":
            continue
        if s.verb == "silent":
            say("  the machine stops reporting")
            await conn.close()
            return sent
        for type_, payload in messages_for(s):
            await conn.call(type_, payload)
            sent += 1
        say("  " + s.phrase())
    return sent


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", help="host:port")
    ap.add_argument("--client-id")
    ap.add_argument("--client-key")
    ap.add_argument("--ca")
    ap.add_argument("--plaintext", action="store_true")
    ap.add_argument("--scenario", default="leak", choices=sorted(set(SCENARIOS) - NOT_LIVE))
    ap.add_argument("--speed", type=float, default=30.0)
    ap.add_argument("--yes", action="store_true", help="yes, this machine is set up for the demo")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.list:
        for name in sorted(set(SCENARIOS) - NOT_LIVE):
            print(f"{name:24} {SCENARIOS[name]().says}")
        return 0
    if not (args.engine and args.client_id and args.client_key):
        ap.error("--engine, --client-id and --client-key are needed (sign in as the demo Worker)")
    if not args.yes:
        print("This sends a scripted person's activity as the Worker you named. It becomes part of that machine's history and raises a real case that people are\n"
              "told about. Run it on a machine set up for the demo, then pass --yes.")
        return 2
    host, _, port = args.engine.rpartition(":")
    conn = EngineConnection(host, int(port), client_id=args.client_id, tls=not args.plaintext, ca_cert=args.ca, derived_key=args.client_key)
    await conn.connect()
    sc = SCENARIOS[args.scenario]()
    print(f"{sc.name}: {sc.says}")
    n = await play_live(conn, sc, speed=args.speed)
    print(f"{n} messages sent. Open Detective in the console.")
    await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
