"""Local by default, Groq only as a fallback (the user, 4 Nov 2026; engine/llm.py). A small HTTP server stands in for Groq: no key means no question
ever leaves, and with a key only what the local model could not answer does."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from engine.config import Settings
from engine.llm import LocalLLM


class FakeGroq:
    def __init__(self) -> None:
        self.asked: list[dict] = []
        self.keys: list[str] = []
        self.status = 200
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.asked.append(body)
                outer.keys.append(self.headers.get("Authorization", ""))
                reply = json.dumps({"choices": [{"message": {"content": "YES"}}]}).encode()
                self.send_response(outer.status)
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

            def log_message(self, *_a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/openai/v1"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def groq():
    fake = FakeGroq()
    yield fake
    fake.close()


def _llm(groq: FakeGroq, key: str | None = "gsk-test", model_path: str | None = None) -> LocalLLM:
    return LocalLLM("llamacpp", model_path=model_path, fallback_key=key, fallback_endpoint=groq.url)


async def test_with_no_key_nothing_ever_leaves_the_machine(groq):
    llm = _llm(groq, key=None)
    assert llm.available is False and await llm.yes_no("Is it?", "text") is None
    assert groq.asked == [] and "Groq" not in llm.describe()
    assert Settings.groq_api_key is None                                              # the default


async def test_a_server_with_no_model_falls_back_and_says_so_once(groq):
    llm = _llm(groq)
    said: list[int] = []

    async def record() -> None:
        said.append(1)
    llm.on_fallback = record
    assert llm.local_available is False and llm.available is True
    assert await llm.yes_no("Is it?", "text") is True
    assert await llm.yes_no("And this?", "other") is True
    body = groq.asked[0]
    assert groq.keys[0] == "Bearer gsk-test" and body["model"] == "openai/gpt-oss-120b" and body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] > 1000 and "/no_think" not in body["messages"][1]["content"]     # room to reason before a one-word answer
    assert said == [1] and llm.stats()["fallback_calls"] == 2                          # asked twice, recorded once
    assert await llm.yes_no("Is it?", "text") is True and len(groq.asked) == 2         # the same question: from the cache


async def test_what_the_local_model_answers_never_goes_to_groq(groq, tmp_path, monkeypatch):
    model = tmp_path / "m.gguf"
    model.write_bytes(b"x")
    llm = _llm(groq, model_path=str(model))
    monkeypatch.setattr(llm, "_generate_local", lambda prompt, max_tokens: "NO")
    assert await llm.yes_no("Is it?", "text") is False and groq.asked == []


async def test_only_a_rewrite_of_markers_goes_to_groq_first_and_with_no_key_nowhere(groq, tmp_path, monkeypatch):
    model = tmp_path / "m.gguf"
    model.write_bytes(b"x")
    llm = _llm(groq, model_path=str(model))
    monkeypatch.setattr(llm, "_generate_local", lambda *a: "from the local model")
    assert await llm.rewrite("Rewrite", "At [time1], [file2] was opened.", cloud=True) == "YES" and len(groq.asked) == 1
    plain = _llm(groq, key=None, model_path=str(model))
    monkeypatch.setattr(plain, "_generate_local", lambda *a: "from the local model")
    assert await plain.rewrite("Rewrite", "At [time1], [file2] was opened.", cloud=True) is None and len(groq.asked) == 1


async def test_a_local_model_that_fails_or_cannot_load_is_covered_by_the_fallback(groq, tmp_path, monkeypatch):
    model = tmp_path / "m.gguf"
    model.write_bytes(b"x")
    llm = _llm(groq, model_path=str(model))

    def cannot(prompt, max_tokens):
        raise ImportError("llama_cpp is not installed")
    monkeypatch.setattr(llm, "_generate_local", cannot)
    assert await llm.yes_no("Is it?", "text") is True and len(groq.asked) == 1
    plain = LocalLLM("llamacpp", model_path=str(model))                               # and with no key: an unclear answer, not a crash
    monkeypatch.setattr(plain, "_generate_local", cannot)
    assert await plain.yes_no("Is it?", "text") is None


async def test_groq_failing_is_an_unclear_answer_and_several_in_a_row_stop_asking(groq):
    llm = _llm(groq)
    groq.status = 429                                                                  # (out of quota, or the model retired)
    for i in range(3):
        assert await llm.yes_no(f"Question {i}?", "text") is None
    assert len(groq.asked) == 3 and llm.available is False
    assert await llm.yes_no("Another?", "text") is None and len(groq.asked) == 3


def test_the_key_is_not_in_what_gets_printed():
    assert "gsk-secret" not in repr(Settings(groq_api_key="gsk-secret"))


def test_a_think_tag_never_closed_does_not_hide_the_answer():
    """The 4B answers "<think>\\n\\nchange an existing file": read as wrong, it scored 0 of 8 on the probe with every answer right but one."""
    from engine.llm import _strip_thinking

    assert _strip_thinking("<think>\n\nchange an existing file").strip() == "change an existing file"
    assert _strip_thinking("<think>\n</think>\n\ncreate a new file").strip() == "create a new file"
    assert _strip_thinking("create a new file").strip() == "create a new file"
