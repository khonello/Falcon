"""Flow: create (with consent / collision / cycle feedback), consent, edit, pause/resume/delete,
status with failure suggestions, history, manual trigger.

    flow create src=<pc_id>:<path> dest=<pc_id|remote>:<path>[@<stage#>] ... [stage=<type>[@<parent#>][:k=v,..]] [confirm]
      e.g. flow create src=2:C:/out dest=3:C:/in@1 dest=4:C:/in@2 stage=transformation:to=pdf stage=branch@0 stage=categorization@1:by=extension
    stages are numbered from 0 in the order given; `@n` attaches to stage n.
"""

from __future__ import annotations

from typing import Any

from operator_client.tui.render import kv, table
from operator_client.tui.shell import Args, ShellContext, UsageError, command


def _parse_structure(args: Args) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stages: list[dict[str, Any]] = []
    dests: list[dict[str, Any]] = []
    for spec in args.all("stage"):
        head, _, cfg = spec.partition(":")
        stype, _, parent = head.partition("@")
        config = dict(item.split("=", 1) for item in cfg.split(",") if "=" in item) if cfg else None
        stages.append({"stage_type": stype, "parent_index": int(parent) if parent else None, "config": config})
    for spec in args.all("dest"):
        target, _, parent = spec.partition("@")
        pc, _, path = target.partition(":")
        if not path:
            raise UsageError("dest must be <pc_id|remote>:<path>")
        dests.append({"destination_pc_id": None if pc == "remote" else int(pc), "destination_path": path,
                      "parent_index": int(parent) if parent else None})
    if not dests:
        raise UsageError("at least one dest=<pc_id>:<path> is required")
    return dests, stages


def _flow_text(flow: dict[str, Any]) -> str:
    out = kv(flow, skip=("stages", "destinations"))
    if flow.get("suggestion"):
        out += f"\nsuggestion: {flow['suggestion']}"
    out += "\n\nstages:\n" + table(flow.get("stages", []), ["id", "stage_type", "parent_stage_id", "config"])
    rows = []
    for d in flow.get("destinations", []):
        last = d.get("last_sync") or {}
        rows.append({"id": d["id"], "pc": d.get("destination_pc_id") or "remote", "path": d["destination_path"],
                     "stage": d.get("parent_stage_id"), "check": d.get("pre_flight_check_status"),
                     "paused": d.get("paused_reason"), "suggestion": d.get("suggestion"),
                     "last_sync": f"{last.get('written_by')} {last.get('content_hash', '')[:8]}" if last else None})
    out += "\n\ndestinations:\n" + table(rows)
    return out


@command("flow", "create", "src=<pc_id>:<path> dest=<pc|remote>:<path>[@stage#] [dest=..] [stage=<type>[@parent#][:k=v,..]] [confirm]",
         "Create a flow; consent / collision / cycle issues come back for you to resolve")
async def flow_create(ctx: ShellContext, args: Args) -> str:
    src = args.opt("src")
    if not src or ":" not in src:
        raise UsageError("src=<pc_id>:<path> required")
    pc, _, path = src.partition(":")
    dests, stages = _parse_structure(args)
    res = await ctx.call("flow.create", {"source_pc_id": int(pc), "source_path": path, "destinations": dests,
                                         "stages": stages, "confirm_collisions": args.flag("confirm")})
    f = res["flow"]
    out = f"flow {f['id']} {f['status']} (consent: {f['consent_status']})"
    if res["consent_pending"]:
        out += "\nwaiting for the destination owner's consent -- they will be asked"
    if res["collisions_confirmed"]:
        out += "\nyou confirmed existing content at: " + ", ".join(c["destination_path"] for c in res["collisions_confirmed"])
    return out + "\n" + _flow_text(f)


@command("flow", "consent", "<flow_id> yes|no", "Answer a consent request for a flow into your space")
async def flow_consent(ctx: ShellContext, args: Args) -> str:
    granted = args.get(1, "yes|no").lower() in ("yes", "y", "true", "1")
    res = await ctx.call("flow.consent", {"flow_id": args.get_int(0, "flow_id"), "granted": granted})
    return f"flow {res['flow_id']}: consent {'granted' if res['granted'] else 'denied'}"


@command("flow", "edit", "<flow_id> dest=.. [stage=..] [confirm]", "Replace a flow's destinations/stages (checks re-run)")
async def flow_edit(ctx: ShellContext, args: Args) -> str:
    dests, stages = _parse_structure(args)
    res = await ctx.call("flow.edit", {"flow_id": args.get_int(0, "flow_id"), "destinations": dests, "stages": stages,
                                       "confirm_collisions": args.flag("confirm")})
    return _flow_text(res["flow"])


@command("flow", "pause", "<flow_id>", "Pause a flow")
async def flow_pause(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("flow.pause", {"flow_id": args.get_int(0, "flow_id")})
    return f"flow {res['flow_id']} {res['status']}"


@command("flow", "resume", "<flow_id> [dest=<destination_id>]", "Resume a flow, or clear one destination's failure")
async def flow_resume(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("flow.resume", {"flow_id": args.get_int(0, "flow_id"), "destination_id": args.opt_int("dest")})
    for d in res["flow"]["destinations"]:
        ctx.state.clear_indicator(f"flow:{res['flow']['id']}:{d['id']}")
    return _flow_text(res["flow"])


@command("flow", "delete", "<flow_id>", "Deactivate a flow (history kept)")
async def flow_delete(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("flow.delete", {"flow_id": args.get_int(0, "flow_id")})
    return f"flow {res['flow_id']} {res['status']}"


@command("flows", help_="Flows you created, own a destination of, or that touch your department")
async def flows(ctx: ShellContext, args: Args) -> str:
    return table((await ctx.call("flow.list"))["flows"],
                 ["id", "status", "consent_status", "source_pc_id", "source_path", "pause_reason", "created_at"])


@command("flow", None, "<flow_id>", "A flow's status: destinations, failures, suggestions")
async def flow_status(ctx: ShellContext, args: Args) -> str:
    return _flow_text((await ctx.call("flow.status", {"flow_id": args.get_int(0, "flow_id")}))["flow"])


@command("flow", "history", "<flow_id>", "Sync log and conflicts")
async def flow_history(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("flow.history", {"flow_id": args.get_int(0, "flow_id")})
    return table(res["history"], ["occurred_at", "destination_path", "written_by", "content_hash", "conflict_resolved"])


@command("flow", "trigger", "<flow_id> <relative_path>", "Manually sync one file")
async def flow_trigger(ctx: ShellContext, args: Args) -> str:
    res = await ctx.call("flow.trigger", {"flow_id": args.get_int(0, "flow_id"), "relative_path": args.get(1, "relative_path")})
    return f"transfer {res['transfer_id'] or '(no active destinations)'}"

