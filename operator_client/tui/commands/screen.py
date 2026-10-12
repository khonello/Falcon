"""The session window from the shell: the picture of a machine you entered, and its mouse and keyboard.

    traverse <pc_id> force mode=see|control    (hierarchy.py) enter a machine, to look or to use it
    screen start <session_id> [width=1280] [fps=2]    ask for the picture
    screen shot <session_id> <file> [wait=5]          wait for a picture and save it as a PNG
    screen mode <session_id> see|control              switch between looking and using
    screen click <session_id> <x> <y>                 click at a place on the screen, as fractions (0.5 0.5 is the middle)
    screen type <session_id> <text...>                type text on the machine
    screen stop <session_id>                          stop the picture
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from operator_client.tui.shell import Args, ShellContext, UsageError, command


@command("screen", "start", "<session_id> [width=1280] [fps=2]", "Ask for the picture of the machine you entered")
async def screen_start(ctx: ShellContext, args: Args) -> str:
    payload = {"session_id": args.get_int(0, "session_id"), "action": "start"}
    for k in ("width", "fps"):
        if args.opt(k):
            payload[k] = args.opt_int(k)
    r = await ctx.call("session.screen", payload)
    return f"picture on ({r['mode']}), {r['fps']} a second, {r['seconds_left']}s left"


@command("screen", "stop", "<session_id>", "Stop the picture")
async def screen_stop(ctx: ShellContext, args: Args) -> str:
    sid = args.get_int(0, "session_id")
    await ctx.call("session.screen", {"session_id": sid, "action": "stop"})
    ctx.state.frames.pop(sid, None)
    return "picture off"


@command("screen", "shot", "<session_id> <file> [wait=5]", "Wait for a picture of the machine and save it as a PNG")
async def screen_shot(ctx: ShellContext, args: Args) -> str:
    sid, target = args.get_int(0, "session_id"), Path(args.get(1, "file"))
    ctx.state.frames.pop(sid, None)
    for _ in range(int((args.opt_int("wait") or 5) * 10)):
        frame = ctx.state.frames.get(sid)
        if frame:
            target.write_bytes(base64.b64decode(frame["png_b64"]))
            return f"saved {frame['w']}x{frame['h']} (screen {frame['screen_w']}x{frame['screen_h']}) to {target}"
        await asyncio.sleep(0.1)
    return "no picture arrived (is it on? screen start first)"


@command("screen", "mode", "<session_id> see|control", "Look only, or use the machine (its person is locked out)")
async def screen_mode(ctx: ShellContext, args: Args) -> str:
    mode = args.get(1, "see|control")
    if mode not in ("see", "control"):
        raise UsageError("see or control")
    r = await ctx.call("session.control", {"session_id": args.get_int(0, "session_id"), "mode": mode})
    return f"now {r['mode']}"


@command("screen", "click", "<session_id> <x> <y>", "Click at a place on the screen (fractions: 0.5 0.5 is the middle)")
async def screen_click(ctx: ShellContext, args: Args) -> str:
    x, y = float(args.get(1, "x")), float(args.get(2, "y"))
    base = {"x": x, "y": y, "button": "left"}
    await ctx.call("session.input", {"session_id": args.get_int(0, "session_id"), "events": [{"t": "move", "x": x, "y": y}, {"t": "down", **base}, {"t": "up", **base}]})
    return f"clicked at {x}, {y}"


@command("screen", "type", "<session_id> <text...>", "Type text on the machine")
async def screen_type(ctx: ShellContext, args: Args) -> str:
    await ctx.call("session.input", {"session_id": args.get_int(0, "session_id"), "events": [{"t": "text", "text": args.rest(1, "text")}]})
    return "typed"
