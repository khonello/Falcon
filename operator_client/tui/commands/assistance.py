"""Assistance: search, people, ping (a message request), respond (accept), message channel, close.

No turn lock (22 Oct 2026): either side writes whenever they like. The Super User's ping to an Admin
opens the channel at once; everyone else's is a request the other person accepts."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


@command("search", usage="<query...>", help_="Search the Global File Index within your access tier")
async def search(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.search", {"query": args.rest(0, "query")})
    return table(res["results"], ["id", "pc_id", "path", "resource_tag", "resource_tag_scope_department_id", "last_seen_at"],
                 width=60)


@command("people", help_="Who you may message, and whether it is a request they accept first")
async def people(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.people")
    return table([{**p, "request": "yes" if p["request"] else "no, opens at once"} for p in res["people"]],
                 ["account_id", "name", "role", "department_name", "hostname", "request"])


@command("ping", usage="<account_id>", help_="Ask someone to talk (a request; repeatable). The Super User to an Admin opens it at once")
async def ping(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.ping", {"to_account_id": args.get_int(0, "account_id")})
    if res.get("channel_id"):
        ctx.scratch["channel"] = res["channel_id"]
        return f"channel {res['channel_id']} {'opened' if res['opened'] else 'already open'}  (use: msg <text>)"
    return f"request {res['ping_id']} sent -- they see it until they accept"


@command("pings", help_="Requests waiting for you to accept (the pulsing indicator)")
async def pings(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.ping_status")
    await ctx.state.on_push("assistance.ping_status", {"unaddressed": res["unaddressed"]})
    return f"{res['unaddressed']} unaddressed\n" + table(res["pings"], ["id", "from_name", "sender_account_id", "sent_at"])


@command("respond", usage="<ping_id>", help_="Accept a request: addresses it and opens (or returns) the channel")
async def respond(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.respond", {"ping_id": args.get_int(0, "ping_id")})
    ctx.scratch["channel"] = res["channel_id"]
    return (f"channel {res['channel_id']} {'opened' if res['opened'] else 'already open'}  "
            f"(use: msg <text> / channel {res['channel_id']})")


@command("msg", usage="[channel_id] <text...>", help_="Post a message; channel defaults to the last used")
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
    return f"sent (message {res['message_id']})"


@command("channel", usage="[channel_id]", help_="Show a channel's messages and who it waits on")
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
    state = "closed" if ch.get("closed_at") else ("waiting on you" if ch.get("my_turn") else "waiting on them")
    return f"channel {channel_id} -- {state}\n" + ("\n".join(lines) or "(no messages)")


@command("channels", help_="Channels you are a party to")
async def channels(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("assistance.channels"))["channels"],
                 ["id", "initiator_account_id", "superior_account_id", "opened_at", "closed_at"])


@command("close", "channel", "<channel_id>", "Close a channel (the superior, or either of two Admins)")
async def close_channel(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("assistance.close_channel", {"channel_id": args.get_int(0, "channel_id")})
    return f"channel {res['channel_id']} closed"
