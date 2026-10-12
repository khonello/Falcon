"""The session window: entering a machine to look at it or to use it, the picture, and the console's mouse and keyboard (WP9)."""

from __future__ import annotations

import asyncio

from tests.conftest import requires_db

pytestmark = requires_db

PNG_B64 = "iVBORw0KGgo="          # a few bytes: the Engine passes pictures on, it does not decode them


async def test_entering_to_look_leaves_the_person_working_and_the_picture_goes_to_the_viewer_only(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await w1.drain_pushes()

    entered = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True, "mode": "see"})
    assert entered["session"]["view_mode"] == "see"
    pushes = await w1.drain_pushes()
    kinds = w1.push_types(pushes)
    assert "session.viewing" in kinds and "session.blocked" not in kinds                      # the person is told, not locked out
    sid = entered["session"]["session_id"]

    assert await a1.err("session.input", {"session_id": sid, "events": [{"t": "move", "x": 0.5, "y": 0.5}]}) == "conflict"      # only looking
    started = await a1.ok("session.screen", {"session_id": sid, "action": "start", "width": 1000, "fps": 3})
    assert started["streaming"] and started["mode"] == "see" and started["fps"] == 3 and started["seconds_left"] > 0
    start = next(p for p in await w1.drain_pushes() if p.type == "screen.start").payload
    assert start["session_id"] == sid and start["width"] == 1000 and start["mode"] == "see"

    await a1.drain_pushes()
    reply = await w1.ok("session.frame", {"session_id": sid, "w": 1000, "h": 560, "screen_w": 1920, "screen_h": 1080, "png_b64": PNG_B64})
    assert reply == {"keep": True}
    frame = next(p for p in await a1.drain_pushes() if p.type == "session.frame").payload
    assert frame["session_id"] == sid and frame["png_b64"] == PNG_B64 and frame["screen_w"] == 1920 and frame["seq"] == 1
    other = await connect("cid-w2")
    assert (await other.ok("session.frame", {"session_id": sid, "png_b64": PNG_B64})) == {"keep": False}                      # not that machine's stream
    assert await w1.err("session.frame", {"session_id": sid, "png_b64": 5}) == "invalid"

    # control: the person is locked out and told who is working on their machine; the viewer's input reaches the machine
    assert (await a1.ok("session.control", {"session_id": sid, "mode": "control"}))["mode"] == "control"
    kinds = w1.push_types(await w1.drain_pushes())
    assert "session.blocked" in kinds and "screen.mode" in kinds
    events = [{"t": "move", "x": 0.25, "y": 0.75}, {"t": "down", "button": "left", "x": 0.25, "y": 0.75}, {"t": "up", "button": "left", "x": 0.25, "y": 0.75},
              {"t": "key", "down": True, "vk": 65}, {"t": "text", "text": "hi"}, {"t": "wheel", "delta": -120}]
    assert (await a1.ok("session.input", {"session_id": sid, "events": events}))["sent"] == 6
    got = next(p for p in await w1.drain_pushes() if p.type == "screen.input").payload
    assert got["session_id"] == sid and got["events"] == events
    assert await a1.err("session.input", {"session_id": sid, "events": []}) == "invalid"
    assert await a1.err("session.input", {"session_id": sid, "events": [{"t": "format-c"}]}) == "invalid"
    assert await a1.err("session.input", {"session_id": sid, "events": [{"t": "move"}] * 201}) == "invalid"
    assert await a1.err("session.control", {"session_id": sid, "mode": "root"}) == "invalid"
    back = await a1.ok("session.control", {"session_id": sid, "mode": "see"})
    assert back["mode"] == "see" and "session.viewing" in w1.push_types(await w1.drain_pushes())

    # stopping tells the machine, and its next picture is refused
    assert (await a1.ok("session.screen", {"session_id": sid, "action": "stop"}))["streaming"] is False
    assert "screen.stop" in w1.push_types(await w1.drain_pushes())
    assert await w1.ok("session.frame", {"session_id": sid, "png_b64": PNG_B64}) == {"keep": False}
    kinds = {e["action_type"] for e in (await a1.ok("audit.events", {"kinds": ["session"]}))["events"]}
    assert {"session.screen_started", "session.screen_stopped", "session.mode_changed"} <= kinds


async def test_the_picture_ends_with_the_session_or_a_dropped_connection_and_is_only_for_who_entered(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    entered = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})                  # no mode: the person is locked out, as before
    assert entered["session"]["view_mode"] == "control" and "session.blocked" in w1.push_types(await w1.drain_pushes())
    sid = entered["session"]["session_id"]
    assert await su.err("session.screen", {"session_id": sid, "action": "start"}) == "not_found"          # someone else's session
    assert await w1.err("session.screen", {"session_id": sid, "action": "start"}) == "forbidden"          # a Worker cannot look at anyone
    assert await a1.err("session.screen", {"session_id": 9999, "action": "start"}) == "not_found"

    await a1.ok("session.screen", {"session_id": sid, "action": "start"})
    await w1.drain_pushes()
    await a1.ok("hierarchy.end_session", {"session_id": sid})
    kinds = w1.push_types(await w1.drain_pushes())
    assert "screen.stop" in kinds and "session.released" in kinds
    assert await w1.ok("session.frame", {"session_id": sid, "png_b64": PNG_B64}) == {"keep": False}
    assert await a1.err("session.screen", {"session_id": sid, "action": "start"}) == "not_found"          # it is over

    again = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True, "mode": "see"})
    sid2 = again["session"]["session_id"]
    await a1.ok("session.screen", {"session_id": sid2, "action": "start"})
    await w1.drain_pushes()
    await a1.close()                                                                                   # the viewer goes: the machine is told to stop
    for _ in range(40):
        if "screen.stop" in w1.push_types(await w1.drain_pushes()):
            break
        await asyncio.sleep(0.05)
    else:
        raise AssertionError("the machine was not told to stop")
    assert await w1.ok("session.frame", {"session_id": sid2, "png_b64": PNG_B64}) == {"keep": False}
