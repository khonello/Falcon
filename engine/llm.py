"""Local LLM client (spec 7.2.1). Local only -- never an external API.

The graph in `task.llm_graph` asks narrow questions -- yes/no, pick-from-a-finite-list, short
span extraction -- and every method returns None when the model is unreachable or its answer
does not parse. None is a *signal* ("unclear -> surface to the assigner"), never an error.

Backends (open item 10.3 -- in-process is the default, a sidecar remains available):
    llamacpp  in-process llama.cpp via llama-cpp-python, GGUF file at FALCON_LLM_MODEL_PATH.
              Inference runs on ONE dedicated worker thread (llama.cpp releases the GIL), so
              the event loop keeps serving connections and calls are naturally serialised.
    openai    an OpenAI-compatible HTTP sidecar in its own process, e.g.
                  python -m llama_cpp.server --model models/Qwen3-0.6B-Q8_0.gguf --port 8008
              set FALCON_LLM_BACKEND=openai FALCON_LLM_ENDPOINT=http://127.0.0.1:8008
    ollama    an Ollama sidecar (FALCON_LLM_ENDPOINT, FALCON_LLM_MODEL as an Ollama tag).

Settings: FALCON_LLM_BACKEND (llamacpp|openai|ollama), FALCON_LLM_MODEL_PATH,
FALCON_LLM_ENDPOINT, FALCON_LLM_MODEL. A missing model file / unreachable sidecar makes the
client unavailable (logged once, retried after a backoff) -- the Engine still runs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

BACKENDS = ("llamacpp", "openai", "ollama")
_BACKOFF_SECONDS = 60.0  # after a failure, don't hammer the backend on every question

SYSTEM = ("You classify short workplace task descriptions. Answer with exactly what is asked and "
          "nothing else: no explanation, no punctuation, no extra words.")


class LocalLLM:
    def __init__(self, backend: str = "llamacpp", *, model_path: str | None = None,
                 endpoint: str = "http://127.0.0.1:11434", model: str = "qwen3:0.6b",
                 timeout: float = 30.0, n_threads: int | None = None) -> None:
        if backend not in BACKENDS:
            raise ValueError(f"unknown LLM backend {backend!r}")
        self.backend = backend
        self.model_path = model_path
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.n_threads = n_threads
        self._unavailable_until = 0.0
        self._llama: Any = None
        self._executor: ThreadPoolExecutor | None = None
        self.calls = 0

    @property
    def available(self) -> bool:
        if self.backend == "llamacpp" and (not self.model_path or not Path(self.model_path).is_file()):
            return False
        return time.monotonic() >= self._unavailable_until

    def describe(self) -> str:
        if self.backend == "llamacpp":
            return f"llamacpp in-process ({self.model_path})"
        return f"{self.backend} sidecar at {self.endpoint} ({self.model})"

    # --- narrow question types ------------------------------------------------------------------

    async def yes_no(self, question: str, text: str) -> bool | None:
        answer = await self._ask(f"{question}\n\nText: \"\"\"{text}\"\"\"\n\nAnswer YES or NO.", max_tokens=3)
        if answer is None:
            return None
        word = answer.strip().upper().strip(".!,\"'")
        if word.startswith("YES"):
            return True
        if word.startswith("NO"):
            return False
        return None

    async def choose(self, question: str, text: str, options: list[str]) -> str | None:
        answer = await self._ask(
            f"{question}\n\nText: \"\"\"{text}\"\"\"\n\nAnswer with exactly one of: "
            f"{' | '.join(options)}.", max_tokens=8)
        if answer is None:
            return None
        norm = answer.strip().lower().strip(".\"'")
        for opt in options:
            if norm == opt.lower():
                return opt
        hits = [opt for opt in options if opt.lower() in norm]
        return hits[0] if len(hits) == 1 else None

    async def extract(self, what: str, text: str) -> str | None:
        """Short span extraction (a file name, a program name, a date phrase)."""
        answer = await self._ask(
            f"Extract {what} from the text. Reply with only the extracted value, copied verbatim "
            f"from the text, or the single word NONE if it is not present.\n\nText: \"\"\"{text}\"\"\"",
            max_tokens=24)
        if answer is None:
            return None
        value = answer.strip().splitlines()[0].strip().strip("\"'`.,")
        if not value or value.upper() == "NONE" or len(value) > 200:
            return None
        return value

    # --- transport ------------------------------------------------------------------------------

    async def _ask(self, prompt: str, *, max_tokens: int) -> str | None:
        if not self.available:
            return None
        self.calls += 1
        try:
            if self.backend == "llamacpp":
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(self._worker(), self._generate_local, prompt, max_tokens)
            return await asyncio.to_thread(self._generate_http, prompt, max_tokens)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            log.warning("local LLM (%s) unreachable: %s; backing off %.0fs", self.backend, exc, _BACKOFF_SECONDS)
            self._unavailable_until = time.monotonic() + _BACKOFF_SECONDS
            return None
        except (ValueError, KeyError, RuntimeError) as exc:
            log.warning("local LLM (%s) failed: %s", self.backend, exc)
            self._unavailable_until = time.monotonic() + _BACKOFF_SECONDS
            return None

    def _worker(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="falcon-llm")
        return self._executor

    def _load_local(self) -> Any:
        if self._llama is None:
            from llama_cpp import Llama  # imported lazily: optional dependency

            log.info("loading local model %s", self.model_path)
            self._llama = Llama(model_path=str(self.model_path), n_ctx=2048, n_threads=self.n_threads,
                                verbose=False)
        return self._llama

    def _generate_local(self, prompt: str, max_tokens: int) -> str:
        llama = self._load_local()
        out = llama.create_chat_completion(
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": prompt + " /no_think"}],
            max_tokens=max_tokens + 8, temperature=0.0)
        return _strip_thinking(str(out["choices"][0]["message"]["content"]))

    def _generate_http(self, prompt: str, max_tokens: int) -> str:
        if self.backend == "ollama":
            url = f"{self.endpoint}/api/generate"
            body: dict[str, Any] = {"model": self.model, "prompt": f"{SYSTEM}\n\n{prompt}", "stream": False,
                                    "think": False, "options": {"temperature": 0, "num_predict": max_tokens + 8}}
        else:  # openai-compatible (e.g. python -m llama_cpp.server)
            url = f"{self.endpoint}/v1/chat/completions"
            body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens + 8,
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": prompt + " /no_think"}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # local sidecar only
            data = json.loads(resp.read().decode("utf-8"))
        if self.backend == "ollama":
            return _strip_thinking(str(data["response"]))
        return _strip_thinking(str(data["choices"][0]["message"]["content"]))


def _strip_thinking(text: str) -> str:
    """Qwen3 may emit an empty <think></think> block even with thinking disabled."""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()
