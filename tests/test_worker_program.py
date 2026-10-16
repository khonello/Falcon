"""The small Falcon program on a Worker's machine: how it talks to the service, what the service tells it, and how emergencies and announcements reach it."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from common.connection import EngineConnection
from tests.conftest import key_for, requires_db
from tests.test_task_reminders import Handle
from tests.test_worker_client import _admin, _cfg, _start
from worker_client.config import WorkerConfig
from worker_client.localapp import LocalApp, read_info
from worker_client.program.__main__ import badge_of
from worker_client.program.client import LocalClient, ServiceAway
from worker_client.service import WorkerService


class Fake:
    """A service that answers like the real one, from memory."""

    def __init__(self) -> None:
        self.started, self.asked, self.acked = [], [], []

    async def app_view(self):
        return {"tasks": [{"id": 1, "title": "t", "started": False}], "announcements": [], "admins": [], "connected": True}

    async def app_start_task(self, task_id):
        self.started.append(task_id)

    async def app_ask(self, to):
        self.asked.append(to)

    async def app_ack(self, ids):
        self.acked.extend(ids)


async def _local(tmp_path: Path):
    fake = Fake()
    app = LocalApp(fake, tmp_path / "worker.json")
    await app.start()
    return fake, app, LocalClient(tmp_path / "worker.json")


async def test_the_program_asks_the_service_and_the_service_answers_only_with_the_token(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FALCON_NO_ACL", "1")
    fake, app, client = await _local(tmp_path)
    try:
        assert read_info(tmp_path / "worker.json")["port"] == app.port
        assert (await asyncio.to_thread(client.view))["tasks"][0]["id"] == 1
        await asyncio.to_thread(client.start_task, 1)
        await asyncio.to_thread(client.ask, 7)
        await asyncio.to_thread(client.ack, ["t1"])
        assert fake.started == [1] and fake.asked == [7] and fake.acked == ["t1"]
        # the wrong token, a missing token, nonsense: all refused, and the service carries on
        for line in (b'{"token": "nope", "op": "view"}\n', b'{"op": "view"}\n', b"not json\n", b"[]\n"):
            r, w = await asyncio.open_connection("127.0.0.1", app.port)
            w.write(line)
            await w.drain()
            reply = json.loads(await r.readline())
            assert reply["ok"] is False and "tasks" not in reply and "view" not in reply
            w.close()
        r, w = await asyncio.open_connection("127.0.0.1", app.port)
        w.write((json.dumps({"token": app.token, "op": "delete_everything"}) + "\n").encode())
        w.write((json.dumps({"token": app.token, "op": "ack", "ids": [1, 2]}) + "\n").encode())
        await w.drain()
        assert json.loads(await r.readline())["error"] == "unknown op"
        assert "text" in json.loads(await r.readline())["error"]
        w.close()
        assert app.refused >= 2 and (await asyncio.to_thread(client.view))["connected"] is True
    finally:
        await app.stop()
    assert read_info(tmp_path / "worker.json") is None                                   # gone with the service
    with pytest.raises(ServiceAway):
        await asyncio.to_thread(client.view)                                             # the program is told, not left hanging


def test_a_service_that_is_not_running_is_said_plainly(tmp_path: Path):
    with pytest.raises(ServiceAway, match="not running"):
        LocalClient(tmp_path / "nothing.json").view()


def test_the_badge_counts_what_is_new_to_this_person():
    view = {"tasks": [{"started": False}, {"started": True}], "announcements": [{"id": 3}, {"id": 5}]}
    assert badge_of(view, 0) == 3 and badge_of(view, 3) == 2 and badge_of(view, 5) == 1 and badge_of({}, 0) == 0


@requires_db
async def test_what_the_program_sees_is_what_concerns_this_person_and_says_when_it_is_not_live(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        tid = (await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "Collect the leave forms. Scan them.",
                                                "verification_mode": "none", "confirm_none": True}))["task"]["id"]
        await admin.call("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"], "title": "Month end",
                                           "body": "Close your books by Friday."})
        v = await svc.app_view()
        assert v["connected"] is True and v["held_by"] is None
        assert [t["id"] for t in v["tasks"]] == [tid] and v["tasks"][0]["title"] == "Collect the leave forms" and v["tasks"][0]["started"] is False
        assert [a["title"] for a in v["announcements"]] == ["Month end"] and v["announcements"][0]["kind"] == "announcement"
        assert [a["account_id"] for a in v["admins"]] == [org["a1"]]
        # a note for the corner when an announcement arrives
        await asyncio.sleep(0.3)
        assert any(t["kind"] == "announcement" and t["title"] == "Month end" for t in svc.toasts.values())
        await svc.app_ack(list(svc.toasts))
        assert svc.toasts == {}
        # asking an Admin for help goes through the service, as a ping
        await svc.app_ask(org["a1"])
        assert (await admin.call("assistance.ping_status"))["unaddressed"] == 1
        # the Engine goes away: the program is shown what was last known, and told it is not live
        await svc.conn.close()
        away = await svc.app_view()
        assert away["connected"] is False and away["tasks"][0]["id"] == tid and away["as_of"] == v["as_of"]
    finally:
        await admin.close()
        await svc.stop()


@requires_db
async def test_an_emergency_covers_the_screen_until_read_and_is_not_shown_again(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    shown = []

    async def fake_open(kind, spec):
        shown.append((kind, spec))
        return Handle({"seen": True})

    monkeypatch.setattr(spawn, "open_window", fake_open)
    monkeypatch.setenv("FALCON_NO_ACL", "1")
    cfg: WorkerConfig = _cfg(engine, tmp_path, "cid-w1", [])
    cfg.windows = True
    svc = WorkerService(cfg, native_watch=False)
    svc.executor.log_dir = tmp_path / "exec"
    svc.executor.log_dir.mkdir()
    monkeypatch.setattr(svc, "_start_program", lambda: asyncio.sleep(0))
    su = None
    try:
        await svc.start()
        su = EngineConnection("127.0.0.1", engine.port, client_id="cid-su", tls=False, derived_key=key_for("cid-su"))
        await su.connect()
        res = await su.call("alerts.create", {"type": "emergency", "audience": "all_users", "title": "Evacuate", "body": "Leave the building."})
        for _ in range(60):
            if any(k == "emergency" for k, _ in shown):
                break
            await asyncio.sleep(0.1)
        spec = next(s for k, s in shown if k == "emergency")
        assert spec["title"] == "Evacuate" and spec["text"] == "Leave the building."
        assert svc._dismissed == {res["alert_id"]}                                       # read: remembered here
        assert not svc.toasts                                                            # an emergency is a window, not a corner note
        before = len(shown)
        await svc._replay_emergencies()                                                   # a reconnect, or a restart
        assert len(shown) == before
        # a machine that was off when it was sent (nothing dismissed yet) is shown it as soon as it connects, if it is under a day old
        svc._dismissed.clear()
        await svc._replay_emergencies()
        assert len(shown) == before + 1
        # and it is in the list the program reads
        assert any(a["kind"] == "emergency" for a in (await svc.app_view())["announcements"])
    finally:
        if su is not None:
            await su.close()
        await svc.stop()


def test_the_program_draws_each_tab_and_says_when_it_is_not_live(tmp_path: Path):
    pytest.importorskip("PySide6")
    view = {"connected": False, "as_of": "2026-10-16T10:00:00+00:00",
            "tasks": [{"id": 1, "title": "Collect the signed leave forms", "description": "x", "from": "R. Mensah", "due": "2030-01-02T15:00:00+00:00", "started": False}],
            "announcements": [{"id": 5, "kind": "emergency", "title": "Server room closed", "body": "Saturday.", "from": "Super User", "at": "2026-10-16T09:00:00+00:00"}],
            "admins": [{"account_id": 7, "name": "R. Mensah"}], "toasts": []}
    for tab in ("today", "tasks", "announcements", "machine"):
        out = tmp_path / f"{tab}.png"
        done = subprocess.run([sys.executable, "-m", "worker_client.program", "--shot", str(out), "--view", json.dumps(view), "--tab", tab],
                              capture_output=True, text=True, timeout=60, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}, check=False)
        assert done.returncode == 0 and out.exists() and out.stat().st_size > 2000, done.stderr
        assert "QML:" not in done.stderr, done.stderr                                      # no QML error on any tab
