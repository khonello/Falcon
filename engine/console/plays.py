"""What can be done about an issue: the options an Admin is offered, and doing them.

`build(ctx, issue)` says what the issue means in plain words (a lead and its facts), what can be done now and why something cannot.
`act(ctx, issue, key, payload)` does one of those things -- through the combos' own handlers where there is one (a flow's delete, a
traversal), so permissions and the audit trail stay in one place -- and records it in the issue's timeline.

An option is {key, title, desc, verb, done, need?, pick?, hint?}: `done` is where the issue goes ("Waiting" or "Resolved"), `need` what
the person must give first (a reason, a message, a pick from `pick`: [{value, label}]).
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, dispatch
from protocol import ErrorCode, ProtocolError

Option = dict[str, Any]


def _opt(key: str, title: str, desc: str, verb: str, done: str, need: str | None = None, pick: list[dict[str, Any]] | None = None,
         hint: str | None = None) -> Option:
    o: Option = {"key": key, "title": title, "desc": desc, "verb": verb, "done": done}
    if need:
        o["need"] = need
    if pick is not None:
        o["pick"] = pick
        o["hint"] = hint
    return o


def _reason(payload: dict[str, Any]) -> str:
    reason = " ".join(str(payload.get("reason") or "").split())[:300]
    if not reason:
        raise ProtocolError(ErrorCode.INVALID, "this needs a reason")
    return reason


async def _person(ctx: Context, issue: dict[str, Any]) -> tuple[int | None, str | None, bool]:
    """(account, name, online) of the person who owns the issue's machine."""
    if issue["pc_id"] is None:
        return None, None, False
    pc = await ctx.engine.db.accounts.pc(issue["pc_id"])
    if not pc or not pc["bound_account_id"]:
        return None, None, False
    names = await ctx.engine.db.accounts.display_names_for(ctx.identity.account_id, [pc["bound_account_id"]])
    return pc["bound_account_id"], names.get(pc["bound_account_id"]), issue["pc_id"] in ctx.engine.online_pc_ids()


async def build(ctx: Context, issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[Option], list[str]]:
    builder = {"file": _file, "update": _update, "deviation": _deviation, "flow": _flow, "offline": _offline}[issue["type"]]
    return await builder(ctx, issue)


async def act(ctx: Context, issue: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any]:
    _, _, options, _ = await build(ctx, issue)
    if key not in {o["key"] for o in options}:
        raise ProtocolError(ErrorCode.INVALID, f"{key!r} is not something that can be done about this issue now")
    doer = {"file": _do_file, "update": _do_update, "deviation": _do_deviation, "flow": _do_flow, "offline": _do_offline}[issue["type"]]
    return await doer(ctx, issue, key, payload)


async def _wait(ctx: Context, issue: dict[str, Any], label: str, text: str) -> dict[str, Any]:
    await ctx.engine.db.issues.set_state(issue["id"], "waiting", label)
    await ctx.engine.db.issues.log(issue["id"], "acted", text, (ctx.viewed_by or ctx.identity).account_id)
    return {"state": "waiting", "label": label}


async def _finish(ctx: Context, issue: dict[str, Any], resolution: str) -> dict[str, Any]:
    from engine.console.issues import resolve_issue

    await resolve_issue(ctx.engine, issue["id"], resolution, by=ctx)
    return {"state": "resolved", "label": "Resolved"}


# --- a restricted file copied ---------------------------------------------------------------------

async def _file(ctx: Context, issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[Option], list[str]]:
    d, host = issue["detail"], issue["hostname"] or "a machine"
    _, person, online = await _person(ctx, issue)
    mark = d.get("mark") or {}
    if mark:
        home = mark.get("host") if mark.get("keep") == "machine" else f"{mark.get('host')} {mark.get('path', '')}".strip()
        lead = (f"A copy of a file marked restricted is on {host}. It is kept to "
                f"{'the machine ' + str(mark.get('host')) if mark.get('keep') == 'machine' else 'one place on ' + str(mark.get('host'))}, "
                "so nowhere else may have it.")
        facts = [["File", d.get("file")], ["Found in", d.get("folder")], ["Size", d.get("size") or "—"], ["Allowed only on", home],
                 ["Marked by", mark.get("by") + (f", as part of {mark.get('path')}" if mark.get("kind") == "folder" else "")]]
    else:
        lead = f"A copy of a restricted file is on {host}, where its tier does not allow it."
        facts = [["File", d.get("file")], ["Found in", d.get("folder")], ["Tier", d.get("tag") or "restricted"]]
    can_reach = issue["pc_id"] in ctx.engine.online_pc_ids()
    why: list[str] = []
    options: list[Option] = []
    if person and online:
        options.append(_opt("ask", f"Ask {person} to delete it", f"{person} sees which file and why. The issue closes on its own when the copy is gone.",
                            "Ask", "Waiting"))
    elif not person:
        why.append("Nobody is signed in, so there is nobody to tell.")
    if can_reach:
        options.append(_opt("delete", "Delete this copy", f"Deletes it from {host} only. The original is not touched.", "Delete copy", "Waiting"))
    else:
        why.append(f"{host} is offline, so the copy cannot be deleted from here.")
    options.append(_opt("allow", f"Allow it on {host} too", "Adds this one place to what is allowed, with your reason. It is not reported again.",
                        "Allow it", "Resolved", need="reason"))
    return lead, facts, options, why


