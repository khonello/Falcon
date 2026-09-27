"""`.env` loading (common/dotenv.py): settings come from a file, never the shell; the real environment still wins."""

from __future__ import annotations

import os

from common import dotenv


def test_the_file_is_read_as_a_person_writes_it():
    parsed = dotenv.parse("""
# a comment
FALCON_ENGINE_PORT=7400
export FALCON_DEBUG=1
FALCON_DATABASE_URL="postgresql://falcon:falcon@localhost:5432/falcon"
FALCON_LLM_MODEL='qwen3:0.6b'
FALCON_TLS_CERT=data/engine.crt   # the pinned certificate
# FALCON_DEV_PLAINTEXT=1
not a line
""")
    assert parsed == {"FALCON_ENGINE_PORT": "7400", "FALCON_DEBUG": "1",
                      "FALCON_DATABASE_URL": "postgresql://falcon:falcon@localhost:5432/falcon",
                      "FALCON_LLM_MODEL": "qwen3:0.6b", "FALCON_TLS_CERT": "data/engine.crt"}


def test_the_real_environment_wins(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("FALCON_X_ONE=from-file\nFALCON_X_TWO=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FALCON_X_ONE", "from-shell")
    monkeypatch.delenv("FALCON_X_TWO", raising=False)
    assert dotenv.load(env) == env
    assert os.environ["FALCON_X_ONE"] == "from-shell" and os.environ["FALCON_X_TWO"] == "from-file"
    monkeypatch.delenv("FALCON_X_TWO")


def test_no_file_is_not_an_error(tmp_path):
    assert dotenv.load(tmp_path / "missing.env") is None
