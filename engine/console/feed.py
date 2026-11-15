"""The audit trail as events the console can show (Audit log, Overview's live activity, a machine's events, an issue's story).

An audit row is `action_type + target + detail`. The console wants an event: a **kind** to colour and filter by, one plain **sentence**,
the **machine**, the **person**, and how much it matters (**level**). This module is the one place that turns one into the other, for the
reader (`audit.events`, `audit.summary`, `audit.export`) and for the live push (`audit.event`, sent by the audit trail itself).

THE CATALOGUE (the user, 10 Nov 2026: the log read as one message repeated, in words nobody could follow). Every action the Engine records
has one entry in `ENTRIES`: its kind, its level and its sentence, and `tests/test_audit_words.py` fails when something is recorded that has
none, so an entry never falls back to its code name again. A sentence says what was done to which thing, where, as the person reading it
would say it -- the actor is shown beside it, so it starts with the verb: "Gave Kojo a task: Write the weekly sales summary". Things are
named, not numbered: a flow, task, rule, issue or mark is looked up by its id when the entry is read (`AuditRepo.labels`), a path is cut
to its file name.

Levels:
    worth     something someone should look at (a copy caught, a deadline passed, a refusal, a failure)
    done      what people and Falcon did (gave a task, made a flow, entered a machine)
    routine   the machinery: kept in the trail, shown only under Everything and on a machine's own page (connections, each file a flow
              carried, catch-ups)
Some entries repeat another one: a copy caught writes the copy, its issue and the built-in rule's deviation. The copy is the line; the
other two are `routine` (`_level`).
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.isotime import parse_iso
from engine.permissions import int_field, kept, require_role
from protocol import ErrorCode, ProtocolError

KINDS = ("session", "action", "flow", "violation", "protected", "task", "issue", "message", "detective", "deviation", "rollout",
         "report", "assistance", "admin", "system")


class W:
    """What a sentence is made from: the row's detail, its machine, its people and the thing it is about, named for the reader."""

    def __init__(self, row: dict[str, Any], host: str | None, names: dict[int, str], things: dict[tuple[str, int], dict[str, Any]], viewer: int):
        self.d: dict[str, Any] = row.get("detail") or {}
        self.host = host
        self.on = f" on {host}" if host else ""
        self.names = names
        self.viewer = viewer
        self.target_type = row.get("target_type")
        self.target_id = _id(row.get("target_id"))
        self.things = things

    def who(self, account_id: Any, default: str = "someone") -> str:
        if not isinstance(account_id, int):
            return default
        return "you" if account_id == self.viewer else self.names.get(account_id) or default

    def thing(self, kind: str | None = None, key: str | None = None) -> dict[str, Any]:
        """The thing this row is about (its target), or the one its detail names under `key`."""
        kind = kind or self.target_type
        tid = self.d.get(key) if key else self.target_id
        return self.things.get((str(kind), tid), {}) if isinstance(tid, int) else {}

    def flow(self) -> str:
        f = self.thing("flows", "flow_id") or self.thing("flow_destinations") or self.thing("flows")
        return f.get("label") or (f"flow {self.d['flow_id']}" if self.d.get("flow_id") else "a flow")

    def task(self) -> str:
        return _q(self.thing("tasks").get("label") or "a task")


def _id(raw: Any) -> int | None:
    """audit_log.target_id is text (a client id is one); a number is a number."""
    if isinstance(raw, int):
        return raw
    return int(raw) if isinstance(raw, str) and raw.isdigit() else None


def _file(path: Any) -> str:
    s = str(path or "").replace("\\", "/").rstrip("/")
    return s.rsplit("/", 1)[-1] or s


def _q(text: Any, n: int = 70) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _n(n: Any, word: str, plural: str | None = None) -> str:
    try:
        k = int(n)
    except (TypeError, ValueError):
        return f"some {plural or word + 's'}"
    return f"{k:,} {word if k == 1 else plural or word + 's'}"


_PROT = {"private": ("Made {f} private", "Stopped keeping {f} private"), "watch": ("Started watching {f}", "Stopped watching {f}")}


def _mark(w: W, made: bool) -> str:
    m = w.thing("resource_marks")
    prot = w.d.get("protection") or m.get("protection") or "restricted"
    f = _file(w.d.get("path")) or m.get("label") or "a file"
    words = _PROT.get(prot, ("Restricted {f}", "Stopped restricting {f}"))
    return words[0 if made else 1].format(f=f) + w.on


def _deviation(w: W) -> str:
    dv = w.thing("deviations")
    if not dv:
        return f"An Automation rule saw something it did not expect{w.on}"
    short = str(dv.get("short") or "").replace("{who}", w.who(dv.get("subject_account_id"), dv.get("subject_host") or w.host or "a machine"))
    return f"Rule “{_q(dv.get('rule') or dv.get('rule_code') or 'a rule', 50)}” was not met: {_q(short, 60)}" + (f" ({_q(dv['happened'], 50)})" if dv.get("happened") else "")


def _issue(w: W) -> str:
    i = w.thing("issues")
    return _q(i.get("label") or w.d.get("title") or "an issue", 60) + (f" ({_q(i['subject'], 40)})" if i.get("subject") else "")


def _action(w: W) -> str:
    a = w.thing("execution") or w.thing("actions") or w.thing("actions", "action_id")
    return "“" + _q(a.get("label") or "an action", 40) + "”"


def _rule(w: W) -> str:
    r = w.thing("event_definitions") or w.thing("rules")
    return "“" + _q(r.get("label") or w.d.get("name") or w.d.get("code") or "a rule", 50) + "”"


