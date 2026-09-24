"""The sentence a chart is making, generated from the same data the chart drew.

The dashboards are visual and nearly wordless; a panel of density 3 or 4 carries one sentence and,
in the reading panels, the facts that back it. Those words are *generated*, never written, and the
rules that keep them honest live here rather than in QML:

  * one template per condition, filled from the data the chart already has;
  * when no condition matches, state the plain fact -- never manufacture an insight;
  * twelve words or fewer, enforced by `_say`, because a longer thought is a fact for the row below;
  * it says what the chart says, not what someone should feel about it.

A panel is never left blank. `state` tells the view which of three cases it is in:

  "ok"      there is data; draw it, sentence included.
  "empty"   nothing has been recorded yet; draw the chart's structure and lay a notice over it.
  "thin"    there is data, but less than the shape needs (one point of a trend, say).

A zero is none of those: it is a result. "All 14 PCs are on 1.4.2" is an "ok" sentence, and a tier
with no violations keeps its row and its 0.

Pure functions over the dicts the handlers already return, so they are unit-testable without Qt and
without a database. `FalconBridge.narrate(topic, data)` is the only caller.
"""

from __future__ import annotations

from typing import Any

MAX_WORDS = 12


def _say(sentence: str) -> str:
    """Every sentence goes through here, so the twelve-word rule cannot be forgotten."""
    words = sentence.split()
    if len(words) > MAX_WORDS:
        raise ValueError(f"sentence is {len(words)} words, limit is {MAX_WORDS}: {sentence!r}")
    return sentence


def _n(count: int, one: str, many: str | None = None) -> str:
    return f"{count} {one}" if count == 1 else f"{count} {many or one + 's'}"


def _fact(label: str, value: Any, tone: str = "") -> dict[str, Any]:
    return {"label": label, "value": str(value), "tone": tone}


def _brief(text: str) -> str:
    """The phrase that sits beside a cell's title on the Overview: six words at the outside, because
    it shares a line with the title and must never wrap."""
    words = text.split()
    if len(words) > 6:
        raise ValueError(f"brief is {len(words)} words, limit is 6: {text!r}")
    return text


def _out(sentence: str, facts: list[dict[str, Any]] | None = None, action: str = "",
         state: str = "ok", brief: str = "", tone: str = "") -> dict[str, Any]:
    return {"sentence": _say(sentence), "facts": facts or [], "action": action, "state": state,
            "brief": _brief(brief), "tone": tone}


def _empty(sentence: str, note: str = "Nothing recorded yet", brief: str = "nothing yet") -> dict[str, Any]:
    return {"sentence": _say(sentence), "facts": [], "action": "", "state": "empty", "note": note,
            "brief": _brief(brief), "tone": ""}


def _thin(sentence: str, note: str = "Not enough to draw yet", brief: str = "not enough yet") -> dict[str, Any]:
    return {"sentence": _say(sentence), "facts": [], "action": "", "state": "thin", "note": note,
            "brief": _brief(brief), "tone": ""}


# --- the rollout --------------------------------------------------------------------------------

def rollout(data: dict[str, Any]) -> dict[str, Any]:
    version = (data.get("version") or {}).get("version_string")
    behind = data.get("pcs_behind") or []
    pcs = int(data.get("pc_count") or 0)
    if not version:
        return _empty("No version has been approved yet.")
    failing = [b for b in behind if b.get("escalated")]
    retrying = [b for b in behind if not b.get("escalated")]
    if not behind:
        return _out(f"Every PC is on {version}.",
                    [_fact("Client PCs", pcs), _fact("Confirmed", pcs, "ok")],
                    brief="all confirmed", tone="ok")
    facts = [_fact("Confirmed", f"{max(0, pcs - len(behind))} of {pcs}")]
    if retrying:
        facts.append(_fact("Retrying", ", ".join(b["hostname"] for b in retrying[:3]), "warn"))
    if failing:
        facts.append(_fact("Failing", ", ".join(b["hostname"] for b in failing[:3]), "danger"))
    verb = "are" if len(behind) != 1 else "is"
    return _out(f"{_n(len(behind), 'PC')} {verb} behind, so the next version stays blocked.",
                facts, action="Prompt their Admins",
                brief=f"{_n(len(behind), 'PC')} behind, next version blocked", tone="warn")


