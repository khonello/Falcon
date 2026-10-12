"""The session window: a machine's screen in the console, and the console's mouse and keyboard back.

    hierarchy.traverse {pc_id, mode?: "see"|"control"}   (engine/hierarchy/traversal.py) -- enter a machine; `see` leaves the person working, `control` locks them out
    session.screen  {session_id, action: "start"|"stop", width?, fps?}    start or stop the picture of the machine; returns the time left
    session.control {session_id, mode: "see"|"control"}                   switch what the machine's person sees and whether input is applied
    session.input   {session_id, events: [...]}                           control mode only: mouse and keyboard, in positions as fractions of the screen
    session.frame   (the machine's Worker, to the Engine)                 one picture of the screen; passed on to the person looking, dropped if they are behind

Rules that keep this honest:
  * only the occupant of an active, entered session (a traversal) can look -- never an assisted-access session (bounded by what its person allowed) and never a native one;
  * the person at the machine is always told: a bar "X is viewing your screen" in `see`, "X is working on this PC" in `control`;
  * it stops with the session -- left, ended by a superior, expired -- and when either side's connection drops; `see` and `control` and every start/stop are audited
    (input itself is not: it would bury the trail; the mode and the time it lasted say what was possible);
  * frames are never queued: a console that cannot keep up gets the latest, not all of them.

Events in `session.input`: {"t": "move", "x": 0..1, "y": 0..1}, {"t": "down"|"up", "button": "left"|"right"|"middle", "x", "y"}, {"t": "wheel", "delta": int},
{"t": "key", "down": bool, "vk": int} or {"t": "text", "text": str}. At most 200 per call.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_account, require_role, str_field
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.connection import Connection
    from engine.server import Engine

log = logging.getLogger(__name__)

MAX_WIDTH = 1920
MAX_FPS = 5
MAX_EVENTS = 200
MAX_FRAME_B64 = 6 * 1024 * 1024


@dataclass
class Stream:
    session_id: int
    pc_id: int
    viewer_account_id: int
    viewer: Connection
    started_at: datetime
    frames: int = 0
    dropped: int = 0
    sending: bool = False


_streams: dict[int, Stream] = {}


def reset_state() -> None:
    _streams.clear()


def streaming(session_id: int) -> bool:
    return session_id in _streams


async def stop(engine: Engine, session_id: int, why: str = "stopped") -> None:
    """The picture ends (the viewer stopped it, the session ended, a connection dropped). The machine is told so it stops capturing."""
    stream = _streams.pop(session_id, None)
    if stream is None:
        return
    await engine.push_to_pc(stream.pc_id, "screen.stop", {"session_id": session_id, "why": why})
    seconds = int((datetime.now(timezone.utc) - stream.started_at).total_seconds())
    await engine.audit.record(None, "session.screen_stopped", target_type="session", target_id=session_id, pc_id=stream.pc_id,
                              detail={"why": why, "seconds": seconds, "frames": stream.frames, "dropped": stream.dropped})


async def on_disconnect(engine: Engine, conn: Connection) -> None:
    """Either end of a picture going away ends it."""
    for sid, s in list(_streams.items()):
        if s.viewer is conn or (conn.ctx.identity is not None and conn.ctx.identity.pc_id == s.pc_id):
            await stop(engine, sid, "a connection dropped")


async def _entered(ctx: Context, session_id: int) -> dict[str, Any]:
    """The viewer's own active traversal."""
    ident = require_role(ctx, "super_user", "admin")
    session = await ctx.engine.db.sessions.by_id(session_id)
    if session is None or session["ended_at"] is not None or session["occupant_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active session of yours")
    if session["occupied_via"] != "traversal":
        raise ProtocolError(ErrorCode.FORBIDDEN, "only a machine you entered can be looked at; an invited helper and a person's own session cannot")
    return session


async def _tell_machine(ctx: Context, session: dict[str, Any], mode: str) -> None:
    """What the person at the machine sees for this mode: who is looking (see) or who is working on their machine (control). Named the way the person names them."""
    pc = await ctx.engine.db.accounts.pc(session["pc_id"])
    owner = pc["bound_account_id"] if pc else None
    names = await ctx.engine.db.accounts.display_names_for(owner or ctx.identity.account_id, [session["occupant_account_id"]])
    view = {"session_id": session["id"], "pc_id": session["pc_id"], "occupant_account_id": session["occupant_account_id"],
            "occupant_name": names.get(session["occupant_account_id"]), "occupant_role": session["occupant_role"],
            "deadline_at": session["deadline_at"].isoformat() if session["deadline_at"] else None, "view_mode": mode}
    await ctx.engine.push_to_pc(session["pc_id"], "session.blocked" if mode == "control" else "session.viewing", view)
    await ctx.engine.push_to_pc(session["pc_id"], "screen.mode", {"session_id": session["id"], "mode": mode, "viewer": view["occupant_name"]})


