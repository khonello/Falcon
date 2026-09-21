"""Assistance: search, ping, respond, message channel (turn lock), close, listeners."""

from __future__ import annotations

from operator_client.tui.render import bullet, table
from operator_client.tui.shell import Args, ShellContext, command


@command("search", usage="<query...>", help_="Search the Global File Index within your access tier")
async def search(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.search", {"query": args.rest(0, "query")})
    return table(res["results"], ["id", "pc_id", "path", "resource_tag", "resource_tag_scope_department_id", "last_seen_at"],
                 width=60)


@command("ping", usage="<account_id>", help_="Ping your direct superior (or subordinate) for attention; repeatable")
async def ping(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.ping", {"to_account_id": args.get_int(0, "account_id")})
    return f"ping {res['ping_id']} sent"


@command("pings", help_="Unaddressed pings waiting for you (the pulsing indicator)")
async def pings(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.ping_status")
    await ctx.state.on_push("assistance.ping_status", {"unaddressed": res["unaddressed"]})
    return f"{res['unaddressed']} unaddressed\n" + table(res["pings"], ["id", "from_name", "sender_account_id", "sent_at"])


@command("respond", usage="<ping_id>", help_="Respond to a ping: addresses it and opens (or returns) the channel")
async def respond(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.respond", {"ping_id": args.get_int(0, "ping_id")})
    ctx.scratch["channel"] = res["channel_id"]
    return (f"channel {res['channel_id']} {'opened' if res['opened'] else 'already open'}; "
            f"turn: {res['turn']}  (use: msg <text> / channel {res['channel_id']})")


@command("msg", usage="[channel_id] <text...>", help_="Post one message (one per turn); channel defaults to the last used")
async def msg(ctx: ShellContext, args: Args) -> str:
    if args.positional and args.positional[0].isdigit():
        channel_id = int(args.positional[0])
        text = args.rest(1, "text")
    else:
        channel_id = ctx.scratch.get("channel")
        text = args.rest(0, "text")
    if channel_id is None:
        return "no channel selected -- give a channel id"
    res = await ctx.call("assistance.message", {"channel_id": channel_id, "body": text})
    ctx.scratch["channel"] = channel_id
    return f"sent (message {res['message_id']}); now the {res['turn']}'s turn"


@command("channel", usage="[channel_id]", help_="Show a channel's messages and whose turn it is")
async def channel(ctx: ShellContext, args: Args) -> str:
    channel_id = int(args.positional[0]) if args.positional else ctx.scratch.get("channel")
    if channel_id is None:
        return "no channel selected"
    res = await ctx.call("assistance.channel", {"channel_id": channel_id})
    ctx.scratch["channel"] = channel_id
    ch = res["channel"]
    names = ch.get("names", {})
    lines = [f"{m['sent_at'][11:16]}  {names.get(str(m['sender_account_id']), m['sender_account_id'])}: {m['body']}"
             for m in res["messages"]]
    state = "closed" if ch.get("closed_at") else ("your turn" if ch.get("my_turn") else "waiting for the other party")
    return f"channel {channel_id} -- {state}\n" + ("\n".join(lines) or "(no messages)")


@command("channels", help_="Channels you are a party to or listen on")
async def channels(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("assistance.channels"))["channels"],
                 ["id", "initiator_account_id", "superior_account_id", "turn", "opened_at", "closed_at"])


@command("close", "channel", "<channel_id>", "Close a channel (superior only)")
async def close_channel(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.close_channel", {"channel_id": args.get_int(0, "channel_id")})
    return f"channel {res['channel_id']} closed"


@command("listen", usage="<channel_id> <admin_account_id>", help_="Add an Admin as a silent Listener (the other party is not told)")
async def listen(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.add_listener", {"channel_id": args.get_int(0, "channel_id"),
                                                    "admin_account_id": args.get_int(1, "admin_account_id")})
    return "listener added" if res["added"] else "already listening"


@command("listeners", usage="<channel_id>", help_="Listeners YOU added to a channel")
async def listeners(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.my_listeners", {"channel_id": args.get_int(0, "channel_id")})
    return bullet(f"{l['name']} (account {l['listener_account_id']}) added {l['added_at']}" for l in res["listeners"])