async def _do_file(ctx: Context, issue: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any]:
    db, d = ctx.engine.db, issue["detail"]
    host = issue["hostname"] or "the machine"
    who = (ctx.viewed_by or ctx.identity).account_id
    if key == "ask":
        account, person, _ = await _person(ctx, issue)
        await ctx.engine.push_to_account(account, "issue.ask_delete", {
            "issue_id": issue["id"], "file": d.get("file"), "folder": d.get("folder"),
            "why": "It is a restricted file, and it is not allowed on this machine."})
        return await _wait(ctx, issue, "Waiting", f"Asked {person} to delete the copy of {d.get('file')}")
    if key == "delete":
        from engine.console.system_actions import run_on_machine

        execution_id = await run_on_machine(ctx, "delete_file", {"path": d["path"]}, issue["pc_id"],
                                            name=f"Delete a restricted copy ({issue['code']})")
        await db.issues.set_detail(issue["id"], {"executions": [*d.get("executions", []), execution_id]})
        return await _wait(ctx, issue, "Waiting", f"Deleting the copy of {d.get('file')} on {host}")
    reason = _reason(payload)
    await db.resource.allow(issue["pc_id"], d["path"], d.get("hash"), who, reason, d.get("mark", {}).get("id"))
    if d.get("violation_id"):
        await db.resource.resolve(d["violation_id"])
    await db.issues.log(issue["id"], "acted", f"Allowed {d.get('file')} on {host}: {reason}", who)
    return await _finish(ctx, issue, f"Allowed on {host}: {reason}")


# --- a stuck or failed update ---------------------------------------------------------------------

async def _update(ctx: Context, issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[Option], list[str]]:
    d, host = issue["detail"], issue["hostname"] or "a machine"
    online = issue["pc_id"] in ctx.engine.online_pc_ids()
    escalated = issue["escalated_at"] is not None
    lead = f"{host} is on {d.get('current') or 'an unknown version'} and should be on {d.get('target')}."
    if issue["department_id"] is not None and issue["owner_account_id"] is None and escalated:
        lead += f" {issue['department_name']} has no Admin, so it came to you."
    facts: list[list[Any]] = [["Running", d.get("current") or "unknown"], ["Should run", d.get("target")],
                              ["Attempts", d.get("attempts") if d.get("attempts") is not None else "none yet"]]
    if d.get("last_attempt_at"):
        facts.append(["Last attempt", d["last_attempt_at"]])
    if not online:
        facts.append(["Offline", "yes, since it last checked in"])
    why: list[str] = [] if online else [f"{host} is offline, so it can only retry when it is back."]
    options: list[Option] = []
    if online:
        options.append(_opt("idle", "Retry when it is idle", "The default: the machine retries by itself in its next idle window.", "Keep this", "Waiting"))
        options.append(_opt("now", "Retry now", "Whoever is signed in may see a restart prompt.", "Retry now", "Waiting"))
    else:
        options.append(_opt("wait", "Retry when it is back online", f"The update runs as soon as {host} checks in again.", "Keep waiting", "Waiting"))
    options.append(_opt("exclude", "Leave it out of the next version's gate", f"The next version can then be approved without {host}. It stays on "
                        f"{d.get('current') or 'its version'} until it updates.", "Leave it out", "Resolved", need="reason"))
    return lead, facts, options, why


async def _do_update(ctx: Context, issue: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any]:
    db, host = ctx.engine.db, issue["hostname"] or "the machine"
    who = (ctx.viewed_by or ctx.identity).account_id
    if key == "now":
        await ctx.engine.push_to_pc(issue["pc_id"], "update.available", {"version": issue["detail"].get("target"), "now": True})
        return await _wait(ctx, issue, "Retrying", f"Asked {host} to retry the update now")
    if key in ("idle", "wait"):
        return await _wait(ctx, issue, "Retrying", f"Left {host} to retry when {'idle' if key == 'idle' else 'it is back online'}")
    reason = _reason(payload)
    await db.updates.exclude_from_gate(issue["pc_id"], "next", reason, who)
    await db.issues.log(issue["id"], "acted", f"Left {host} out of the next version's gate: {reason}", who)
    return await _finish(ctx, issue, f"Left out of the next version's gate: {reason}")


# --- a machine that presented another name --------------------------------------------------------

async def _deviation(ctx: Context, issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[Option], list[str]]:
    d, host = issue["detail"], issue["hostname"] or "a machine"
    lead = f"{host} presented a name that does not match what it was registered with."
    facts = [["Registered as", d.get("expected")], ["Presented", d.get("presented")], ["First seen", issue["opened_at"].isoformat()]]
    options = [
        _opt("accept", f"Accept {d.get('presented')}", f"Registers the machine as {d.get('presented')}.", "Accept", "Resolved"),
        _opt("reverse", f"Put it back to {d.get('expected')}", f"Waits for the machine to present {d.get('expected')} again; the issue closes when it does.",
             "Put it back", "Waiting")]
    return lead, facts, options, []