def _alert(w: W) -> str:
    return "“" + _q(w.thing("system_alerts").get("label") or w.d.get("title") or "an announcement", 50) + "”"


def _person(w: W, key: str | None = None) -> str:
    if key:
        return w.who(w.d.get(key))
    return w.who(w.target_id) if w.target_type == "accounts" else "someone"


# what an Admin chose on an issue (engine/console/plays.py's option keys), as done
_CHOSE = {"delete": "Deleted the copy", "allow": "Allowed the copy where it is", "ask": "Asked the person to delete the copy",
          "rule": "Deleted the copy and made a rule", "accept": "Accepted the new name", "reverse": "Put the old name back",
          "remind": "Sent a reminder", "withdraw": "Withdrew the flow", "dest": "Sent the flow elsewhere",
          "keep_copies": "Kept the copies", "remove_copies": "Removed the copies", "now": "Retried the update now",
          "idle": "Left the update to retry when idle", "wait": "Left the update to retry when the machine is back",
          "exclude": "Left the machine out of the update", "admin": "Sent it to an Admin"}

S = Callable[[W], str]
# action type -> (kind, level, sentence)
ENTRIES: dict[str, tuple[str, str, S]] = {
    # --- going into machines ------------------------------------------------------------------------------------------------------
    "session.traversed": ("session", "done", lambda w: f"Entered {w.host or 'a machine'}" + (" (outside working hours)" if w.d.get("outside_hours") else "")),
    "session.ended": ("session", "done", lambda w: {"superior_ended": f"Another Admin ended the session{w.on}", "expired": f"The session{w.on} timed out"}.get(
        str(w.d.get("reason")), f"Left {w.host or 'the machine'}")),
    "session.extended": ("session", "done", lambda w: f"Gave the session{w.on} more time"),
    "session.mode_changed": ("session", "done", lambda w: f"Took control of {w.host or 'the machine'}" if w.d.get("mode") == "control" else f"Went back to watching {w.host or 'the machine'}"),
    "session.screen_started": ("session", "routine", lambda w: f"Started seeing the screen{w.on}"),
    "session.screen_stopped": ("session", "routine", lambda w: f"Stopped seeing the screen{w.on}"),
    "execution.image_viewed": ("session", "done", lambda w: f"Looked at a screenshot{w.on}"),
    # --- actions and Automation ---------------------------------------------------------------------------------------------------
    "action.started": ("action", "done", lambda w: f"Ran {_action(w)}{w.on}" + (" (an Automation rule)" if w.d.get("event_id") else "")),
    "action.finished": ("action", "done", lambda w: f"The action {_action(w)} finished{w.on}: " + {"success": "it worked", "failed": "it failed", "terminated": "it was stopped"}.get(
        str(w.d.get("status")), str(w.d.get("status") or "done"))),
    "action.not_run": ("action", "worth", lambda w: f"The action {_action(w)} did not run{w.on}" + (f": {_q(w.d['why'], 60)}" if w.d.get("why") else "")),
    "action.timeout_unreported": ("action", "worth", lambda w: f"The action {_action(w)} never reported back{w.on}"),
    "action.terminate_requested": ("action", "done", lambda w: f"Asked {_action(w)} to stop{w.on}"),
    "action.run_stop_requested": ("action", "done", lambda w: f"Asked {_action(w)} to stop{w.on}"),
    "action.created": ("action", "done", lambda w: f"Made the action “{_q(w.d.get('name') or 'new', 40)}”"),
    "action.updated": ("action", "done", lambda w: f"Changed the action {_action(w)}"),
    "action.archived": ("action", "done", lambda w: f"Archived the action {_action(w)}"),
    "action.tried": ("action", "done", lambda w: f"Tried the action {_action(w)}{w.on}"),
    "action.run": ("action", "done", lambda w: f"Ran {_action(w)} on {_n(len(w.d.get('pcs') or []), 'machine')}"),
    "event.created": ("action", "done", lambda w: f"Made the Automation rule {_rule(w)}"),
    "event.updated": ("action", "done", lambda w: f"Changed the Automation rule {_rule(w)}"),
    "event.disabled": ("action", "done", lambda w: f"Switched off the Automation rule {_rule(w)}"),
    "event.fired": ("action", "done", lambda w: f"The Automation rule {_rule(w)} went off{w.on}"),
    "event.tested": ("action", "done", lambda w: f"Tested the Automation rule {_rule(w)}{w.on}"),
    "event.skipped": ("action", "done", lambda w: f"Skipped the next run of {_rule(w)}"),
    "event.unskipped": ("action", "done", lambda w: f"Took back the skip on {_rule(w)}"),
    "event.skip_used": ("action", "routine", lambda w: f"The Automation rule {_rule(w)} skipped a run, as it was asked to"),
    "event.run_again": ("action", "done", lambda w: f"Asked {_rule(w)} to run again"),
    "rule.created": ("deviation", "done", lambda w: f"Made the rule {_rule(w)}"),
    "rule.updated": ("deviation", "done", lambda w: f"Changed the rule {_rule(w)}"),
    "rule.switched": ("deviation", "done", lambda w: f"Switched {'on' if w.d.get('on') else 'off'} the rule {_rule(w)}"),
    "rule.tried": ("deviation", "done", lambda w: f"Tried a rule{w.on}"),
    "deviation.raised": ("deviation", "worth", _deviation),
    "deviation.outcome": ("deviation", "done", lambda w: f"Marked “{_q((w.thing('deviations').get('short') or '').replace('{who}', w.host or 'a machine') or w.d.get('code') or 'a rule not met', 50)}” as "
                          + {"dismissed": "not a problem", "explained": "explained", "acted": "dealt with"}.get(str(w.d.get("outcome")), str(w.d.get("outcome") or "seen"))),
    # the name check, postponed to version 2 (the user, 10 Nov 2026; ENGINE-GAPS 30): what is already recorded reads plainly, and is routine
    "deviation.logged": ("deviation", "routine", lambda w: f"{w.d.get('announced_hostname') or 'A machine'} connected under another name; it is registered as {w.d.get('expected_hostname') or w.host or 'something else'}"),
    # --- flows --------------------------------------------------------------------------------------------------------------------
    "flow.created": ("flow", "done", lambda w: f"Made the flow {w.d.get('name') or w.flow()}" + (", which copies only when it is run" if w.d.get("run_mode") == "manual" else "")),
    "flow.edited": ("flow", "done", lambda w: f"Changed the flow {w.flow()}"),
    "flow.deleted": ("flow", "done", lambda w: f"Deleted the flow {w.flow()}"),
    "flow.paused": ("flow", "done", lambda w: f"Paused the flow {w.flow()}" + (f" ({_q(w.d['because'], 50)})" if w.d.get("because") else "")),
    "flow.resumed": ("flow", "done", lambda w: f"Resumed the flow {w.flow()}" + (f" ({_q(w.d['why'], 50)})" if w.d.get("why") else "")),
    "flow.run": ("flow", "done", lambda w: f"Ran the flow {w.flow()}"),
    "flow.consent": ("flow", "done", lambda w: f"{'Agreed to' if w.d.get('granted') else 'Turned down'} the flow {w.flow()}"),
    "flow.reminded": ("flow", "done", lambda w: f"Reminded {w.who(w.d.get('told'), 'them')} about the flow {w.flow()}"),
    "flow.delete_rule_changed": ("flow", "done", lambda w: f"Changed what {w.flow()} does when a file is deleted at its source"),
    "flow.copies_removed": ("flow", "done", lambda w: f"Removed {_n(w.d.get('files'), 'copy', 'copies')} the flow {w.flow()} had made"),
    "flow.keep_settled": ("flow", "done", lambda w: f"Settled which copy of {_file(w.d.get('path'))} {w.flow()} keeps"),
    "flow.synced": ("flow", "routine", lambda w: f"{w.flow()} copied {_file(w.d.get('relative_path'))}{' to ' + w.host if w.host else ''}"),
    "flow.caught_up": ("flow", "routine", lambda w: f"{w.flow()} caught up on {_n(w.d.get('files'), 'file')}"),
    "flow.bundled": ("flow", "routine", lambda w: f"{w.flow()} bundled {_n(w.d.get('files'), 'file')} into {_file(w.d.get('path'))}"),
    "flow.removed": ("flow", "routine", lambda w: f"{w.flow()} removed {_file(w.d.get('relative_path'))}{w.on}, as it was deleted at the source"),
    "flow.replaced": ("flow", "routine", lambda w: f"{w.flow()} replaced {_file(w.d.get('relative_path'))}{w.on}"),
    "flow.copy_followed": ("flow", "routine", lambda w: f"{w.flow()} followed a copy that moved{w.on}"),
    "flow.source_followed": ("flow", "done", lambda w: f"The source folder of {w.flow()} moved; the flow follows it to {_q(w.d.get('to'), 50)}"),
    "flow.failed": ("flow", "worth", lambda w: f"{w.flow()} could not copy{w.on}" + (f": {_q(w.d['reason'], 60)}" if w.d.get("reason") else "")),
    "flow.conflict": ("flow", "worth", lambda w: f"{w.flow()} found {_file(w.d.get('path'))} changed by someone else{w.on}; it kept both"),
    "flow.kept": ("flow", "done", lambda w: f"{w.flow()} kept {_file(w.d.get('relative_path') or w.d.get('path'))} beside the new copy{w.on}"),
    "flow.left_out": ("flow", "done", lambda w: f"{w.flow()} left out {_file(w.d.get('relative_path'))}" + (f": {_q(w.d['why'], 50)}" if w.d.get("why") else "")),
    "flow.not_converted": ("flow", "worth", lambda w: f"{w.flow()} could not convert {_file(w.d.get('relative_path'))}{w.on}"),
    "flow.mirror_held": ("flow", "worth", lambda w: f"{w.flow()} held back deleting {_n(w.d.get('files'), 'file')}" + (f": {_q(w.d['why'], 50)}" if w.d.get("why") else "")),
    "flow.held_restricted": ("flow", "worth", lambda w: f"{w.flow()} stopped at {_file(w.d.get('path'))}, which is restricted"),
    "flow.restricted_asked": ("flow", "worth", lambda w: f"{w.flow()} asks to carry {w.d.get('name') or 'something restricted'}, which is restricted"),
    "flow.restricted_consented": ("flow", "done", lambda w: f"Let {w.flow()} carry {w.d.get('name') or 'something restricted'}"),
    "flow.restricted_declined": ("flow", "done", lambda w: f"Refused to let {w.flow()} carry {w.d.get('name') or 'something restricted'}"),
    "flow.restricted_expired": ("flow", "done", lambda w: f"The permission for {w.flow()} to carry {w.d.get('name') or 'something restricted'} ran out"),
    "flow.restricted_revoked": ("flow", "done", lambda w: f"Took back the permission for {w.flow()} to carry something restricted"),
    # --- protected files and caught copies ----------------------------------------------------------------------------------------
    "mark.created": ("protected", "done", lambda w: _mark(w, True)),
    "mark.removed": ("protected", "done", lambda w: _mark(w, False)),
    "mark.changed": ("protected", "done", lambda w: f"Changed where {w.thing('resource_marks').get('label') or 'a restricted file'} may be: "
                     + ("only exactly where it is" if w.d.get("keep") == "path" else f"anywhere on {w.host or 'its machine'}")),
    "mark.followed": ("protected", "routine", lambda w: f"{w.thing('resource_marks').get('label') or 'A protected file'} moved to {_q(w.d.get('to'), 50)}; its mark went with it"),
    "mark.healed": ("protected", "routine", lambda w: f"Looked again for copies of {w.thing('resource_marks').get('label') or 'a restricted file'}"),
    "mark.allowance_revoked": ("protected", "done", lambda w: f"Took back a copy allowed of {w.thing('resource_marks').get('label') or 'a restricted file'}"),
    "private.applied": ("protected", "routine", lambda w: f"{w.host or 'The machine'} made {w.thing('resource_marks').get('label') or 'a file'} private"),
    "private.apply_failed": ("protected", "worth", lambda w: f"{w.host or 'The machine'} could not make {w.thing('resource_marks').get('label') or 'a file'} private"),
    "private.lift_asked": ("protected", "routine", lambda w: f"{w.host or 'The machine'} was asked to put back who may open {w.thing('resource_marks').get('label') or 'a file'}"),
    "private.readers_changed": ("protected", "done", lambda w: f"Changed who may open {w.thing('resource_marks').get('label') or 'a private file'}"),
    "private.refused": ("violation", "worth", lambda w: f"{w.d.get('who') or 'Someone'} was refused {_file(w.d.get('path'))}{w.on}, which is private"
                        + (f" (in {w.d['process']})" if w.d.get("process") else "")),
    "resource.violation": ("violation", "worth", lambda w: f"Caught a copy of {_file(w.d.get('path'))}{w.on}, where it may not be"),
    "resource.violation_resolved": ("violation", "done", lambda w: f"A copy that was caught{w.on} was dealt with"),
    "resource.tagged": ("protected", "done", lambda w: f"Tagged a file {w.d.get('tag') or 'restricted'}{w.on}"),
    # --- tasks and to-dos ---------------------------------------------------------------------------------------------------------
    "task.created": ("task", "done", lambda w: f"Gave {w.who(w.d.get('assignee_account_id') or w.thing('tasks').get('assignee'), 'someone')} a task: {w.task()}"),
    "task.started": ("task", "done", lambda w: f"Started the task “{w.task()}”"),
    "task.verified": ("task", "done", lambda w: ("Closed the task “" if w.d.get("outcome") == "complete" else "Sent back the task “") + w.task() + "”"),
    "task.reminded": ("task", "done", lambda w: f"Reminded {w.who(w.thing('tasks').get('assignee'), 'them')} about the task “{w.task()}”"),
    "task.deadline_soft": ("task", "worth", lambda w: f"The task “{w.task()}” reached its soft deadline"),
    "task.deadline_final": ("task", "worth", lambda w: f"The task “{w.task()}” passed its deadline"),
    "todo.added": ("task", "routine", lambda w: "Added a to-do"),
    "todo.done": ("task", "routine", lambda w: "Ticked off a to-do"),
    "todo.undone": ("task", "routine", lambda w: "Un-ticked a to-do"),
    # --- issues -------------------------------------------------------------------------------------------------------------------
    "issue.raised": ("issue", "worth", lambda w: f"Raised an issue{w.on}: {_issue(w)}"),
    "issue.acted": ("issue", "done", lambda w: f"{_CHOSE[str(w.d.get('key'))]}{w.on} ({_issue(w)})" if str(w.d.get("key")) in _CHOSE
                    else f"Acted on the issue{w.on}: {_issue(w)}"),
    "issue.escalated": ("issue", "worth", lambda w: f"An issue{w.on} passed its target time: {_issue(w)}"),
    "issue.resolved": ("issue", "done", lambda w: f"Closed the issue{w.on}: {_issue(w)}" + (f" ({_q(w.d['resolution'], 50)})" if w.d.get("resolution") else "")),
    # --- messages -----------------------------------------------------------------------------------------------------------------
    "chat.sent": ("message", "routine", lambda w: "Wrote in a conversation"),
    "chat.asked": ("message", "worth", lambda w: "Asked to talk" + (f": “{_q(w.thing('talk_requests').get('label'), 60)}”" if w.thing("talk_requests").get("label") else "")),
    "chat.request_accepted": ("message", "done", lambda w: "Accepted a request to talk"),
    "chat.request_closed": ("message", "done", lambda w: "Closed a request to talk" + (f": {_q(w.d['why'], 50)}" if w.d.get("why") else "")),
    "chat.file_offered": ("message", "done", lambda w: f"Sent the file {w.d.get('name') or 'a file'} in a conversation" + (", waiting for a yes, as it is restricted" if w.d.get("restricted") else "")),
    "chat.file_sent": ("message", "routine", lambda w: f"The file {w.d.get('name') or 'a file'} was sent{w.on}"),
    "chat.file_consent": ("message", "done", lambda w: f"{'Let' if w.d.get('granted') else 'Kept back'} a restricted file sent in a conversation"),
    "chat.file_save_asked": ("message", "routine", lambda w: f"Asked to save a file{w.on}"),
    "chat.file_saved": ("message", "done", lambda w: f"Saved {_file(w.d.get('path'))}{w.on}"),
    "chat.file_save_failed": ("message", "worth", lambda w: f"Could not save a file{w.on}" + (f": {_q(w.d['error'], 50)}" if w.d.get("error") else "")),
    "chat.files_dropped": ("message", "routine", lambda w: f"Dropped {_n(len(w.d.get('ids') or []), 'file')} nobody saved in time"),
    "assistance.ping": ("message", "done", lambda w: f"Messaged {_person(w, 'to_account_id')}"),
    "assistance.message": ("message", "routine", lambda w: "Wrote in a conversation"),
    "assistance.channel_opened": ("message", "done", lambda w: "Opened a conversation"),
    "assistance.channel_closed": ("message", "done", lambda w: "Closed a conversation"),
    # --- Detective and its suggestions --------------------------------------------------------------------------------------------
    "detective.raised": ("detective", "worth", lambda w: f"Opened a case{w.on}" + (f": {_q(w.thing('detective_cases').get('label'), 60)}" if w.thing("detective_cases").get("label") else "")),
    "detective.dismissed": ("detective", "done", lambda w: f"Dismissed the case{w.on}"),
    "detective.confirmed": ("detective", "done", lambda w: f"Confirmed the case{w.on}"),
    "detective.noted": ("detective", "done", lambda w: f"Noted the case{w.on}"),
    "detective.rule_made": ("detective", "done", lambda w: "Taught Detective to let this kind of thing pass"),
    "detective.rule_revoked": ("detective", "done", lambda w: "Took back something Detective was taught to let pass"),
    "proposal.made": ("detective", "worth", lambda w: f"Suggested: {_q(w.d.get('title') or w.thing('proposals').get('label') or 'a step', 70)}"),
    "proposal.accepted": ("detective", "done", lambda w: f"Took the suggestion: {_q(w.thing('proposals').get('label') or 'a step', 70)}"),
    "proposal.dismissed": ("detective", "done", lambda w: f"Turned down the suggestion: {_q(w.thing('proposals').get('label') or 'a step', 70)}"),
    # --- people, machines, departments --------------------------------------------------------------------------------------------
    "account.created": ("admin", "done", lambda w: f"Made {'an Admin' if w.d.get('role') == 'admin' else 'a Worker'} account" + (f" for {w.host}" if w.host else "")),
    "account.offboarded": ("admin", "done", lambda w: f"Offboarded {_person(w)}"),
    "account.promoted": ("admin", "done", lambda w: f"Made {_person(w)} an Admin"),
    "account.demoted": ("admin", "done", lambda w: f"Made {_person(w)} a Worker"),
    "account.handed_over": ("admin", "done", lambda w: f"Handed {_person(w)}'s work to {_person(w, 'to_account_id')}"),
    "display_name.set": ("admin", "done", lambda w: f"Gave {_person(w)} a name"),
    "display_name.self": ("admin", "done", lambda w: "Set the name others see"),
    "pc.registered": ("admin", "done", lambda w: f"Registered {w.host or 'a machine'}"),
    "pc.rekeyed": ("admin", "worth", lambda w: f"Made a new key for {w.host or 'a machine'}"),
    "pc.renamed": ("admin", "done", lambda w: f"Renamed {w.d.get('from') or 'a machine'} to {w.d.get('to') or 'a new name'}"),
    "pc.moved": ("admin", "done", lambda w: f"Moved {w.d.get('hostname') or w.host or 'a machine'} to another department"),
    "department.created": ("admin", "done", lambda w: f"Made the department {w.d.get('name') or ''}".rstrip()),
    "department.renamed": ("admin", "done", lambda w: f"Renamed the department {w.d.get('from') or ''} to {w.d.get('to') or ''}"),
    "enroll.requested": ("admin", "worth", lambda w: f"{w.d.get('hostname') or 'A machine'} asked to join"),
    "enroll.confirmed": ("admin", "done", lambda w: f"Let {w.d.get('hostname') or 'a machine'} join"),
    "enroll.licensed": ("admin", "done", lambda w: f"{w.d.get('hostname') or 'A machine'} joined with a licence code"),
    "enroll.refused": ("admin", "done", lambda w: f"Refused to let {w.d.get('hostname') or 'a machine'} join" + (f": {_q(w.d['reason'], 50)}" if w.d.get("reason") else "")),
    "enroll.cancelled": ("admin", "done", lambda w: f"{w.d.get('hostname') or 'A machine'} stopped asking to join"),
    "enroll.collected": ("admin", "routine", lambda w: "A machine that joined collected its key"),
    "knock.new": ("admin", "worth", lambda w: f"{w.d.get('hostname') or 'A machine'} is knocking for a seat"
                  + (f" ({w.d['user']} signed in)" if w.d.get("user") else "")),
    "knock.flooded": ("admin", "worth", lambda w: f"Too many new machines knocked from {w.d.get('address') or 'one address'}: refused for an hour"),
    "seat.given": ("admin", "done", lambda w: f"Gave {w.d.get('hostname') or w.host or 'a machine'} a {w.d.get('role') or 'Worker'} seat"),
    "seat.collected": ("admin", "routine", lambda w: f"{w.host or 'A machine'} collected its key"),
    "seat.claimed": ("admin", "done", lambda w: f"{w.d.get('member_email') or 'An Admin'} took an Admin seat on {w.d.get('hostname') or w.host or 'a machine'}"),
    "seat.taken": ("admin", "done", lambda w: f"Took back the seat of {w.d.get('hostname') or w.host or 'a machine'}"
                   + (": the seat period ended" if w.d.get("reason") == "the seat period ended" else "")),
    "seats.granted": ("admin", "done", lambda w: f"{'Admin' if w.d.get('role') == 'admin' else 'Worker'} seats came from the store"
                      + (f": {w.d['seats']}" if w.d.get("seats") else "")
                      + (f", until {str(w.d['valid_until'])[:10]}" if w.d.get("valid_until") else "")),
    "licence.imported": ("admin", "done", lambda w: f"Imported the licence {w.d.get('name') or ''}".rstrip()),
    "licence.revoked": ("admin", "done", lambda w: "Revoked a licence code"),
    "licence.wrong_code": ("admin", "worth", lambda w: "A machine tried a licence code that is not valid"),
    "registry.address_blocked": ("admin", "worth", lambda w: f"Blocked the address {w.d.get('address') or ''}".rstrip()),
    "registry.address_unblocked": ("admin", "done", lambda w: f"Unblocked the address {w.d.get('address') or ''}".rstrip()),
    "alert.created": ("admin", "done", lambda w: f"Wrote the announcement {_alert(w)}"),
    "alert.delivered": ("admin", "routine", lambda w: f"The announcement {_alert(w)} went out"),
    "alert.withdrawn": ("admin", "done", lambda w: f"Withdrew the announcement {_alert(w)}"),
    "audit.exported": ("admin", "done", lambda w: f"Downloaded the audit log ({_n(w.d.get('rows'), 'entry', 'entries')})"),
    "audit.reviewed": ("admin", "done", lambda w: f"Looked through what {_person(w)} did"),
    "retention.deleted": ("admin", "done", lambda w: f"Deleted {_n(w.d.get('rows'), 'old record')}, as it was over 90 days old"),
    "retention.kept": ("admin", "done", lambda w: f"Kept {_n(w.d.get('rows'), 'old record')} past 90 days"),
    "report.addressed": ("report", "done", lambda w: "Marked a report dealt with"),
    # --- Falcon itself ------------------------------------------------------------------------------------------------------------
    "auth.connected": ("system", "routine", lambda w: f"Connected{w.on}"),
    "auth.disconnected": ("system", "routine", lambda w: f"Disconnected{w.on}"),
    "auth.failed": ("system", "worth", lambda w: "Refused a connection without a valid key" + (f" ({_q(w.d['reason'], 40)})" if w.d.get("reason") else "")),
    "index.caught_up": ("system", "routine", lambda w: f"{w.host or 'A machine'} told Falcon about {_n(w.d.get('events'), 'file change')} it had missed"),
    "index.swept": ("system", "routine", lambda w: f"{w.host or 'A machine'} looked through its folders"),
    "component.unhealthy": ("system", "worth", lambda w: f"{str(w.d.get('component') or 'A part of Falcon').replace('_', ' ').capitalize()} stopped working{w.on}"),
    "llm.fallback": ("system", "done", lambda w: "Asked Groq a question the local model could not answer"),
    "update.approved": ("rollout", "done", lambda w: f"Approved version {w.d.get('version') or ''}".rstrip()),
    "update.staged": ("rollout", "done", lambda w: f"Made version {w.d.get('version') or ''} ready to go out".replace("  ", " ")),
    "update.rollout": ("rollout", "done", lambda w: f"Started rolling out version {w.d.get('version') or ''}".rstrip()),
    "update.prompt": ("rollout", "done", lambda w: "Asked for the rollout to move on"),
    "update.attempt": ("rollout", "done", lambda w: f"{'Installed' if w.d.get('succeeded') else 'Could not install'} version {w.d.get('version') or ''}{w.on}"),
    "update.fetched": ("rollout", "routine", lambda w: f"{w.host or 'A machine'} downloaded version {w.d.get('version') or ''}".rstrip()),
    "update.retry": ("rollout", "routine", lambda w: f"Will try the update again{w.on}"),
    "update.left_out": ("rollout", "done", lambda w: f"Left {w.host or 'a machine'} out of the update"),
    "update.left_in": ("rollout", "done", lambda w: f"Put {w.host or 'a machine'} back into the update"),
}

