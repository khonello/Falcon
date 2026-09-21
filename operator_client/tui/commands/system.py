"""connect / status / help / pushes / raw / quit"""

from __future__ import annotations

import json

from operator_client.core.connection import EngineConnection, connect_with_retry
from operator_client.tui.render import bullet, kv, pretty, table
from operator_client.tui.shell import Args, Command, ShellContext, UsageError, command, registry


@command("connect", usage="[host:port] [client=<client_id>] [plaintext] [ca=<cert.pem>]",
         help_="Connect to the Engine and authenticate as this client")
async def connect(ctx: ShellContext, args: Args) -> str:
    cfg = ctx.config
    if args.positional:
        host, _, port = args.positional[0].partition(":")
        cfg.engine_host = host or cfg.engine_host
        if port:
            cfg.engine_port = int(port)
    if args.opt("client"):
        cfg.client_id = str(args.opt("client"))
    if args.flag("plaintext"):
        cfg.tls = False
    if args.opt("ca"):
        cfg.ca_cert = args.opt("ca")
    if not cfg.client_id:
        raise UsageError("no client id: connect ... client=<id>")
    if ctx.conn is not None:
        await ctx.conn.close()
    conn = EngineConnection(cfg.engine_host, cfg.engine_port, client_id=cfg.client_id, tls=cfg.tls,
                            ca_cert=cfg.ca_cert)
    conn.on_push(ctx.state.on_push)
    extra = ctx.scratch.get("push_printer")
    if extra:
        conn.on_push(extra)

    async def lost() -> None:
        ctx.state.connected = False
        ctx.state.session = None
        ctx.state.add_indicator("session", "connection to Engine lost", key="conn")

    conn.on_disconnect = lost
    ident = await connect_with_retry(conn, attempts=int(args.opt("attempts", "1") or 1))
    ctx.conn = conn
    ctx.state.set_identity(ident, cfg.engine_address)
    ctx.state.clear_indicator("conn")
    cfg.save()
    st = await conn.call("hierarchy.session_state")
    ctx.state.set_session(st.get("my_session"))
    if st.get("blocked"):
        ctx.state.blocked_by = st.get("pc_session")
    ps = await conn.call("assistance.ping_status")
    await ctx.state.on_push("assistance.ping_status", {"unaddressed": ps.get("unaddressed", 0)})
    return (f"connected to {cfg.engine_address} as {ctx.state.role_label} "
            f"(account {ident.account_id}, pc {ident.pc_id}, department {ident.department_id})")


@command("disconnect", help_="Close the connection")
async def disconnect(ctx: ShellContext, args: Args) -> str:
    if ctx.conn is not None:
        await ctx.conn.close()
        ctx.conn = None
    ctx.state.connected = False
    ctx.state.session = None
    return "disconnected"


@command("status", help_="Who you are, what session you occupy, current indicators")
async def status(ctx: ShellContext, args: Args) -> str:
    s = ctx.state
    out = kv({"engine": s.engine or "-", "connected": s.connected, "client_id": s.client_id or "-",
              "role": s.role_label, "account_id": s.account_id, "pc_id": s.pc_id, "department_id": s.department_id})
    out += "\n\nsession:\n" + (kv(s.session) if s.session else "  (none)")
    if s.blocked_by:
        out += "\n\nBLOCKED: your PC is occupied by " + str(s.blocked_by.get("occupant_name"))
    if s.super_user_banner:
        out += "\n\n[RED BANNER] Super User is inside another user's view"
    out += "\n\nindicators:\n" + bullet(f"[{i.kind}] {i.text}" for i in s.indicators)
    return out


@command("pushes", usage="[n]", help_="Recent pushes from the Engine")
async def pushes(ctx: ShellContext, args: Args) -> str:
    n = int(args.positional[0]) if args.positional else 20
    rows = [{"at": at.strftime("%H:%M:%S"), "type": t, "payload": p} for at, t, p in ctx.state.recent_pushes[-n:]]
    return table(rows, ["at", "type", "payload"], width=90)


@command("raw", usage="<message.type> [json-payload]", help_="Send any request to the Engine")
async def raw(ctx: ShellContext, args: Args) -> str:
    type_ = args.get(0, "message.type")
    payload = {}
    if len(args.positional) > 1:
        try:
            payload = json.loads(" ".join(args.positional[1:]))
        except ValueError as exc:
            raise UsageError(f"payload must be JSON: {exc}") from exc
    return pretty(await ctx.call(type_, payload))


@command("capabilities", help_="Message types the Engine accepts")
async def capabilities(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("system.capabilities")
    return f"engine {res.get('version')}\n" + bullet(res.get("message_types", []))


@command("help", usage="[command]", help_="List commands, or show one command's usage")
async def help_(ctx: ShellContext, args: Args) -> str:
    if args.positional:
        want = " ".join(args.positional).lower()
        found = [c for c in registry.commands.values() if c.full == want or c.name == want]
        if not found:
            return f"no such command {want!r}"
        return "\n".join(f"{c.full} {c.usage}\n    {c.help}" for c in sorted(found, key=lambda c: c.full))
    rows = [{"command": c.full, "usage": c.usage, "what": c.help}
            for c in sorted(registry.commands.values(), key=lambda c: c.full)]
    return table(rows, ["command", "usage", "what"], width=60)


@command("quit", help_="Exit")
async def quit_(ctx: ShellContext, args: Args) -> str:
    ctx.quit_requested = True
    return "bye"


registry.add(Command("exit", None, "", "Exit", quit_))
