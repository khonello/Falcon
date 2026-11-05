"""Local LLM client (spec 7.2.1). Local by default: nothing leaves the machine unless a Groq key was set (see the fallback, below).

The graph in `task.llm_graph` asks narrow questions -- yes/no, pick-from-a-finite-list, short
span extraction -- and every method returns None when the model is unreachable or its answer
does not parse. None is a *signal* ("unclear -> surface to the assigner"), never an error.

Backends (open item 10.3 -- in-process is the default, a sidecar remains available):
    llamacpp  in-process llama.cpp via llama-cpp-python, GGUF file at FALCON_LLM_MODEL_PATH.
              Inference runs on ONE dedicated worker thread (llama.cpp releases the GIL), so
              the event loop keeps serving connections and calls are naturally serialised.
    openai    an OpenAI-compatible HTTP sidecar in its own process, e.g.
                  python -m llama_cpp.server --model models/Qwen3-1.7B-Q8_0.gguf --port 8008
              set FALCON_LLM_BACKEND=openai FALCON_LLM_ENDPOINT=http://127.0.0.1:8008
    ollama    an Ollama sidecar (FALCON_LLM_ENDPOINT, FALCON_LLM_MODEL as an Ollama tag).

Settings: FALCON_LLM_BACKEND (llamacpp|openai|ollama), FALCON_LLM_MODEL_PATH,
FALCON_LLM_ENDPOINT, FALCON_LLM_MODEL. A missing model file / unreachable sidecar makes the
client unavailable (logged once, retried after a backoff) -- the Engine still runs.

Fallback (the user, 4 Nov 2026): a server that cannot run the model. With FALCON_GROQ_API_KEY set, a question the local model could not answer (its
file is not there, it cannot be loaded, it timed out, it is treated as away) goes to Groq instead; a question it did answer never does. With no
key, which is the default, no question ever leaves the machine. Each use is logged and put on the audit trail (`llm.fallback`). FALCON_GROQ_MODEL,
FALCON_GROQ_ENDPOINT. Groq retires models often: when it does, the fallback fails loudly in the log and the setting is what changes.

Hardening (the model is the part of Task a person waits on, so it must never be the part that breaks):
  * answers are cached (temperature 0 makes the same question the same answer), so reading the same description twice costs nothing;
  * every call has a time limit; one that overruns is an unclear answer, not a hung request;
  * one failure is not an outage: the backend is declared away only after FAILURES_BEFORE_BACKOFF in a row, and any success clears the count;
  * a prompt too long for the model's context is refused up front (it is that input that is wrong, not the backend), and the text inside the
    quotes can never close them early;
  * `stats()` says how many questions were asked, answered from the cache, timed out or failed, and how long they took.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

BACKENDS = ("llamacpp", "openai", "ollama")
_BACKOFF_SECONDS = 60.0  # once the backend is declared away, don't hammer it on every question
FAILURES_BEFORE_BACKOFF = 3
MAX_PROMPT_CHARS = 9000        # about 3,000 tokens: well inside the context window below
CACHE_SIZE = 1024
FALLBACK_SECONDS = 20.0
FALLBACK_THINKING_TOKENS = 1024
FALLBACK_SAY_SECONDS = 3600.0
N_CTX = 4096

SYSTEM = ("You classify short workplace task descriptions. Answer with exactly what is asked and "
          "nothing else: no explanation, no punctuation, no extra words.")
SYSTEM_WRITE = ("You rewrite short factual paragraphs in plain words. Keep every marker such as [person1] exactly as it is, "
                "add nothing and leave nothing out. Reply with only the paragraph.")


class LocalLLM:
    def __init__(self, backend: str = "llamacpp", *, model_path: str | None = None,
                 endpoint: str = "http://127.0.0.1:11434", model: str = "qwen3:1.7b",
                 timeout: float = 30.0, n_threads: int | None = None, fallback_key: str | None = None,
                 fallback_model: str = "openai/gpt-oss-120b", fallback_endpoint: str = "https://api.groq.com/openai/v1") -> None:
        if backend not in BACKENDS:
            raise ValueError(f"unknown LLM backend {backend!r}")
        self.backend = backend
        self.model_path = model_path
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.n_threads = n_threads
        self.fallback_key = fallback_key or None
        self.fallback_model = fallback_model
        self.fallback_endpoint = fallback_endpoint.rstrip("/")
        self.fallback_calls = 0                           # questions sent to Groq
        self.fallback_failures = 0
        self._fallback_until = 0.0
        self._fallback_in_a_row = 0
        self._fallback_said: float | None = None
        self.on_fallback: Callable[[], Awaitable[None]] | None = None
        self._unavailable_until = 0.0
        self._llama: Any = None
        self._executor: ThreadPoolExecutor | None = None
        self.calls = 0                                    # questions that reached the model
        self.cache_hits = 0
        self.timeouts = 0
        self.failures = 0
        self.refused = 0                                  # prompts too long to ask
        self.seconds = 0.0                                # total time the model spent answering
        self._consecutive_failures = 0
        self._cache: OrderedDict[str, str] = OrderedDict()

    def stats(self) -> dict[str, Any]:
        return {"calls": self.calls, "cache_hits": self.cache_hits, "timeouts": self.timeouts, "failures": self.failures, "refused": self.refused,
                "seconds": round(self.seconds, 3), "available": self.available, "backend": self.backend, "fallback_calls": self.fallback_calls,
                "fallback_failures": self.fallback_failures}

    @property
    def available(self) -> bool:
        return self.local_available or self.fallback_available

    @property
    def local_available(self) -> bool:
        if self.backend == "llamacpp" and (not self.model_path or not Path(self.model_path).is_file()):
            return False
        return time.monotonic() >= self._unavailable_until

    def describe(self) -> str:
        said = f"llamacpp in-process ({self.model_path})" if self.backend == "llamacpp" else f"{self.backend} sidecar at {self.endpoint} ({self.model})"
        return said + (f", falling back to Groq ({self.fallback_model})" if self.fallback_key else "")

    # --- narrow question types ------------------------------------------------------------------

    async def yes_no(self, question: str, text: str) -> bool | None:
        answer = await self._ask(f"{question}\n\nText: \"\"\"{_quoted(text)}\"\"\"\n\nAnswer YES or NO.", max_tokens=3)
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
            f"{question}\n\nText: \"\"\"{_quoted(text)}\"\"\"\n\nAnswer with exactly one of: "
            f"{' | '.join(options)}.", max_tokens=8)
        if answer is None:
            return None
        norm = answer.strip().lower().strip(".\"'")
        for opt in options:
            if norm == opt.lower():
                return opt
        hits = [opt for opt in options if opt.lower() in norm]
        if len(hits) == 1:
            return hits[0]
        # One option can contain another ("use it" inside "use it on the file"): the longest
        # hit is the answer when the shorter ones are merely parts of it. Anything else --
        # notably a model that echoes the whole option list back -- stays unclear.
        if len(hits) > 1:
            longest = max(hits, key=len)
            if all(h.lower() in longest.lower() for h in hits):
                return longest
        return None

    async def extract(self, what: str, text: str) -> str | None:
        """Short span extraction (a file name, a program name, a date phrase)."""
        answer = await self._ask(
            f"Extract {what} from the text. Reply with only the extracted value, copied verbatim "
            f"from the text, or the single word NONE if it is not present.\n\nText: \"\"\"{_quoted(text)}\"\"\"",
            max_tokens=24)
        if answer is None:
            return None
        value = answer.strip().splitlines()[0].strip().strip("\"'`.,")
        if not value or value.upper() == "NONE" or len(value) > 200:
            return None
        return value

    async def rewrite(self, instruction: str, text: str, *, max_tokens: int = 320, cloud: bool = False) -> str | None:
        """The one place the model writes sentences: a paragraph whose facts are markers it cannot see ([person1], [file2]...), smoothed into plainer
        words. Never shown as it comes: the caller checks it (engine/detective/telling.py `checked`) and keeps its own paragraph otherwise. `cloud`: straight
        to Groq, the one question that may skip the local model, because it holds no fact (only markers), and nothing at all without a key."""
        answer = await self._ask(f"{instruction}\n\nParagraph: \"\"\"{_quoted(text)}\"\"\"", max_tokens=max_tokens, system=SYSTEM_WRITE, cloud=cloud)
        if answer is None:
            return None
        return answer.strip().strip("\"'`").strip() or None

    # --- transport ------------------------------------------------------------------------------

    async def _ask(self, prompt: str, *, max_tokens: int, system: str = SYSTEM, cloud: bool = False) -> str | None:
        if not self.available:
            return None
        if len(prompt) > MAX_PROMPT_CHARS:
            self.refused += 1                                           # this input is too long to read; the backend is fine
            return None
        key = f"{max_tokens}|{system[:12]}|{prompt}"
        if (hit := self._cache.get(key)) is not None:
            self._cache.move_to_end(key)
            self.cache_hits += 1
            return hit
        answer = await self._ask_local(prompt, max_tokens, system) if self.local_available and not cloud else None
        if answer is None and self.fallback_available:
            answer = await self._ask_fallback(prompt, max_tokens, system)
        if answer is None:
            return None
        self._cache[key] = answer
        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return answer

    async def _ask_local(self, prompt: str, max_tokens: int, system: str) -> str | None:
        self.calls += 1
        started = time.monotonic()
        try:
            if self.backend == "llamacpp":
                loop = asyncio.get_running_loop()
                answer = await asyncio.wait_for(loop.run_in_executor(self._worker(), self._generate_local, *_args(prompt, max_tokens, system)), self.timeout)
            else:
                answer = await asyncio.wait_for(asyncio.to_thread(self._generate_http, *_args(prompt, max_tokens, system)), self.timeout + 5)
        except asyncio.TimeoutError:
            self.timeouts += 1
            self._failed(f"did not answer within {self.timeout:.0f}s")
            return None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            self._failed(f"unreachable: {exc}")
            return None
        except (ValueError, KeyError, RuntimeError, ImportError, MemoryError) as exc:      # (a server that cannot load the model at all)
            self._failed(f"failed: {exc!r}")
            return None
        finally:
            self.seconds += time.monotonic() - started
        self._consecutive_failures = 0
        return answer

    # --- the fallback: only when a key was set, and only for what the local model could not answer -----------------------------

    @property
    def fallback_available(self) -> bool:
        return bool(self.fallback_key) and time.monotonic() >= self._fallback_until

    async def _ask_fallback(self, prompt: str, max_tokens: int, system: str) -> str | None:
        self.fallback_calls += 1
        await self._say_fallback_used()
        try:
            answer = await asyncio.wait_for(asyncio.to_thread(self._generate_groq, prompt, max_tokens, system), FALLBACK_SECONDS + 2)
        except (asyncio.TimeoutError, urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            self.fallback_failures += 1
            self._fallback_in_a_row += 1
            log.warning("Groq fallback failed (%s, %d in a row)", exc.__class__.__name__, self._fallback_in_a_row)
            if self._fallback_in_a_row >= FAILURES_BEFORE_BACKOFF:
                self._fallback_until = time.monotonic() + _BACKOFF_SECONDS
                self._fallback_in_a_row = 0
            return None
        self._fallback_in_a_row = 0
        return answer or None

    async def _say_fallback_used(self) -> None:
        """Text is leaving the machine: logged and put on the audit trail (`on_fallback`), at most once an hour, not once per question."""
        now = time.monotonic()
        if self._fallback_said is not None and now - self._fallback_said < FALLBACK_SAY_SECONDS:
            return
        self._fallback_said = now
        log.warning("questions are going to Groq (%s)", self.fallback_model)
        if self.on_fallback is not None:
            try:
                await self.on_fallback()
            except Exception:                                # (the question is answered either way)
                log.exception("could not record the fallback")

    def _generate_groq(self, prompt: str, max_tokens: int, system: str) -> str:
        # A reasoning model spends tokens thinking before it answers: the room is for that, so a one-word question is not cut off before its answer
        body: dict[str, Any] = {"model": self.fallback_model, "temperature": 0, "max_completion_tokens": max_tokens + FALLBACK_THINKING_TOKENS,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if "gpt-oss" in self.fallback_model:
            body.update({"reasoning_effort": "low", "include_reasoning": False})
        req = urllib.request.Request(f"{self.fallback_endpoint}/chat/completions", data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.fallback_key}", "User-Agent": "falcon-engine"})
        with urllib.request.urlopen(req, timeout=FALLBACK_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return _strip_thinking(str(data["choices"][0]["message"]["content"] or ""))

    def _failed(self, why: str) -> None:
        """One failure is a missing answer; only several in a row mean the backend is away."""
        self.failures += 1
        self._consecutive_failures += 1
        log.warning("local LLM (%s) %s (%d in a row)", self.backend, why, self._consecutive_failures)
        if self._consecutive_failures >= FAILURES_BEFORE_BACKOFF:
            self._unavailable_until = time.monotonic() + _BACKOFF_SECONDS
            self._consecutive_failures = 0
            log.warning("local LLM (%s) is treated as away for %.0fs", self.backend, _BACKOFF_SECONDS)

    def _worker(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="falcon-llm")
        return self._executor

    def _load_local(self) -> Any:
        if self._llama is None:
            from llama_cpp import Llama  # imported lazily: optional dependency

            log.info("loading local model %s", self.model_path)
            self._llama = Llama(model_path=str(self.model_path), n_ctx=N_CTX, n_threads=self.n_threads,
                                verbose=False)
        return self._llama

    def _generate_local(self, prompt: str, max_tokens: int, system: str = SYSTEM) -> str:
        llama = self._load_local()
        out = llama.create_chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt + " /no_think"}],
            max_tokens=max_tokens + 8, temperature=0.0)
        return _strip_thinking(str(out["choices"][0]["message"]["content"]))

    def _generate_http(self, prompt: str, max_tokens: int, system: str = SYSTEM) -> str:
        if self.backend == "ollama":
            url = f"{self.endpoint}/api/generate"
            body: dict[str, Any] = {"model": self.model, "prompt": f"{system}\n\n{prompt}", "stream": False,
                                    "think": False, "options": {"temperature": 0, "num_predict": max_tokens + 8}}
        else:  # openai-compatible (e.g. python -m llama_cpp.server)
            url = f"{self.endpoint}/v1/chat/completions"
            body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens + 8,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": prompt + " /no_think"}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # local sidecar only
            data = json.loads(resp.read().decode("utf-8"))
        if self.backend == "ollama":
            return _strip_thinking(str(data["response"]))
        return _strip_thinking(str(data["choices"][0]["message"]["content"]))


def _args(prompt: str, max_tokens: int, system: str) -> tuple[Any, ...]:
    """What the generator is called with: the system prompt only when it is not the usual one (a narrow question is asked as it always was)."""
    return (prompt, max_tokens) if system is SYSTEM else (prompt, max_tokens, system)


def _strip_thinking(text: str) -> str:
    """Qwen3 may emit an empty <think></think> block even with thinking disabled, and the 4B opens one and never closes it: its answer follows the bare tag."""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    elif text.lstrip().startswith("<think>"):
        text = text.lstrip()[len("<think>"):]
    return text.strip()


def _quoted(text: str) -> str:
    """The description goes inside triple quotes in the prompt; nothing in it may close them early or pose as a new instruction line."""
    return str(text).replace(chr(34) * 3, chr(39) * 3).replace(chr(0), "")