# older kinds of entry no current code writes (a dev database still holds some) are routine, sorted by their prefix
_KIND_PREFIX = (("session.", "session"), ("assisted_access.", "session"), ("action.", "action"), ("event.", "action"), ("flow.", "flow"),
                ("mark.", "protected"), ("private.", "protected"), ("resource.", "violation"), ("task.", "task"), ("issue.", "issue"),
                ("chat.", "message"), ("assistance.", "message"), ("detective.", "detective"), ("deviation.", "deviation"), ("rule.", "deviation"),
                ("update.", "rollout"), ("report", "report"))


def kind_of(action_type: str) -> str:
    if action_type in ENTRIES:
        return ENTRIES[action_type][0]
    return next((k for p, k in _KIND_PREFIX if action_type.startswith(p)), "admin" if action_type.split(".")[0] in (
        "account", "pc", "department", "enroll", "knock", "seat", "seats", "alert", "licence", "registry", "audit", "display_name", "retention") else "system")


def _like_patterns(kinds: list[str]) -> tuple[list[str], list[str]]:
    """The SQL for a kinds filter: every catalogued type of those kinds, and the prefixes older entries of them start with."""
    exact = [t for t, (k, _, _) in ENTRIES.items() if k in kinds]
    like = [p + "%" for p, k in _KIND_PREFIX if k in kinds]
    return exact, like