def confirmations(data: dict[str, Any]) -> dict[str, Any]:
    points = [int(p) for p in (data.get("points") or [])]
    if not points or max(points) == 0:
        return _empty("No update attempts recorded this week.")
    if len(points) < 3:
        return _thin("Only one day of attempts so far.")
    moved = points[-1] - points[0]
    flat_days = 0
    for a, b in zip(reversed(points[:-1]), reversed(points)):
        if a == b:
            flat_days += 1
        else:
            break
    if flat_days >= 2:
        return _out(f"Nothing has confirmed for {_n(flat_days, 'day')}.",
                    [_fact("Confirmed", points[-1]), _fact("Stalled for", _n(flat_days, "day"), "warn")],
                    brief=f"stalled {_n(flat_days, 'day')}", tone="warn")
    if moved <= 0:
        return _out("No PC confirmed this week.", [_fact("Confirmed", points[-1])],
                    brief="none this week", tone="warn")
    return _out(f"{_n(moved, 'PC')} confirmed this week.",
                [_fact("Confirmed", points[-1]), _fact("This week", f"+{moved}", "ok")],
                brief=f"{_n(moved, 'PC')} this week", tone="ok")


def fleet(data: dict[str, Any]) -> dict[str, Any]:
    pcs = int(data.get("pc_count") or 0)
    behind = data.get("pcs_behind") or []
    if pcs == 0:
        return _empty("No client PCs are registered.", brief="no client PCs")
    if not behind:
        return _out(f"All {pcs} PCs are on the current version.",
                    [_fact("Client PCs", pcs), _fact("Confirmed", pcs, "ok")],
                    brief="all confirmed", tone="ok")
    failing = [b for b in behind if b.get("escalated")]
    return _out(f"{_n(len(behind), 'PC')} of {pcs} still to confirm.",
                [_fact("Confirmed", f"{max(0, pcs - len(behind))} of {pcs}"),
                 _fact("Behind", len(behind) - len(failing), "warn" if len(behind) > len(failing) else ""),
                 _fact("Failing", len(failing), "danger" if failing else "")],
                brief=f"{len(behind)} of {pcs} behind", tone="danger" if failing else "warn")


def rollout_departments(data: dict[str, Any]) -> dict[str, Any]:
    """The same rollout, one bar per department: which department is holding the fleet up."""
    departments = data.get("departments") or []
    if not departments:
        return _empty("No departments exist yet.")
    failing = [d for d in departments if int(d.get("escalated") or 0) > 0]
    pending = [d for d in departments if int(d.get("pending") or 0) > 0]
    if failing:
        if len(failing) == 1:
            sentence = f"{failing[0]['department_name']} is the only one failing."
            brief = f"{failing[0]['department_name']} failing"
        else:
            sentence = f"{len(failing)} departments have a PC past the threshold."
            brief = f"{len(failing)} departments failing"
        return _out(sentence, [_fact(d["department_name"], _n(int(d["escalated"]), "PC"), "danger")
                               for d in failing[:4]], brief=brief, tone="danger")
    if pending:
        total = sum(int(d.get("pending") or 0) for d in pending)
        return _out(f"{_n(total, 'PC')} still retrying, none past the threshold.",
                    [_fact(d["department_name"], _n(int(d["pending"]), "PC"), "warn") for d in pending[:4]],
                    brief=f"{_n(total, 'PC')} retrying", tone="warn")
    return _out("Every department is fully confirmed.",
                [_fact(d["department_name"], _n(int(d.get("pcs") or 0), "PC"), "ok") for d in departments[:4]],
                brief="all departments confirmed", tone="ok")


