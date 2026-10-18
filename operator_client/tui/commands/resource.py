"""Resource: violations, resolve, tag."""

from __future__ import annotations

from operator_client.tui.render import table
from operator_client.tui.shell import Args, ShellContext, command


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
         help_="Classify an indexed file explicitly (admin tier: Super User only)")
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


@command("marks", usage="[all|department]", help_="Restricted marks: files and folders marked where they are")
async def marks_list(ctx: ShellContext, args: Args) -> str:
    scope = args.positional[0] if args.positional and args.positional[0] in ("all", "department") else "mine"
    res = await ctx.call("marks.list", {"scope": scope})
    rows = [{"id": m["id"], "code": m["code"], "kind": m["kind"], "name": m["name"], "on": m["host"], "allowed": m["keep_label"],
             "files": m["files"], "versions": m["versions"], "copies": m["copies"], "worst": m["worst"] or ""} for m in res["marks"]]
    s = res["summary"]
    return (f"{s['marks']} marks, {s['files']} files, {s['copies']} copies found elsewhere\n\n"
            + (table(rows, ["id", "code", "kind", "name", "on", "allowed", "files", "versions", "copies", "worst"]) if rows else "(none)"))


@command("mark", "assess", "<path> [<path>...]", "What marking these would cost, before doing it: files, how long, and whether it is too large")
async def mark_assess(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.assess", {"paths": list(args.positional)})
    lines = [f"this machine tracks {res['tracked_now']:,} files by content now (most it can: {res['machine_limit']:,})"]
    for a in res["assessed"]:
        lines.append(f"{a['path']}: {a['verdict'].upper().replace('_', ' ')} - {a['files']:,} files ({a['tracked']:,} tracked, {a['junk']:,} generated), about {a['seconds']:.0f}s")
        lines += [f"    {r}" for r in a["reasons"]]
    return "\n".join(lines)


@command("mark", usage="<path> [<path>...] [keep=machine|path] [confirm_large=1]", help_="Mark files or folders restricted, where they are (nothing is moved)")
async def mark_create(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.create", {"paths": list(args.positional), "keep": args.opt("keep") or "machine", "confirm_large": bool(args.opt("confirm_large"))})
    return "\n".join(f"{m['code']} {m['kind']} {m['name']} on {m['host']}: {m['files']} file(s), kept to {m['keep_label'].lower()}" for m in res["marks"]) \
        + (f"\n{res['copies_found']} copy(ies) already elsewhere" if res["copies_found"] else "")


@command("mark", "show", "<mark_id>", "One mark: where it is allowed, its copies, and what changing it would do")
async def mark_show(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("marks.get", {"mark_id": args.get_int(0, "mark_id")})
    m, ch = res["mark"], res["change"]
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