def shown_types() -> list[str]:
    """What the Audit log lists unless Everything is asked for: every catalogued type that is not routine."""
    return [t for t, (_, level, _) in ENTRIES.items() if level != "routine"]


def _words(action_type: str) -> str:
    return action_type.replace("_", " ").replace(".", " ", 1).replace(".", " ").capitalize()


# a built-in rule that only says again what has its own line (a copy caught; the name check)
_REPEATS_RULES = {"B-1", "B-4"}


def _level(action_type: str, row: dict[str, Any], w: W) -> str:
    if action_type not in ENTRIES:
        return "routine"
    level = ENTRIES[action_type][1]
    d = row.get("detail") or {}
    if action_type == "issue.raised" and d.get("type") in ("file", "deviation"):
        return "routine"                                          # the copy caught (or the name check) is the line
    if action_type == "deviation.raised" and (d.get("rule") in _REPEATS_RULES or w.thing("deviations").get("rule_code") in _REPEATS_RULES):
        return "routine"
    if action_type == "action.finished" and d.get("status") == "failed":
        return "worth"
    if action_type == "update.attempt" and not d.get("succeeded"):
        return "worth"
    return level


def sentence(action: str, d: dict[str, Any], host: str | None, names: dict[int, str]) -> str:
    """One plain sentence for what happened (kept for callers that have only the detail)."""
    w = W({"detail": d}, host, names, {}, 0)
    entry = ENTRIES.get(action)
    return entry[2](w) if entry else _words(action)


