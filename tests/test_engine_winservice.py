"""The Engine as a Windows service (engine/winservice.py, common/winsvc.py; 14 Nov 2026): installed, started, answering, stopped and removed, for real.
Needs Windows and an elevated prompt (it registers a real service), and the test database."""

from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import time

import pytest

from tests.conftest import TEST_DB_URL, requires_db

pytestmark = [requires_db, pytest.mark.skipif(sys.platform != "win32" or not (sys.platform == "win32" and ctypes.windll.shell32.IsUserAnAdmin()),
                                              reason="a real Windows service: Windows, elevated")]

NAME = "FalconEngineTest"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_the_engine_installs_runs_answers_and_removes_itself_as_a_windows_service(db, tmp_path):
    from engine import winservice
    from engine.tls import generate_self_signed

    state = tmp_path / "Falcon Engine"
    state.mkdir()
    cert, key = generate_self_signed("127.0.0.1,localhost", state)
    (state / "master.secret").write_text(os.urandom(32).hex(), encoding="ascii")
    port = _free_port()
    env = state / "falcon.env"
    env.write_text("\n".join(["FALCON_ENGINE_HOST=127.0.0.1", f"FALCON_ENGINE_PORT={port}", f"FALCON_DATABASE_URL={TEST_DB_URL}",
                              f"FALCON_TLS_CERT={cert.as_posix()}", f"FALCON_TLS_KEY={key.as_posix()}",
                              f"FALCON_SECRET_PATH={(state / 'master.secret').as_posix()}", "FALCON_GROQ_API_KEY=",
                              f"FALCON_LLM_MODEL_PATH={(state / 'no-model.gguf').as_posix()}", ""]), encoding="utf-8")

    def cli(*args: str) -> str:
        done = subprocess.run([sys.executable, "-m", "engine", "service", *args, "--name", NAME], capture_output=True, text=True, timeout=120, check=False)
        return (done.stdout + done.stderr).strip()

    cli("uninstall")
    try:
        assert "installed" in cli("install", "--env", str(env))
        assert winservice.command_line(NAME, str(env)).endswith(f'--env "{env.resolve()}"') or str(env.resolve()) in winservice.command_line(NAME, str(env))
        assert "running" in cli("start", "--env", str(env)), (state / "logs" / "engine.log").read_text(encoding="utf-8", errors="replace")[-2000:]
        end = time.monotonic() + 60
        while time.monotonic() < end:
            try:
                with socket.create_connection(("127.0.0.1", port), 1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail("the service never answered: " + (state / "logs" / "engine.log").read_text(encoding="utf-8", errors="replace")[-2000:])
        assert "Engine listening on" in (state / "logs" / "engine.log").read_text(encoding="utf-8", errors="replace")   # its log is beside its settings
        assert cli("status").endswith("running")
        assert "stopped" in cli("stop")
    finally:
        assert "removed" in cli("uninstall") or "not installed" in cli("status")
    assert cli("status").endswith("not installed")