def blocking(data: dict[str, Any]) -> dict[str, Any]:
    """What holds the next version back. The Engine refuses to approve N+1 while any PC is not
    confirmed on N, so this panel names the machines the gate is actually resting on."""
    version = (data.get("version") or {}).get("version_string")
    behind = data.get("pcs_behind") or []
    pcs = int(data.get("pc_count") or 0)
    if not version:
        return _empty("No version has been approved yet.")
    if not behind:
        return _out("Nothing is blocking the next version.",
                    [_fact("Current version", version), _fact("Confirmed", f"{pcs} of {pcs}", "ok")],
                    brief="nothing blocking", tone="ok")
    failing = [b for b in behind if b.get("escalated")]
    retrying = [b for b in behind if not b.get("escalated")]
    # ordered by what has to be dealt with first, because a panel shows only the first few
    facts = []
    for b in failing[:2]:
        attempts = int(b.get("failures") or 0)
        facts.append(_fact("Failing", f"{b['hostname']}, {_n(attempts, 'attempt')}" if attempts
                           else b["hostname"], "danger"))
    if retrying:
        facts.append(_fact("Retrying", ", ".join(b["hostname"] for b in retrying[:2]), "warn"))
    facts.append(_fact("Confirmed", f"{max(0, pcs - len(behind))} of {pcs}"))
    facts.append(_fact("Current version", version))
    verb = "confirms" if len(behind) == 1 else "confirm"
    return _out(f"The next version stays blocked until {_n(len(behind), 'PC')} {verb}.", facts,
                action="Prompt their Admins",
                brief=(f"{_n(len(failing), 'PC')} failing" if failing
                       else f"{_n(len(retrying), 'PC')} retrying"),
                tone="danger" if failing else "warn")


# --- what needs the Super User ------------------------------------------------------------------

def needs_you(data: dict[str, Any]) -> dict[str, Any]:
    tree = data.get("tree") or []
    violations = data.get("violations") or []
    deviations = [d for d in (data.get("deviations") or []) if not d.get("resolved_at")]
    behind = data.get("pcs_behind") or []
    empty_depts = [d for d in tree if not d.get("admins")]

    facts: list[dict[str, Any]] = []
    for b in behind[:2]:
        facts.append(_fact("Failing" if b.get("escalated") else "Retrying", b["hostname"],
                           "danger" if b.get("escalated") else "warn"))
    for d in empty_depts[:2]:
        facts.append(_fact("No Admin", d["name"], "danger"))
    if violations:
        v = violations[0]
        facts.append(_fact("Violation", f"{v.get('filename', 'a file')}, {v.get('hostname', '')}".strip(", "), "danger"))
    if deviations:
        facts.append(_fact("Deviation", str(deviations[0].get("expectation", "")).replace("_", " "), "warn"))

    if not facts:
        return _out("Nothing is waiting on you.", state="ok")
    if empty_depts and behind:
        return _out(f"{_n(len(behind), 'PC')} behind, and {_n(len(empty_depts), 'department')} without an Admin.",
                    facts, action="Prompt their Admins")
    if empty_depts:
        # name it when there is one: a department is a thing, not a count
        sentence = (f"{empty_depts[0]['name']} has no Admin governing it." if len(empty_depts) == 1
                    else f"{len(empty_depts)} departments have no Admin governing them.")
        return _out(sentence, facts, action="Assign an Admin")
    if behind:
        return _out(f"{_n(len(behind), 'PC')} behind, so the next version stays blocked.",
                    facts, action="Prompt their Admins")
    return _out(f"{_n(len(facts), 'thing')} needs addressing.", facts)


# --- the hierarchy ------------------------------------------------------------------------------

def hierarchy(data: dict[str, Any]) -> dict[str, Any]:
    tree = data.get("tree") or []
    if not tree:
        return _empty("No departments exist yet.")
    pcs = sum(len(d.get("workers") or []) for d in tree)
    admins = sum(len(d.get("admins") or []) for d in tree)
    empty_depts = [d for d in tree if not d.get("admins")]
    if not empty_depts:
        return _out("Every department has an Admin.",
                    [_fact("Departments", len(tree)), _fact("Admins", admins), _fact("Client PCs", pcs)],
                    brief="every department governed", tone="ok")
    d = empty_depts[0]
    ungoverned = sum(len(x.get("workers") or []) for x in empty_depts)
    facts = [_fact("Department", d["name"], "danger"), _fact("Its client PCs", len(d.get("workers") or [])),
             _fact("Ungoverned PCs", ungoverned, "danger"), _fact("Departments", len(tree))]
    return _out(f"{d['name']} has no Admin, so nobody below you governs it.", facts,
                action="Assign an Admin",
                brief=(f"{d['name']} has no Admin" if len(empty_depts) == 1
                       else f"{len(empty_depts)} departments have no Admin"), tone="danger")


