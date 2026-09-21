"""Local LLM client (spec 7.2.1). Local only -- never an external API.

Talks to an Ollama-style sidecar over HTTP on the Engine host (open item 10.3 leaves
in-process vs sidecar undecided; this interface hides that choice from `task.llm_graph`, the
only consumer). The graph asks narrow questions -- yes/no, pick-from-a-finite-list, short span
extraction -- and every method returns None when the model is unreachable or its answer does
not parse. None is a *signal* ("unclear -> surface to the assigner"), never an error.

Settings: FALCON_LLM_ENDPOINT (default http://127.0.0.1:11434), FALCON_LLM_MODEL
(default qwen3:0.6b -- the v1 top pick; final size is an empirical decision).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

_BACKOFF_SECONDS = 60.0  # after a connection failure, don't hammer the sidecar on every question


class LocalLLM:
    def __init__(self, endpoint: str = "http://127.0.0.1:11434", model: str = "qwen3:0.6b",
                 timeout: float = 30.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._unavailable_until = 0.0

    @property
    def available(self) -> bool:
        return time.monotonic() >= self._unavailable_until

    # --- narrow question types ------------------------------------------------------------------

    async def yes_no(self, question: str, text: str) -> bool | None:
        answer = await self._ask(
            f"{question}\n\nText: \"\"\"{text}\"\"\"\n\nAnswer with exactly one word: YES or NO.")
        if answer is None:
            return None
        word = answer.strip().upper().strip(".!")
        if word.startswith("YES"):
            return True
        if word.startswith("NO"):
            return False
        return None

    async def choose(self, question: str, text: str, options: list[str]) -> str | None:
        answer = await self._ask(
            f"{question}\n\nText: \"\"\"{text}\"\"\"\n\nAnswer with exactly one of these options and "
            f"nothing else: {', '.join(options)}.")
        if answer is None:
            return None
        norm = answer.strip().lower().strip(".\"'")
        for opt in options:
            if norm == opt.lower():
                return opt
        for opt in options:  # tolerate "The answer is: exists"
            if opt.lower() in norm:
                return opt
        return None

    async def extract(self, what: str, text: str) -> str | None:
        """Short span extraction (a file name, a program name, a date phrase)."""
        answer = await self._ask(
            f"Extract {what} from the text. Reply with only the extracted value, verbatim from the "
            f"text, or the single word NONE if it is not present.\n\nText: \"\"\"{text}\"\"\"")
        if answer is None:
            return None
        value = answer.strip().strip("\"'`")
        if not value or value.upper() == "NONE" or len(value) > 200:
            return None
        return value

    # --- transport ------------------------------------------------------------------------------

    async def _ask(self, prompt: str) -> str | None:
        if not self.available:
            return None
        try:
            return await asyncio.to_thread(self._generate, prompt)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            log.warning("local LLM unreachable at %s (%s); backing off %.0fs", self.endpoint, exc, _BACKOFF_SECONDS)
            self._unavailable_until = time.monotonic() + _BACKOFF_SECONDS
            return None
        except (ValueError, KeyError) as exc:
            log.warning("local LLM returned an unparseable response: %s", exc)
            return None

    def _generate(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": 64},
        }).encode("utf-8")
        req = urllib.request.Request(f"{self.endpoint}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(data["response"])
