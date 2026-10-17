"""The helper that lives on the signed-in person's desktop: captures the screen and applies input when the Worker is a service.

    python -m worker_client.helper          (started by the Worker; reads one JSON command per line on stdin, answers one JSON line on stdout)

    {"cmd": "ping"}                                 -> {"ok": true}
    {"cmd": "capture", "width": 1280}               -> {"ok": true, "sw", "sh", "w", "h", "png_b64"}  (or {"ok": false, "error"})
    {"cmd": "witness"}                              -> {"ok": true, "idle_s": seconds since input, "front": program in front, "title": its window title}
    {"cmd": "control", "on": true|false}            -> {"ok": true, "controlling": bool}   block the person's own input and take the console's
    {"cmd": "input", "events": [...]}               -> {"ok": true, "planned": n}          (only while controlling)
    {"cmd": "quit"}                                 -> exits

A service cannot see or touch the person's desktop (session 0); this small process can, because the service starts it on that desktop
(`worker_client.winsession`). It does nothing on its own and ends when its input closes -- when the service stops or restarts.
"""

from __future__ import annotations

import base64
import json
import sys

from worker_client.screenstream import RemoteInput, capture_png


def handle(msg: dict, remote: RemoteInput) -> dict:
    cmd = msg.get("cmd")
    if cmd == "ping":
        return {"ok": True}
    if cmd == "capture":
        try:
            sw, sh, w, h, png = capture_png(int(msg.get("width") or 1280))
        except Exception as exc:  # noqa: BLE001 -- no desktop right now (locked, signed out)
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "sw": sw, "sh": sh, "w": w, "h": h, "png_b64": base64.b64encode(png).decode("ascii")}
    if cmd == "witness":                                      # what Detective weighs a change by: was a person at the keyboard, and what was in front
        from worker_client import idle
        from worker_client.foreground import foreground

        try:
            front = foreground()
        except OSError:
            front = None
        return {"ok": True, "idle_s": idle.idle_seconds(), "front": (front or {}).get("program"), "title": (front or {}).get("title")}
    if cmd == "control":
        remote.control(bool(msg.get("on")))
        return {"ok": True, "controlling": remote.controlling}
    if cmd == "input":
        return {"ok": True, "planned": remote.apply(list(msg.get("events") or []))}
    return {"ok": False, "error": f"unknown command {cmd!r}"}


def main() -> int:
    remote = RemoteInput()
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                print(json.dumps({"ok": False, "error": "not JSON"}), flush=True)
                continue
            if msg.get("cmd") == "quit":
                break
            print(json.dumps(handle(msg, remote)), flush=True)
    finally:
        remote.stop()                  # lifts the block on the person's input however this ends
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
