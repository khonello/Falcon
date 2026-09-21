"""Local LLM client (spec 7.2.1). Local only -- never an external API.

Hosting (in-process vs. Ollama-style sidecar) is an open item (spec 10.3); this interface hides
that choice from `engine.task.llm_graph`, which is the only consumer. The graph asks narrow
questions: yes/no, pick-from-a-finite-list, short span extraction. Nothing here generates
open-ended text.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class LocalLLM:
    def __init__(self, model: str = "qwen3:0.6b", endpoint: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.endpoint = endpoint

    async def yes_no(self, question: str, text: str) -> bool | None:
        """Returns None when the answer is unclear -- that is a signal, not an error."""
        log.debug("LLM yes_no: %s", question)
        return None  # SCAFFOLD

    async def choose(self, question: str, text: str, options: list[str]) -> str | None:
        log.debug("LLM choose: %s %s", question, options)
        return None  # SCAFFOLD

    async def extract(self, what: str, text: str) -> str | None:
        """Short span extraction (a file name, a program name, a date phrase)."""
        log.debug("LLM extract: %s", what)
        return None  # SCAFFOLD