def assistance(data: dict[str, Any]) -> dict[str, Any]:
    pairs = data.get("pairs") or []          # [{from_name, to_name, count}]
    if not pairs:
        return _out("No department has asked another for help today.")
    top = max(pairs, key=lambda p: p["count"])
    total = sum(p["count"] for p in pairs)
    return _out(f"{_n(total, 'assisted session')} today, most from {top['from_name']}.",
                [_fact(f"{p['from_name']} → {p['to_name']}", _n(p["count"], "session")) for p in pairs[:4]])


def routing(data: dict[str, Any]) -> dict[str, Any]:
    categories = data.get("categories") or []
    routed = data.get("routing") or []
    if not categories:
        return _empty("No report categories are configured.")
    with_dept = {r.get("category") for r in routed}
    only_you = [c for c in categories if c not in with_dept]
    if not only_you:
        return _out("Every category also reaches a department.")
    return _out(f"{_n(len(only_you), 'category', 'categories')} reach only you.",
                [_fact(str(c).replace("_", " ").capitalize(), "you alone") for c in only_you[:4]])


# --- the record ---------------------------------------------------------------------------------

def the_day(data: dict[str, Any]) -> dict[str, Any]:
    sessions = data.get("sessions") or []
    quiet = int(data.get("quiet_pcs") or 0)
    pcs = int(data.get("pc_count") or 0)
    if pcs == 0:
        return _empty("No client PCs are registered.")
    if not sessions:
        return _out("Nobody signed in anywhere today.",
                    [_fact("Client PCs", pcs), _fact("Never signed in", pcs, "warn")],
                    brief="nobody signed in", tone="warn")
    traversals = [s for s in sessions if s.get("occupied_via") != "native"]
    yours = [s for s in traversals if s.get("occupant_role") == "super_user"]
    assisted = [s for s in traversals if s.get("occupied_via") == "assisted_access"]
    still_open = [s for s in traversals if not s.get("ended_at")]
    facts = [_fact("Traversals", f"{len(traversals)}, {len(still_open)} still open" if still_open
                   else str(len(traversals)))]
    if yours:
        facts.append(_fact("You entered", yours[0].get("hostname", "a PC")))
    if quiet:
        facts.append(_fact("Never signed in", _n(quiet, "PC"), "warn"))
    if assisted:
        facts.append(_fact("Assisted", _n(len(assisted), "session")))
    if not traversals:
        return _out("Everyone worked at their own PC today.", facts, brief="nobody entered a machine")
    if yours:
        return _out(f"{_n(len(traversals), 'traversal')} today, one of them yours.", facts,
                    action="Open the trail", brief="you entered one machine")
    return _out(f"{_n(len(traversals), 'traversal')} today, none of them yours.", facts,
                action="Open the trail", brief=f"{_n(len(traversals), 'traversal')}, none yours")


def violations(data: dict[str, Any]) -> dict[str, Any]:
    found = data.get("violations") or []
    if not found:
        return _out("Nothing is out of place right now.")
    v = found[0]
    return _out(f"{_n(len(found), 'file')} sits where its tier does not allow.",
                [_fact("File", v.get("filename", "")), _fact("Found on", v.get("hostname", ""), "danger"),
                 _fact("Tier", v.get("resource_tag", ""))],
                action="Open the violation")


def deviations(data: dict[str, Any]) -> dict[str, Any]:
    found = data.get("deviations") or []
    open_ = [d for d in found if not d.get("resolved_at")]
    if not found:
        return _out("Nothing has deviated from what the system expects.")
    if not open_:
        return _out(f"All {len(found)} deviations have been addressed.")
    return _out(f"{_n(len(open_), 'deviation')} still unaddressed.",
                [_fact(str(d.get("expectation", "")).replace("_", " ").capitalize(), "logged", "warn")
                 for d in open_[:3]])


