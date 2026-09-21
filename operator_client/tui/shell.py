"""Command registry, argument grammar, and the shell context commands run against.

Grammar:  `<command> [<sub>] [positional ...] [key=value ...]`
          quoted strings allowed; `key=a,b,c` gives a list where the command expects one.

    @command("task", "propose", "<assignee_id> <description...>", "Ask the Engine to propose a structure")
    async def task_propose(ctx: ShellContext, args: Args) -> str: ...

A command returns the text to print (or None). Errors from the Engine are `EngineError` and
are rendered by the shell as `code: message`, never as tracebacks.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from operator_client.core.config import LocalConfig
from operator_client.core.connection import ConnectionError_, EngineConnection, EngineError
from operator_client.core.state import ClientState

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
    tokens = shlex.split(line, posix=True)
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


Handler = Callable[["ShellContext", Args], Awaitable[str | None]]


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


registry = Registry()


def command(name: str, sub: str | None = None, usage: str = "", help_: str = "", roles: tuple[str, ...] = ()):
    def register(fn: Handler) -> Handler:
        registry.add(Command(name, sub, usage, help_, fn, roles))
        return fn
    return register


@dataclass
class ShellContext:
    config: LocalConfig
    state: ClientState
    conn: EngineConnection | None = None
    # Working data between commands (e.g. the last task proposal being edited).
    scratch: dict[str, Any] = field(default_factory=dict)
    quit_requested: bool = False

    def require_conn(self) -> EngineConnection:
        if self.conn is None or not self.conn.connected:
            raise UsageError("not connected -- use: connect [host:port] [client=<id>] [plaintext]")
        return self.conn

    async def call(self, type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.require_conn().call(type_, payload)


async def run_line(ctx: ShellContext, line: str) -> str:
    """Execute one command line; always returns printable text (errors included)."""
    line = line.strip()
    if not line or line.startswith("#"):
        return ""
    try:
        positional, args = parse(line)
    except ValueError as exc:
        return f"parse error: {exc}"
    found = registry.resolve(positional)
    if found is None:
        return f"unknown command {positional[0]!r} -- try: help"
    cmd, consumed = found
    args.positional = args.positional[consumed:]
    try:
        out = await cmd.handler(ctx, args)
        return out if out is not None else ""
    except UsageError as exc:
        return f"usage: {cmd.full} {cmd.usage}\n  {exc}"
    except EngineError as exc:
        return f"{exc.code}: {exc.message}"
    except ConnectionError_ as exc:
        return f"connection: {exc}"


async def run_script(config: LocalConfig, lines: list[str]) -> list[str]:
    """Non-interactive: run commands in order, return their outputs. Used by tests and for
    scripted checks (`python -m operator_client --script "connect ...; tree"`). No UI imports."""
    import operator_client.tui.commands  # noqa: F401  -- registers commands

    ctx = ShellContext(config=config, state=ClientState())
    outputs: list[str] = []
    for line in lines:
        outputs.append(await run_line(ctx, line))
        if ctx.quit_requested:
            break
    if ctx.conn is not None:
        await ctx.conn.close()
    return outputs
