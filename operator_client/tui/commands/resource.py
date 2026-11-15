"""Resource: violations, resolve, tag."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


@command("violations", usage="[all]", help_="Resource violations you can see (`all` includes resolved)")
async def violations(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.violations", {"include_resolved": args.flag("all")})
    return table(res["violations"], ["id", "hostname", "filename", "expected_tag", "detected_via", "detected_at",
                                     "resolved_at", "report_id", "path"], width=70)


@command("violation", "resolve", "<violation_id>", "Mark a violation rectified; the file stops being ignored")
async def violation_resolve(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.resolve", {"violation_id": args.get_int(0, "violation_id")})
    ctx.state.clear_indicator(f"violation:{res['violation_id']}")
    return f"violation {res['violation_id']} resolved"


@command("tag", usage="<file_index_id> admin|restricted|worker_dept|common [dept=<id>]",
         help_="Classify an indexed file explicitly (admin tier: whoever heads the organisation)")
async def tag(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.tag", {"file_index_id": args.get_int(0, "file_index_id"), "tag": args.get(1, "tag"),
                                          "scope_department_id": args.opt_int("dept")})
    return f"file {res['file_index_id']} tagged {res['tag']}"


@command("shelves", help_="The tiers you keep, with how many files sit on each")
async def shelves(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.shelves")
    return "\n".join(f"{s['folder']:<12} {s['files']} file(s)" for s in res["shelves"])


@command("journey", usage="<file_index_id>",
         help_="A file's journey: where its content has been and what was done about it, oldest first")
async def journey(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("resource.journey", {"file_index_id": args.get_int(0, "file_index_id")})
    f = res["file"]
    head = f"{f['filename']}  (tag: {f['tag'] or 'none'})  on {len(res['places'])} place(s)"
    lines = [f"{e['at'][:16].replace('T', ' ')}  {e['kind']:<10} {e['text']}" for e in res["events"]]
    return "\n".join([head, ""] + lines)


@command("lineage", usage="<file_index_id>",
         help_="The file this place holds: every place it has been, however it was renamed, moved or saved, and its copies")
async def lineage(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("index.lineage", {"file_index_id": args.get_int(0, "file_index_id")})
    lin = res["lineage"]
    head = f"{lin['first_name']}: first seen {lin['first_seen_at'][:16].replace('T', ' ')} at {lin['first_path']}" + (f" (a copy of file {lin['copy_of']})" if lin["copy_of"] else "")
    lines = [f"  {p['first_seen_at'][:16].replace('T', ' ')}  {p['hostname'] or '?'}  {p['path']}  {p['how']}{'  (left)' if p['gone_at'] else ''}" for p in res["places"]]
    copies = [f"  copy: {c['first_name']} at {c['first_path']} ({c['began_by']})" for c in res["copies"]]
    return "\n".join([head, *lines, *copies])


@command("marks", usage="[all|department]", help_="Protected files: marked where they are, restricted, private or watched")
async def marks_list(ctx: ShellContext, args: Args) -> str:
    scope = args.positional[0] if args.positional and args.positional[0] in ("all", "department") else "mine"
    res = await ctx.call("marks.list", {"scope": scope})
    rows = [{"id": m["id"], "code": m["code"], "kind": m["kind"], "as": m.get("protection") or "restricted", "name": m["name"], "on": m["host"],
             "allowed": m["keep_label"] if (m.get("protection") or "restricted") == "restricted" else
             f"{len(m.get('readers') or [])} may open it" if m.get("protection") == "private" else "anyone (noted)",
             "files": m["files"], "versions": m["versions"], "copies": m["copies"], "worst": m["worst"] or ""} for m in res["marks"]]
    s = res["summary"]
    return (f"{s['marks']} marks, {s['files']} files, {s['copies']} copies found elsewhere\n\n"
            + (table(rows, ["id", "code", "kind", "as", "name", "on", "allowed", "files", "versions", "copies", "worst"]) if rows else "(none)"))


@command("mark", "assess", "<path> [<path>...]", "What marking these would cost, before doing it: files, how long, and whether it is too large")
async def mark_assess(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.assess", {"paths": list(args.positional)})
    lines = [f"this machine tracks {res['tracked_now']:,} files by content now (most it can: {res['machine_limit']:,})"]
    for a in res["assessed"]:
        lines.append(f"{a['path']}: {a['verdict'].upper().replace('_', ' ')} - {a['files']:,} files ({a['tracked']:,} tracked, {a['junk']:,} generated), about {a['seconds']:.0f}s")
        lines += [f"    {r}" for r in a["reasons"]]
    return "\n".join(lines)


def _ids(raw: str | None) -> list[int]:
    try:
        return [int(x) for x in (raw or "").split(",") if x.strip()]
    except ValueError as exc:
        raise UsageError("readers are account ids separated by commas, e.g. readers=21,27") from exc


@command("mark", usage="<path> [<path>...] [as=restricted|private|watch] [keep=machine|path] [readers=<id>,<id>] [system=0] [confirm_large=1]",
         help_="Protect files or folders where they are (nothing is moved): restricted (the default), private to the people named, or watched")
async def mark_create(ctx: ShellContext, args: Args) -> str:
    prot = args.opt("as") or "restricted"
    payload: dict = {"paths": list(args.positional), "protection": prot, "keep": args.opt("keep") or "machine", "confirm_large": bool(args.opt("confirm_large"))}
    if prot == "private":
        payload["readers"] = _ids(args.opt("readers"))
        payload["allow_system"] = args.opt("system") not in ("0", "no", "false")
    res = await ctx.call("marks.create", payload)

    def said(m: dict) -> str:
        if m.get("protection") == "private":
            return "private, " + (", ".join(r["name"] or f"account {r['account_id']}" for r in m.get("readers") or []) or "only you") + " may open it"
        if m.get("protection") == "watch":
            return "watched, every change, copy and move noted"
        return f"kept to {m['keep_label'].lower()}"
    return "\n".join(f"{m['code']} {m['kind']} {m['name']} on {m['host']}: {m['files']} file(s), {said(m)}" for m in res["marks"]) \
        + (f"\n{res['copies_found']} copy(ies) already elsewhere" if res["copies_found"] else "")


@command("mark", "readers", "<mark_id> <id>,<id>... [system=0]", "Change who may open a private file or folder (account ids; you are always one)")
async def mark_readers(ctx: ShellContext, args: Args) -> str:
    payload: dict = {"mark_id": args.get_int(0, "mark_id"), "readers": _ids(args.positional[1] if len(args.positional) > 1 else "")}
    if args.opt("system") is not None:
        payload["allow_system"] = args.opt("system") not in ("0", "no", "false")
    res = await ctx.call("marks.readers", payload)
    return (f"M-{res['mark_id']}: accounts {', '.join(str(a) for a in res['readers'])} may open it"
            + ("" if res["allow_system"] else "; the system account may not") + ("" if res["applied_now"] else " (its machine is told when it connects)"))


@command("mark", "show", "<mark_id>", "One mark: where it is allowed, its copies, and what changing it would do")
async def mark_show(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.get", {"mark_id": args.get_int(0, "mark_id")})
    m, ch = res["mark"], res["change"]
    prot = m.get("protection") or "restricted"
    if prot != "restricted":
        out = [f"{m['code']} {m['name']} on {m['host']}: {prot}, {m['files']} file(s)"]
        if prot == "private":
            a = m.get("applied") or {}
            out.append("may open it: " + (", ".join(r["name"] or f"account {r['account_id']}" for r in m.get("readers") or []) or "only whoever made it private")
                       + ("" if m.get("allow_system", True) else "; the system account may not"))
            out.append("on the machine: " + ("set" if a.get("ok") else a.get("waiting") or a.get("error") or "not yet"))
            out.append("refused:\n" + ("\n".join(f"  {r['at'][:16].replace('T', ' ')}  {r['who'] or 'someone'}  {r['process'] or ''}" for r in m.get("refusals") or []) or "  nobody"))
        out.append("lately:\n" + ("\n".join(f"  {e['at'][:16].replace('T', ' ')}  {e.get('who') or ''} {e['what']}" for e in res.get("lately") or []) or "  nothing"))
        return "\n".join(out)
    out = [f"{m['code']} {m['name']} on {m['host']}: {m['keep_label']}, {m['files']} file(s), {m['versions']} version(s)"]
    out.append("copies elsewhere:\n" + (table([{"issue": c["code"], "severity": c["severity"], "on": c["host"], "file": c["file"],
                                               "signed in": c["signed_in"] or "", "state": c["label"]} for c in res["copies"]],
                                              ["issue", "severity", "on", "file", "signed in", "state"]) if res["copies"] else "  none"))
    out.append(f"if kept to {ch['keep_label'].lower()}: {ch['effect']['would_flag']} more would be caught, {ch['effect']['would_clear']} would stop being caught")
    return "\n".join(out)


@command("mark", "keep", "<mark_id> machine|path", "Change where a mark allows its content")
async def mark_keep(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.change_keep", {"mark_id": args.get_int(0, "mark_id"), "keep": args.get(1, "machine|path")})
    return f"{res['mark']['code']} is now kept to {res['mark']['keep_label'].lower()}: {res['flagged']} caught, {res['cleared']} cleared"


@command("mark", "remove", "<mark_id>", "Stop restricting a file or folder (its open copy issues close)")
async def mark_remove(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.unmark", {"mark_id": args.get_int(0, "mark_id")})
    return f"unmarked; {res['copies_closed']} copy issue(s) closed"
