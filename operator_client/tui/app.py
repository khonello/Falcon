"""The prompt_toolkit loop: a prompt with completion, a bottom toolbar that is the persistent
status surface, and pushes printed live above the prompt.

Toolbar (always visible):
    [Admin · account 2 · pc 2 · Finance]  session: TRAVERSAL pc 3 until 12:30  ⚠ 2 pings  ⏰ task 5 deadline
    and, when Super User is inside another user's view, a red "SUPER USER TRAVERSING" banner;
    when this PC is blocked, a red "BLOCKED by <name>" marker.
"""

from __future__ import annotations

from typing import Any

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

import operator_client.tui.commands  # noqa: F401  -- registers commands
from operator_client.core.config import LocalConfig
from operator_client.core.state import ClientState
from operator_client.tui.push_format import describe_push
from operator_client.tui.shell import ShellContext, registry, run_line

STYLE = Style.from_dict({
    "bottom-toolbar": "bg:#222222 #dddddd",
    "bottom-toolbar.role": "bold #ffffff",
    "bottom-toolbar.banner": "bg:#aa0000 #ffffff bold",
    "bottom-toolbar.blocked": "bg:#aa0000 #ffffff bold",
    "bottom-toolbar.session": "#9fd0ff",
    "bottom-toolbar.pulse": "bold #ffcc00",
    "bottom-toolbar.pulse-done": "bold #66ff66",
    "bottom-toolbar.pulse-bad": "bold #ff6666",
    "push": "#8ab4f8",
    "push.alert": "bold #ff6666",
})

_PULSE_STYLE = {"deadline_reached": "pulse-bad", "task_completed": "pulse-done", "unaddressed_ping": "pulse",
                "blocked": "blocked", "flow_failed": "pulse-bad", "violation": "pulse-bad", "offer": "pulse",
                "session": "session"}


def _toolbar(state: ClientState, tick: list[int]) -> FormattedText:
    tick[0] += 1
    on = tick[0] % 2 == 0  # the "pulse": alternate emphasis every refresh
    parts: list[tuple[str, str]] = []
    if not state.connected:
        return FormattedText([("class:bottom-toolbar", " not connected -- connect [host:port] client=<id> [plaintext] ")])
    parts.append(("class:bottom-toolbar.role", f" {state.role_label} "))
    parts.append(("class:bottom-toolbar", f"acct {state.account_id} pc {state.pc_id} dept {state.department_id or '-'} "))
    if state.super_user_banner:
        parts.append(("class:bottom-toolbar.banner", "  SUPER USER TRAVERSING  "))
    if state.blocked_by:
        parts.append(("class:bottom-toolbar.blocked", f"  BLOCKED by {state.blocked_by.get('occupant_name')}  "))
    s = state.session
    if s:
        via = "native" if s.get("occupied_via") == "native" else f"{s.get('occupied_via', '').upper()} pc {s.get('pc_id')}"
        until = f" until {s['deadline_at'][11:16]}" if s.get("deadline_at") else ""
        parts.append(("class:bottom-toolbar.session", f" session: {via}{until} "))
    for ind in state.indicators[-4:]:
        style = _PULSE_STYLE.get(ind.kind, "pulse")
        marker = "●" if on else "○"
        parts.append((f"class:bottom-toolbar.{style}", f" {marker} {ind.text} "))
    return FormattedText(parts)


async def run_app(config: LocalConfig, *, initial: list[str] | None = None) -> None:
    state = ClientState()
    ctx = ShellContext(config=config, state=state)

    async def print_push(type_: str, payload: dict[str, Any]) -> None:
        text, alert = describe_push(type_, payload)
        if text:
            print_formatted_text(FormattedText([("class:push.alert" if alert else "class:push", f"  » {text}")]),
                                 style=STYLE)

    ctx.scratch["push_printer"] = print_push
    tick = [0]
    session: PromptSession[str] = PromptSession(
        completer=NestedCompleter.from_nested_dict(registry.completions()),
        bottom_toolbar=lambda: _toolbar(state, tick), style=STYLE, refresh_interval=0.7,
        complete_while_typing=False)

    print_formatted_text(FormattedText([("bold", "Falcon Operator Client"), ("", "  --  type `help`; `connect` to begin")]))
    for line in initial or []:
        out = await run_line(ctx, line)
        if out:
            print_formatted_text(out)
    with patch_stdout():
        while not ctx.quit_requested:
            try:
                line = await session.prompt_async(_prompt(state))
            except (EOFError, KeyboardInterrupt):
                break
            out = await run_line(ctx, line)
            if out:
                print_formatted_text(out)
    if ctx.conn is not None:
        await ctx.conn.close()


def _prompt(state: ClientState) -> str:
    if not state.connected:
        return "falcon> "
    tag = {"super_user": "su", "admin": "admin", "worker": "worker"}.get(state.role or "", "?")
    where = f"@pc{state.session['pc_id']}" if state.traversing and state.session else ""
    return f"{tag}{where}> "
