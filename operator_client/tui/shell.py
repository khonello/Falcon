"""The Operator Client shell: its context, the command registry, and `run_line`/`run_script`.

The grammar/registry machinery lives in `common.cli` (shared with the Worker Client).

    @command("task", "propose", "<assignee_id> <description...>", "Ask the Engine to propose a structure")
    async def task_propose(ctx: ShellContext, args: Args) -> str: ...

A command returns the text to print (or None). Errors from the Engine are `EngineError` and
are rendered by the shell as `code: message`, never as tracebacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from common.cli import (  # noqa: F401
    Args,
    Command,
    Registry,
    UsageError,
    make_command_decorator,
    parse,
)
from operator_client.core.config import LocalConfig
from operator_client.core.connection import ConnectionError_, EngineConnection, EngineError
from operator_client.core.state import ClientState

registry = Registry()
command = make_command_decorator(registry)


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
