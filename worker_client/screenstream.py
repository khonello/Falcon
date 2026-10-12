"""The picture of this machine for a superior who has entered it, and their mouse and keyboard.

The Engine starts it (`screen.start {session_id, width, fps, mode}`) only while someone has entered this machine and asked to look; it stops when they stop, the
session ends, or either connection drops (`screen.stop`, or `{"keep": false}` in reply to a frame). The person at the machine is always told by the Worker's own
window (a bar in `see`, the "working on this machine" cover in `control`) -- this module never hides that it is running.

Frames are the primary screen scaled to `width` and encoded as PNG (zlib, fast level; stdlib only, like the `screenshot` built-in), sent only when the picture
changed, at most `fps` a second, and never queued: a send that is slow simply makes the next frame later.

Input arrives as fractions of the screen (so the console's window size does not matter) and is applied with Windows `SendInput`. In `control` mode the person's
own keyboard and mouse are blocked with `BlockInput` so the two do not fight; Windows ends that block by itself if this process dies, and Ctrl+Alt+Del always
overrides it, so nobody is ever stranded. The block and every injected event are made by one dedicated thread, which is what Windows requires of them.

When the Worker runs as a Windows service, capture and input must run in the signed-in person's session (a helper), like the `screenshot` built-in; that arrives
with packaging.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import queue
import sys
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
Capture = Callable[[int], tuple[int, int, int, int, bytes]]

SEND_LEVEL = 1                 # zlib level: a screen of flat colours compresses well even when fast
MAX_FPS = 5
KEEPALIVE_SECONDS = 5.0        # an unchanged screen is still sent this often, so the console knows the picture is alive


def capture_png(width: int) -> tuple[int, int, int, int, bytes]:
    """(screen w, screen h, w, h, PNG bytes) of the primary screen at `width`."""
    from worker_client import screenshot

    sw, sh, w, h, rows = screenshot.capture(width)
    return sw, sh, w, h, screenshot.png(w, h, rows, SEND_LEVEL)


class ScreenStreamer:
    def __init__(self, report: Reporter, *, capture: Capture = capture_png) -> None:
        self.report = report
        self.capture = capture
        self._tasks: dict[int, asyncio.Task[None]] = {}

    @property
    def active(self) -> set[int]:
        return {sid for sid, t in self._tasks.items() if not t.done()}

    def start(self, session_id: int, width: int, fps: int) -> None:
        self.stop(session_id)
        self._tasks[session_id] = asyncio.create_task(self._loop(session_id, max(160, int(width)), max(1, min(int(fps), MAX_FPS))))

    def stop(self, session_id: int | None = None) -> None:
        for sid in [session_id] if session_id is not None else list(self._tasks):
            task = self._tasks.pop(sid, None)
            if task is not None:
                task.cancel()

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        self.stop()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _loop(self, session_id: int, width: int, fps: int) -> None:
        last_hash, last_sent, period = b"", 0.0, 1.0 / fps
        try:
            while True:
                began = time.monotonic()
                try:
                    sw, sh, w, h, png = await asyncio.to_thread(self.capture, width)
                except Exception as exc:  # noqa: BLE001 -- no desktop to capture (locked, or a service's empty one): say so once and stop
                    log.warning("the screen could not be captured: %s", exc)
                    return
                digest = hashlib.blake2b(png, digest_size=16).digest()
                if digest != last_hash or began - last_sent >= KEEPALIVE_SECONDS:
                    reply = await self.report("session.frame", {"session_id": session_id, "w": w, "h": h, "screen_w": sw, "screen_h": sh,
                                                                "png_b64": base64.b64encode(png).decode("ascii")})
                    last_hash, last_sent = digest, began
                    if not reply.get("keep", False):
                        return
                await asyncio.sleep(max(0.0, period - (time.monotonic() - began)))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- the connection went; the Engine ends the picture on its side too
            log.info("the screen stopped: %s", exc)
        finally:
            self._tasks.pop(session_id, None)


# --- the console's mouse and keyboard -----------------------------------------------------------------------------------------

MOUSE = {"move": 0x0001, "left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}
ABSOLUTE, WHEEL, KEYUP, UNICODE = 0x8000, 0x0800, 0x0002, 0x0004


def plan(events: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    """What `SendInput` should do for events from the console, as plain tuples (testable anywhere):
    ("mouse", flags, x65535, y65535, data) and ("key", vk, scan, flags). Anything malformed is dropped, never guessed."""
    out: list[tuple[Any, ...]] = []
    for e in events:
        try:
            t = e["t"]
            if t in ("move", "down", "up"):
                x, y = min(max(float(e["x"]), 0.0), 1.0), min(max(float(e["y"]), 0.0), 1.0)
                ax, ay = int(x * 65535), int(y * 65535)
                if t == "move":
                    out.append(("mouse", MOUSE["move"] | ABSOLUTE, ax, ay, 0))
                else:
                    button = MOUSE[e.get("button", "left")]
                    out.append(("mouse", MOUSE["move"] | ABSOLUTE | button[0 if t == "down" else 1], ax, ay, 0))
            elif t == "wheel":
                out.append(("mouse", WHEEL, 0, 0, max(-1200, min(int(e["delta"]), 1200))))
            elif t == "key":
                out.append(("key", int(e["vk"]) & 0xFF, 0, 0 if e.get("down", True) else KEYUP))
            elif t == "text":
                for ch in str(e["text"])[:200]:
                    out.append(("key", 0, ord(ch), UNICODE))
                    out.append(("key", 0, ord(ch), UNICODE | KEYUP))
        except (KeyError, TypeError, ValueError):
            continue
    return out


class RemoteInput:
    """Applies the console's input on one dedicated thread; `control(True)` also blocks the person's own input while it lasts."""

    def __init__(self) -> None:
        self._q: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self.controlling = False

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="falcon-remote-input", daemon=True)
            self._thread.start()
        return True

    def control(self, on: bool) -> None:
        self.controlling = bool(on) and self.start()
        self._q.put(("block", self.controlling))

    def apply(self, events: list[dict[str, Any]]) -> int:
        """Queue input for the thread; only while controlling. Returns how many actions were planned."""
        if not self.controlling:
            return 0
        steps = plan(events)
        if steps:
            self._q.put(("send", steps))
        return len(steps)

    def stop(self) -> None:
        self.controlling = False
        if self._thread is not None and self._thread.is_alive():
            self._q.put(("block", False))
            self._q.put(("quit", None))
            self._thread.join(2)

    def _run(self) -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_size_t)]

        class _U(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        blocked = False
        while True:
            kind, arg = self._q.get()
            if kind == "quit":
                break
            if kind == "block":
                if arg and not blocked:
                    blocked = bool(user32.BlockInput(True))
                elif not arg and blocked:
                    user32.BlockInput(False)
                    blocked = False
                continue
            for step in arg:
                inp = INPUT()
                if step[0] == "mouse":
                    inp.type = 0
                    inp.u.mi = MOUSEINPUT(step[2], step[3], step[4] & 0xFFFFFFFF, step[1], 0, 0)
                else:
                    inp.type = 1
                    inp.u.ki = KEYBDINPUT(step[1], step[2], step[3], 0, 0)
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if blocked:
            user32.BlockInput(False)
