"""Operator Client TUI (prompt_toolkit) -- the first UI, used to exercise the built system.

A command shell rather than a screen-per-feature layout: every Engine handler is reachable by
a short command, pushes print live above the prompt, and the bottom toolbar is the persistent
surface the design asks for (identity, occupied session, the red Super User banner, blocked
state, and the pulsing indicators). The GUI later sits on the same `operator_client.core`.

    shell      ShellContext + command registry + argument grammar (no UI imports)
    render     tables / key-value / status text (plain strings)
    commands   one module per area, registering commands
    app        the prompt_toolkit loop and push printing
"""