_ACCOUNT_KEYS = ("to_account_id", "account_id", "by_account_id", "target_account_id", "admin_id", "assignee_account_id", "told")


async def describe_many(db: Any, entries: list[dict[str, Any]], viewer_account_id: int) -> list[dict[str, Any]]:
    """Each audit row as an event, named for the viewer: {id, at, kind, level, worth, action_type, actor, actor_account_id, what, pc_id, host}."""
    pc_ids = sorted({e["pc_id"] for e in entries if e.get("pc_id")})
    hosts: dict[int, str] = {}
    for pc_id in pc_ids:
        pc = await db.accounts.pc(pc_id)
        if pc:
            hosts[pc_id] = pc["hostname"]
    # the things the rows are about, by kind of target (and the flow / action a detail names), looked up once
    wanted: dict[str, set[int]] = {}
    for e in entries:
        d = e.get("detail") or {}
        if e.get("target_type") and _id(e.get("target_id")) is not None:
            wanted.setdefault(e["target_type"], set()).add(_id(e["target_id"]))  # type: ignore[arg-type]
        if isinstance(d.get("flow_id"), int):
            wanted.setdefault("flows", set()).add(d["flow_id"])
        if isinstance(d.get("action_id"), int):
            wanted.setdefault("actions", set()).add(d["action_id"])
    things: dict[tuple[str, int], dict[str, Any]] = {}
    labels = getattr(db.audit, "labels", None)
    if labels is not None:
        for kind, ids in wanted.items():
            for tid, row in (await labels(kind, sorted(ids))).items():
                things[(kind, tid)] = row
    people = {e["actor_account_id"] for e in entries if e.get("actor_account_id")}
    for e in entries:
        d = e.get("detail") or {}
        people.update(d[k] for k in _ACCOUNT_KEYS if isinstance(d.get(k), int))
        if e.get("target_type") == "accounts" and _id(e.get("target_id")) is not None:
            people.add(_id(e["target_id"]))  # type: ignore[arg-type]
    people.update(t[k] for t in things.values() for k in ("assignee", "subject_account_id") if isinstance(t.get(k), int))
    names = await db.accounts.display_names_for(viewer_account_id, sorted(people)) if people else {}
    out = []
    for e in entries:
        host = hosts.get(e.get("pc_id")) if e.get("pc_id") else None
        action = e["action_type"]
        w = W(e, host, names, things, viewer_account_id)
        if action in ENTRIES:
            try:
                what = ENTRIES[action][2](w)
            except Exception:                                          # noqa: BLE001 -- an odd old row never takes the log down
                what = _words(action)
        else:
            what = _words(action)
        level = _level(action, e, w)
        aid = e.get("actor_account_id")
        actor = ("You" if aid == viewer_account_id else names.get(aid) or "someone") if aid else (
            "Automation" if action in ("action.started", "action.finished", "event.fired") else "Falcon")
        at = e.get("occurred_at") or e.get("at")
        out.append({"id": e.get("id"), "at": at.isoformat() if isinstance(at, datetime) else at, "kind": kind_of(action), "level": level,
                    "worth": level == "worth", "action_type": action, "actor": actor, "actor_account_id": aid,
                    "what": what, "pc_id": e.get("pc_id"), "host": host})
    return out