async def _do_deviation(ctx: Context, issue: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any]:
    d, who = issue["detail"], (ctx.viewed_by or ctx.identity).account_id
    if key == "accept":
        await ctx.engine.db.accounts.rename_pc(issue["pc_id"], d["presented"])
        await ctx.engine.audit.record(ctx, "pc.renamed", target_type="pcs", target_id=issue["pc_id"],
                                      detail={"from": d.get("expected"), "to": d["presented"]})
        await ctx.engine.db.issues.log(issue["id"], "acted", f"Registered the machine as {d['presented']}", who)
        return await _finish(ctx, issue, f"Accepted {d['presented']}")
    return await _wait(ctx, issue, "Waiting", f"Waiting for the machine to present {d.get('expected')} again")


# --- a flow waiting for someone to agree ----------------------------------------------------------

async def _flow(ctx: Context, issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[Option], list[str]]:
    d = issue["detail"]
    who = d.get("consent_by") or "the destination's owner"
    lead = f"Flow {d.get('flow_id')} starts when {who} agrees to receive it. Agreeing is how they allow it."
    facts = [["Flow", f"#{d.get('flow_id')}"], ["From", d.get("from")], ["To", d.get("to")], ["Asked", d.get("asked_at")]]
    mine = sorted((p for p in await ctx.engine.db.accounts.pcs_in_department(issue["department_id"])
                   if p["bound_account_id"] and p["id"] != issue["pc_id"]), key=lambda p: p["hostname"]) \
        if issue["department_id"] is not None else []
    options = [
        _opt("remind", f"Remind {who}", "Sends the request again.", "Remind", "Waiting"),
        _opt("dest", "Send it somewhere you manage instead", "A machine in your own department needs nobody to agree.", "Change it", "Resolved",
             need="pick", pick=[{"value": p["id"], "label": p["hostname"]} for p in mine], hint="Pick a destination"),
        _opt("withdraw", "Withdraw the flow", "Nothing has been copied yet. The request is closed.", "Withdraw", "Resolved")]
    return lead, facts, options, []


async def _do_flow(ctx: Context, issue: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any]:
    db, d = ctx.engine.db, issue["detail"]
    who = (ctx.viewed_by or ctx.identity).account_id
    flow_id = d["flow_id"]
    if key == "remind":
        await ctx.engine.push_to_account(d.get("consent_account_id"), "flow.consent_request",
                                         {"flow_id": flow_id, "from_account_id": who, "reminder": True})
        return await _wait(ctx, issue, "Waiting", f"Reminded {d.get('consent_by')}")
    if key == "withdraw":
        await dispatch(ctx, "flow.delete", {"flow_id": flow_id})
        await db.issues.log(issue["id"], "acted", f"Withdrew flow {flow_id}", who)
        return await _finish(ctx, issue, f"Withdrew flow {flow_id}")
    pc_id = payload.get("pick")
    if not isinstance(pc_id, int):
        raise ProtocolError(ErrorCode.INVALID, "pick a destination")
    shape = (await db.flows.shapes([flow_id]))[flow_id]
    index = {s["id"]: i for i, s in enumerate(shape["stages"])}
    dests = []
    for dest in shape["destinations"]:
        if dest["destination_pc_id"] == d.get("destination_pc_id"):
            dest = {**dest, "destination_pc_id": pc_id}
        dests.append({"destination_pc_id": dest["destination_pc_id"], "destination_path": dest["destination_path"],
                      "parent_index": index.get(dest.get("parent_stage_id"))})
    stages = [{"stage_type": s["stage_type"], "parent_index": index.get(s.get("parent_stage_id")), "config": s.get("config")}
              for s in shape["stages"]]
    await dispatch(ctx, "flow.edit", {"flow_id": flow_id, "destinations": dests, "stages": stages, "confirm_collisions": True})
    await db.flows.set_consent(flow_id, "not_required")
    await db.flows.set_status(flow_id, "active", None)
    host = next((p["hostname"] for p in await db.accounts.pcs_in_department(issue["department_id"]) if p["id"] == pc_id), "another machine")
    await db.issues.log(issue["id"], "acted", f"Sent flow {flow_id} to {host} instead", who)
    return await _finish(ctx, issue, f"Sent to {host} instead")


# --- a machine that stopped checking in -----------------------------------------------------------

async def _offline(ctx: Context, issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[Option], list[str]]:
    d, host = issue["detail"], issue["hostname"] or "a machine"
    lead = f"{host} has not checked in since {d.get('last_seen_at')}."
    return lead, [["Last seen", d.get("last_seen_at")]], [], [f"{host} can only be reached once it is back online; this closes by itself then."]


async def _do_offline(ctx: Context, issue: dict[str, Any], key: str, payload: dict[str, Any]) -> dict[str, Any]:
    raise ProtocolError(ErrorCode.INVALID, "there is nothing to do about a machine that is offline but wait")