def work(data: dict[str, Any]) -> dict[str, Any]:
    tasks = data.get("tasks") or []
    flows = data.get("flows") or []
    overdue = int(data.get("overdue") or 0)
    paused = [f for f in flows if f.get("status") != "active"]
    if not tasks and not flows:
        return _empty("No tasks or flows exist yet.")
    if overdue:
        return _out(f"{_n(overdue, 'task')} past {'its' if overdue == 1 else 'their'} final deadline.",
                    [_fact("Tasks", len(tasks)), _fact("Overdue", overdue, "danger"),
                     _fact("Flows", len(flows)), _fact("Paused", len(paused), "warn" if paused else "")])
    if paused:
        return _out(f"{_n(len(paused), 'flow')} paused, and no task is overdue.",
                    [_fact("Tasks", len(tasks)), _fact("Flows", len(flows)),
                     _fact("Paused", len(paused), "warn")])
    return _out("Every task is on track and every flow is syncing.",
                [_fact("Tasks", len(tasks)), _fact("Flows", len(flows))])


def dept_fleet(data: dict[str, Any]) -> dict[str, Any]:
    """One department's client PCs, always counted against the largest department rather than on
    their own -- so the panel says how big it is as well as how it stands."""
    hosts = data.get("hosts") or []
    biggest = int(data.get("biggest") or len(hosts))
    if not hosts:
        return _empty("This department has no client PCs.", brief="no client PCs")
    failing = [h for h in hosts if h.get("state") == "failing"]
    behind = [h for h in hosts if h.get("state") == "behind"]
    brief = f"{len(hosts)} of {biggest}"
    if failing:
        return _out(f"{failing[0]['hostname']} has failed past the threshold.",
                    [_fact("Client PCs", f"{len(hosts)} of {biggest} the largest has"),
                     _fact("Failing", failing[0]["hostname"], "danger")],
                    brief=brief, tone="danger")
    if behind:
        return _out(f"{_n(len(behind), 'machine')} here is still behind.",
                    [_fact("Client PCs", f"{len(hosts)} of {biggest} the largest has")],
                    brief=brief, tone="warn")
    return _out(f"All {len(hosts)} machines here are on the current version.",
                [_fact("Client PCs", f"{len(hosts)} of {biggest} the largest has")],
                brief=brief, tone="ok")


def out_of_place(data: dict[str, Any]) -> dict[str, Any]:
    """The Overview's fourth cell: files against their tier, and deviations logged but not yet
    addressed. Two different records, one question -- has anything gone where it should not."""
    found = data.get("violations") or []
    open_dev = [d for d in (data.get("deviations") or []) if not d.get("resolved_at")]
    if not found and not open_dev:
        return _out("Nothing is out of place, and nothing has deviated.",
                    brief="nothing out of place", tone="ok")
    facts = []
    if found:
        v = found[0]
        facts.append(_fact("File", f"{v.get('filename', 'a file')}, {v.get('hostname', '')}".strip(", "), "danger"))
        facts.append(_fact("Tier", v.get("resource_tag", ""), "danger"))
    if open_dev:
        facts.append(_fact("Deviation", str(open_dev[0].get("expectation", "")).replace("_", " "), "warn"))
    bits = []
    if found:
        bits.append(_n(len(found), "file"))
    if open_dev:
        bits.append(_n(len(open_dev), "deviation"))
    return _out(f"{' and '.join(bits)} out of place.", facts,
                action="Open the violation" if found else "",
                brief=", ".join(bits), tone="danger" if found else "warn")


TOPICS = {
    "rollout": rollout, "confirmations": confirmations, "fleet": fleet, "needs_you": needs_you,
    "rollout_departments": rollout_departments, "blocking": blocking,
    "hierarchy": hierarchy, "assistance": assistance, "routing": routing, "the_day": the_day,
    "violations": violations, "deviations": deviations, "work": work, "out_of_place": out_of_place, "dept_fleet": dept_fleet,
}


def narrate(topic: str, data: dict[str, Any]) -> dict[str, Any]:
    """The single entry point. An unknown topic is a programming error, not a runtime one, so it
    returns an empty-state panel rather than raising into the UI."""
    fn = TOPICS.get(topic)
    if fn is None:
        return _empty("Nothing to say about this yet.")
    return fn(data or {})