async def describe(db: Any, entry: dict[str, Any], viewer_account_id: int | None = None) -> dict[str, Any]:
    """One live entry (as `AuditTrail.record` builds it) as an event; names are neutral unless a viewer is given."""
    e = {**entry, "action_type": entry.get("action_type") or entry["action"]}
    return (await describe_many(db, [e], viewer_account_id or 0))[0]


_COPIED = re.compile(r"^(?P<flow>.+) copied (?P<file>.+?)(?: to (?P<host>\S+))?$")


def fold(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each file a flow carried is a row in the trail; read back, a run of them for one flow and machine within the hour is one line:
    "reports-to-inbox copied 12 files to WS-D2: sales-october.csv, visits-october.csv and 10 more"."""
    def within_the_hour(a: Any, b: Any) -> bool:
        try:
            return abs((parse_iso(str(a)) - parse_iso(str(b))).total_seconds()) <= 3600
        except (TypeError, ValueError):
            return False

    out: list[dict[str, Any]] = []
    for e in events:
        m = _COPIED.match(e["what"]) if e["action_type"] == "flow.synced" else None
        prev = out[-1] if out else None
        if (m and prev is not None and prev.get("_flow") == m.group("flow") and prev.get("pc_id") == e.get("pc_id")
                and within_the_hour(prev["_first"], e["at"])):
            files = prev["_files"]
            files.append(m.group("file"))
            prev["what"] = (f"{prev['_flow']} copied {len(files)} files" + (f" to {prev['host']}" if prev.get("host") else "") + ": "
                            + ", ".join(files[:2]) + (f" and {len(files) - 2} more" if len(files) > 2 else ""))
            continue
        out.append({**e, "_flow": m.group("flow"), "_files": [m.group("file")], "_first": e["at"]} if m else e)
    return [{k: v for k, v in e.items() if not k.startswith("_")} for e in out]


def _scope(ident: Any, payload: dict[str, Any]) -> int | None:
    """The department a reader is limited to: an Admin's own, or the one the head of the organisation asks for (None: all)."""
    if kept(ident):
        return ident.department_id
    return int_field(payload, "department_id", required=False)


def _window(payload: dict[str, Any]) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)

    def parse(name: str, default: datetime) -> datetime:
        raw = payload.get(name)
        if not raw:
            return default
        try:
            when = parse_iso(str(raw))
        except ValueError as exc:
            raise ProtocolError(ErrorCode.INVALID, f"{name} must be ISO 8601") from exc
        return when if when.tzinfo else when.replace(tzinfo=timezone.utc)

    return parse("since", now - timedelta(days=7)), parse("until", now + timedelta(minutes=1))


