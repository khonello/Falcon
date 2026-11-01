"""An Admin's conversations in version 1 (ENGINE-GAPS #17): two people, or every Admin; no request first.

    chats                                  your conversations, latest first, with unread
    chat with <account_id> | pc=<pc_id> | admins     open (or make) the conversation; it becomes the one `chat send` uses
    chat send [conversation_id] <text...>  write in it (defaults to the last opened)
    chat <conversation_id>                 its messages, and who has read up to when
    chat who                               who you may write to
"""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, UsageError, command

_last: dict[str, int] = {}


def _title(c: dict) -> str:
    return f"conversation {c['conversation_id']} with {c['title'] or '?'}"


@command("chats", help_="Your conversations: other Admins, a machine's person, and every Admin")
async def chats(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("chat.list", {})
    rows = [{"id": c["conversation_id"], "with": c["title"], "unread": c["unread"] or "",
             "last": (f"{c['last']['from']}: {c['last']['body']}" if c["last"] else "")} for c in res["conversations"]]
    return table(rows, ["id", "with", "unread", "last"], width=50) if rows else "(none)"


@command("chat", "with", "<account_id> | pc=<pc_id> | admins", "Open the conversation with someone (made the first time), or with every Admin")
async def chat_with(ctx: ShellContext, args: Args) -> str:
    if args.positional and args.positional[0] == "admins":
        payload: dict = {"admins": True}
    elif args.opt("pc"):
        payload = {"pc_id": args.opt_int("pc")}
    else:
        payload = {"account_id": args.get_int(0, "account_id")}
    c = (await ctx.call("chat.open", payload))["conversation"]
    _last["id"] = c["conversation_id"]
    return _title(c)


@command("chat", "send", "[conversation_id] <text...>", "Write in a conversation (the last one opened if no id is given)")
async def chat_send(ctx: ShellContext, args: Args) -> str:
    words = list(args.positional)
    if words and words[0].isdigit():
        convo = int(words.pop(0))
    elif "id" in _last:
        convo = _last["id"]
    else:
        raise UsageError("open one first with `chat with ...`, or give its id")
    if not words:
        raise UsageError("write something to send")
    _last["id"] = convo
    res = await ctx.call("chat.send", {"conversation_id": convo, "body": " ".join(words)})
    return f"sent in conversation {convo} at {res['at']}"


@command("chat", "who", "", "Who you may write to")
async def chat_who(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("chat.people", {})
    rows = [{"id": p["account_id"], "name": p["name"], "role": p["role"], "machine": p["hostname"], "online": "yes" if p["online"] else ""}
            for p in res["people"]]
    return table(rows, ["id", "name", "role", "machine", "online"]) if rows else "(nobody)"


@command("chat", None, "<conversation_id>", "A conversation's messages, and who has read up to when (marks it read)")
async def chat_get(ctx: ShellContext, args: Args) -> str:
    convo = args.get_int(0, "conversation_id")
    res = await ctx.call("chat.get", {"conversation_id": convo})
    await ctx.call("chat.read", {"conversation_id": convo})
    _last["id"] = convo
    lines = [_title(res["conversation"])]
    lines.extend(f"{(m['at'] or '')[:16].replace('T', ' ')}  {m['from']}: {m['body']}" for m in res["messages"])
    lines.extend(f"read by {r['name']} up to {r['read_at'][:16].replace('T', ' ')}" for r in res["reads"] if r["read_at"])
    return "\n".join(lines)
