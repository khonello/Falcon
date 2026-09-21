"""Command-shell machinery shared by the Operator Client TUI and the Worker Client's narrow
UI: the argument grammar, the command registry, and the `@command` decorator.

Grammar:  `<command> [<sub>] [positional ...] [key=value ...]`
          quoted strings allowed; `key=a,b` and repeated `key=` are both supported.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

_OPTION_KEY = re.compile(r"^[a-z][a-z0-9_]+$")


class UsageError(Exception):
    pass


@dataclass
class Args:
    positional: list[str]
    options: dict[str, str]
    repeated: dict[str, list[str]] = field(default_factory=dict)  # every value of a repeated key=

    def all(self, name: str) -> list[str]:
        return self.repeated.get(name, [])

    def get(self, index: int, name: str) -> str:
        if index >= len(self.positional):
            raise UsageError(f"missing <{name}>")
        return self.positional[index]

    def get_int(self, index: int, name: str) -> int:
        raw = self.get(index, name)
        try:
            return int(raw)
        except ValueError as exc:
            raise UsageError(f"<{name}> must be a number, got {raw!r}") from exc

    def rest(self, start: int, name: str) -> str:
        text = " ".join(self.positional[start:]).strip()
        if not text:
            raise UsageError(f"missing <{name}>")
        return text

    def opt(self, name: str, default: str | None = None) -> str | None:
        return self.options.get(name, default)

    def opt_int(self, name: str) -> int | None:
        raw = self.options.get(name)
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError as exc:
            raise UsageError(f"{name}= must be a number") from exc

    def opt_ints(self, name: str) -> list[int] | None:
        raw = self.options.get(name)
        if raw is None:
            return None
        try:
            return [int(x) for x in raw.split(",") if x.strip()]
        except ValueError as exc:
            raise UsageError(f"{name}= must be numbers separated by commas") from exc

    def flag(self, name: str) -> bool:
        return name in self.positional or self.options.get(name, "").lower() in ("1", "true", "yes", "on")


def parse(line: str) -> tuple[list[str], Args]:
    """-> (command words consumed by lookup, Args). Splitting of words vs args happens in
    `Registry.resolve`; here we just tokenise and separate key=value options."""
    # POSIX splitting gives us quotes, but it also treats backslashes as escapes -- fatal for
    # Windows paths (C:\Users\...). Double them first so they survive verbatim.
    tokens = shlex.split(line.replace("\\", "\\\\"), posix=True)
    positional: list[str] = []
    options: dict[str, str] = {}
    repeated: dict[str, list[str]] = {}
    for tok in tokens:
        # key=value only for lowercase keys of 2+ chars: `C:/x=y` or a description containing
        # `x=1` stays positional. Quote text that must contain a `key=` literally.
        if "=" in tok and _OPTION_KEY.match(tok.split("=", 1)[0]):
            k, v = tok.split("=", 1)
            options[k] = v
            repeated.setdefault(k, []).append(v)
        else:
            positional.append(tok)
    return positional, Args(positional, options, repeated)


Handler = Callable[[Any, Args], Awaitable[str | None]]


@dataclass
class Command:
    name: str
    sub: str | None
    usage: str
    help: str
    handler: Handler
    roles: tuple[str, ...] = ()  # informational; the Engine enforces

    @property
    def full(self) -> str:
        return f"{self.name} {self.sub}" if self.sub else self.name


class Registry:
    def __init__(self) -> None:
        self.commands: dict[tuple[str, str | None], Command] = {}

    def add(self, cmd: Command) -> None:
        self.commands[(cmd.name, cmd.sub)] = cmd

    def resolve(self, positional: list[str]) -> tuple[Command, int] | None:
        """Longest match first: (name, sub) then (name, None). Returns the command and how many
        leading words it consumed."""
        if not positional:
            return None
        name = positional[0].lower()
        if len(positional) > 1:
            cmd = self.commands.get((name, positional[1].lower()))
            if cmd:
                return cmd, 2
        cmd = self.commands.get((name, None))
        return (cmd, 1) if cmd else None

    def names(self) -> list[str]:
        return sorted({c.full for c in self.commands.values()})

    def completions(self) -> dict[str, Any]:
        """Nested dict for prompt_toolkit's NestedCompleter."""
        tree: dict[str, Any] = {}
        for (name, sub) in self.commands:
            tree.setdefault(name, {} if sub else None)
            if sub:
                if tree[name] is None:
                    tree[name] = {}
                tree[name][sub] = None
        return tree


def make_command_decorator(registry: Registry):
    def command(name: str, sub: str | None = None, usage: str = "", help_: str = "", roles: tuple[str, ...] = ()):
        def register(fn: Handler) -> Handler:
            registry.add(Command(name, sub, usage, help_, fn, roles))
            return fn
        return register
    return command