def _kinds(payload: dict[str, Any]) -> list[str] | None:
    kinds = payload.get("kinds")
    if kinds is None:
        return None
    if not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds):
        raise ProtocolError(ErrorCode.INVALID, "kinds must be a list of names")
    if unknown := sorted(set(kinds) - set(KINDS)):
        raise ProtocolError(ErrorCode.INVALID, f"unknown kinds {unknown}; known: {sorted(KINDS)}")
    return kinds


@handler("audit.events")
async def events(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"since"?, "until"?, "kinds"?:[..], "pc_id"?, "department_id"? (the head of the organisation), "actor_account_id"?, "before_id"?,
    "limit"? (500 at most), "routine"? (default false)} -> {"events": [{id, at, kind, level, worth, actor, what, pc_id, host}], "more": bool},
    newest first. Without `routine` the machinery is left out (connections, each file a flow carried, catch-ups) and so is a line that only
    repeats another; with it, everything, a flow's files folded into one line per flow and hour. An Admin sees the events that concern their
    own department's machines or were made by their own people."""
    ident = require_role(ctx, "super_user", "admin")
    since, until = _window(payload)
    limit = min(int_field(payload, "limit", required=False) or 100, 500)
    routine = bool(payload.get("routine"))
    found = await ctx.engine.db.audit.feed(
        since=since, until=until, kinds=_kinds(payload), pc_id=int_field(payload, "pc_id", required=False),
        department_id=_scope(ident, payload), actor_account_id=int_field(payload, "actor_account_id", required=False),
        before_id=int_field(payload, "before_id", required=False), limit=limit + 1, types=None if routine else shown_types())
    more = len(found) > limit
    described = await describe_many(ctx.engine.db, found[:limit], ident.account_id)
    return {"events": fold(described) if routine else [e for e in described if e["level"] != "routine"], "more": more}