def _left(session: dict[str, Any]) -> int | None:
    return max(0, int((session["deadline_at"] - datetime.now(timezone.utc)).total_seconds())) if session["deadline_at"] else None


@handler("session.screen")
async def screen(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"session_id", "action": "start"|"stop", "width"?: 1280, "fps"?: 2} -> {"mode", "seconds_left", "width", "fps"}."""
    session = await _entered(ctx, int_field(payload, "session_id"))
    action = str_field(payload, "action", choices=("start", "stop"))
    engine = ctx.engine
    if action == "stop":
        await stop(engine, session["id"], "stopped by the viewer")
        return {"streaming": False}
    if session["pc_id"] not in engine.online_pc_ids():
        raise ProtocolError(ErrorCode.UNAVAILABLE, "the machine is not reachable")
    width = max(320, min(int_field(payload, "width", required=False) or 1280, MAX_WIDTH))
    fps = max(1, min(int_field(payload, "fps", required=False) or 2, MAX_FPS))
    if session["id"] in _streams:
        await stop(engine, session["id"], "restarted")
    _streams[session["id"]] = Stream(session["id"], session["pc_id"], ctx.identity.account_id, ctx.connection, datetime.now(timezone.utc))
    await engine.push_to_pc(session["pc_id"], "screen.start", {"session_id": session["id"], "width": width, "fps": fps, "mode": session["view_mode"]})
    await engine.audit.record(ctx, "session.screen_started", target_type="session", target_id=session["id"], pc_id=session["pc_id"],
                              detail={"mode": session["view_mode"], "width": width, "fps": fps})
    return {"streaming": True, "mode": session["view_mode"], "seconds_left": _left(session), "width": width, "fps": fps}


@handler("session.control")
async def control(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"session_id", "mode": "see"|"control"} -- the person at the machine is told at once; `control` locks them out and applies your mouse and keyboard."""
    session = await _entered(ctx, int_field(payload, "session_id"))
    mode = str_field(payload, "mode", choices=("see", "control"))
    if mode != session["view_mode"]:
        await ctx.engine.db.sessions.set_view_mode(session["id"], mode)
        await ctx.engine.audit.record(ctx, "session.mode_changed", target_type="session", target_id=session["id"], pc_id=session["pc_id"], detail={"mode": mode})
        await _tell_machine(ctx, session, mode)
    return {"session_id": session["id"], "mode": mode, "seconds_left": _left(session)}


@handler("session.input")
async def send_input(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    session = await _entered(ctx, int_field(payload, "session_id"))
    if session["view_mode"] != "control":
        raise ProtocolError(ErrorCode.CONFLICT, "you are only looking; switch to see and control first")
    if session["id"] not in _streams:
        raise ProtocolError(ErrorCode.CONFLICT, "the picture is not on")
    events = payload.get("events")
    if not isinstance(events, list) or not events or len(events) > MAX_EVENTS or not all(isinstance(e, dict) and e.get("t") in
                                                                                         ("move", "down", "up", "wheel", "key", "text") for e in events):
        raise ProtocolError(ErrorCode.INVALID, f"events must be 1..{MAX_EVENTS} of move, down, up, wheel, key, text")
    await ctx.engine.push_to_pc(session["pc_id"], "screen.input", {"session_id": session["id"], "events": events})
    return {"sent": len(events)}


@handler("session.frame")
async def frame(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The machine's Worker: one picture. -> {"keep": bool} -- false tells it to stop capturing."""
    ident = require_account(ctx)
    session_id = int_field(payload, "session_id")
    stream = _streams.get(session_id)
    if stream is None or ident.pc_id != stream.pc_id:
        return {"keep": False}
    data = payload.get("png_b64")
    if not isinstance(data, str) or len(data) > MAX_FRAME_B64:
        raise ProtocolError(ErrorCode.INVALID, "png_b64 must be a picture within the size limit")
    stream.frames += 1
    if stream.sending:
        stream.dropped += 1                  # the console is still taking the last one: not queued, the next one replaces it
        return {"keep": True}
    stream.sending = True
    try:
        await stream.viewer.push("session.frame", {"session_id": session_id, "seq": stream.frames, "w": payload.get("w"), "h": payload.get("h"),
                                                    "screen_w": payload.get("screen_w"), "screen_h": payload.get("screen_h"), "png_b64": data})
    except Exception:  # noqa: BLE001 -- the viewer's connection went; the disconnect hook ends the stream
        log.debug("frame for session %s could not be delivered", session_id)
    finally:
        stream.sending = False
    return {"keep": True}