@handler("audit.summary")
async def summary(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"since"?, "until"?, "bucket_minutes"? (default 60), "pc_id"?, "department_id"?} -> {total, actors, violations, by_kind,
    series: [{at, counts: {kind: n}}], kept_days}. What Overview's event volume and the Audit log's *Events over time* draw."""
    ident = require_role(ctx, "super_user", "admin")
    since, until = _window(payload)
    bucket = max(1, min(int_field(payload, "bucket_minutes", required=False) or 60, 24 * 60))
    dept = _scope(ident, payload)
    pc_id = int_field(payload, "pc_id", required=False)
    db = ctx.engine.db.audit
    rows_ = await db.counts(since=since, until=until, bucket_minutes=bucket, pc_id=pc_id, department_id=dept)
    by_kind: dict[str, int] = {}
    series: dict[str, dict[str, int]] = {}
    for r in rows_:
        kind = kind_of(r["action_type"])
        by_kind[kind] = by_kind.get(kind, 0) + r["n"]
        s = series.setdefault(r["bucket"].isoformat(), {})
        s[kind] = s.get(kind, 0) + r["n"]
    return {"total": sum(by_kind.values()), "actors": await db.distinct_actors(since=since, until=until, pc_id=pc_id, department_id=dept),
            "violations": by_kind.get("violation", 0), "by_kind": by_kind,
            "series": [{"at": at, "counts": c} for at, c in sorted(series.items())],
            "kept_days": ctx.engine.settings.audit_retention_days}


@handler("audit.export")
async def export(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The same filters as audit.events -> {"filename", "csv", "rows"}: when, kind, who, what, machine. At most 20,000 rows, the routine
    ones too (an export is the record). Exporting is itself recorded."""
    ident = require_role(ctx, "super_user", "admin")
    since, until = _window(payload)
    found = await ctx.engine.db.audit.feed(
        since=since, until=until, kinds=_kinds(payload), pc_id=int_field(payload, "pc_id", required=False),
        department_id=_scope(ident, payload), actor_account_id=int_field(payload, "actor_account_id", required=False),
        before_id=None, limit=20000)
    items = await describe_many(ctx.engine.db, found, ident.account_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["when", "kind", "who", "what", "machine"])
    for e in items:
        w.writerow([e["at"], e["kind"], e["actor"], e["what"], e["host"] or ""])
    await ctx.engine.audit.record(ctx, "audit.exported", detail={"rows": len(items), "since": since.isoformat(), "until": until.isoformat()})
    return {"filename": f"falcon-audit-{since:%Y%m%d}-{until:%Y%m%d}.csv", "csv": buf.getvalue(), "rows": len(items)}
