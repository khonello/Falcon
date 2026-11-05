"""The console concept's "small" sample, as the Engine would answer it, dated around now.

`scripts/preview.py` answers every `falcon.call` from here, so the real QML can be looked at and
screenshotted beside the published concept (Falcon Concepts) with the same machines, people and
events. Times are hours relative to now (negative is earlier), the concept's own time axis.

Not product code: nothing imports this but the preview.
"""
from __future__ import annotations

import base64
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REAL_NOW = datetime.now(timezone.utc).astimezone()
# the sample is the concept's, so the preview's clock reads the concept's now, Thursday 1 October 2026 at 13:20, whatever
# the real time is (the preview tells the console's Time the same skew): days, dates and charts then read as the concept's
NOW = REAL_NOW.replace(year=2026, month=10, day=1, hour=13, minute=20, second=0, microsecond=0)
SKEW_MS = (NOW - REAL_NOW).total_seconds() * 1000


def at(hours: float) -> str:
    """An ISO time `hours` from now (negative: earlier)."""
    return (NOW + timedelta(minutes=round(hours * 60))).isoformat()    # the concept rounds to the minute where a clock would cut


CONCEPT_NOW = 13 + 20 / 60       # the concept's "now", 13:20; the sample is laid out around it


def today(h: float) -> str:
    """The concept's clock hour `h` (13.33 is now), placed the same distance before the real now."""
    return at(min(h, CONCEPT_NOW) - CONCEPT_NOW)


# --- the estate --------------------------------------------------------------------------------------
# account ids: Admins 7 (R. Mensah), 9 (A. Quaye), 8 (K. Boateng); workers 21..
DEPTS = [(1, "Operations"), (2, "Finance"), (3, "Logistics")]
ADMINS = [  # account, name, dept, pc, workstation, busy
    (7, "R. Mensah", 1, 101, "WS-OPS-A1", "OPS-04"),
    (9, "A. Quaye", 1, 102, "WS-OPS-A2", None),
    (8, "K. Boateng", 2, 103, "WS-FIN-A1", None),
]
MACHINES = [  # pc, host, user, account, dept, online, hours since seen
    (1, "OPS-01", "Kojo", 21, 1, True, 0),
    (2, "OPS-02", None, 22, 1, True, 0),
    (3, "OPS-03", "Yaw", 23, 1, True, 0),
    (4, "OPS-04", "Adjoa", 24, 1, True, 0),
    (5, "OPS-05", "Nana", 25, 1, True, 0),
    (6, "OPS-06", "Kwame", 26, 1, True, 0),
    (7, "OPS-07", "Ama", 27, 1, True, 0),
    (11, "FIN-01", "Afi", 31, 2, True, 0),
    (12, "FIN-02", "Kofi", 32, 2, True, 0),
    (21, "LOG-01", "Esi", 41, 3, True, 0),
    (22, "LOG-02", "Abena", 42, 3, False, 10.8133),
]
HOST = {m[1]: m for m in MACHINES}
_CM = json.loads((Path(__file__).with_name("preview_concept_machines.json")).read_text(encoding="utf-8"))["machines"]
# who is inside a machine now: host -> (occupant, account, via, entered hours ago)
HELD = {"OPS-04": ("A. Quaye", 9, "traversal", 0.4), "OPS-07": ("You", 7, "traversal", 2.6)}


def _session(host: str) -> dict[str, Any] | None:
    pc, _, user, acct, *_ = HOST[host]
    if host in HELD:
        who, a, via, h = HELD[host]
        return {"session_id": 900 + pc, "pc_id": pc, "occupant_account_id": a, "occupant_name": who,
                "occupant_role": "admin", "occupied_via": via, "entered_at": at(-h), "deadline_at": at(0.5)}
    if user and HOST[host][5]:
        return {"session_id": 800 + pc, "pc_id": pc, "occupant_account_id": acct, "occupant_name": user,
                "occupant_role": "worker", "occupied_via": "native", "entered_at": at(-5), "deadline_at": None}
    return None


def calendar_board() -> dict[str, Any]:
    """What is coming, as `calendar.board` answers it, from the concept's calEvents: open tasks by their final deadline, your to-dos, and Daily maintenance."""
    items = []
    for t in TASKS:
        tid, title, who, _by, status, _c, _s, _soft, final, _i = t
        if status != "completed":
            pc = next((m[1] for m in MACHINES if m[3] == who), "")
            h = final - CONCEPT_NOW
            items.append({"kind": "task", "at": at(h), "title": title, "line": f"{NAMES.get(who, '?')} · {pc}", "to": ["tasks", tid], "overdue": h < 0})
    for td in _todos()["todos"]:
        if not td["done"]:
            items.append({"kind": "todo", "at": td["due_at"], "title": td["text"], "line": "your to-do", "to": ["tasks", None], "overdue": td["overdue"]})
    for d in range(61):
        day = NOW + timedelta(days=d)
        when = day.replace(hour=9, minute=0)
        if day.weekday() < 5 and when > NOW and day.month <= 11:
            items.append({"kind": "rule", "at": when.isoformat(), "title": "Daily maintenance", "line": "All machines · 2 actions", "to": ["automation", "4"], "overdue": False})
    items.sort(key=lambda x: x["at"])
    return {"now": NOW.isoformat(), "until": at(124 * 24), "items": items, "cut": False}


def tree(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for did, name in DEPTS:
        admins = [{"account_id": a, "role": "admin", "name": n, "status": "active", "pc_id": pc, "hostname": ws,
                   "pc_type": "admin_workstation", "online": ws != "WS-FIN-A1", "last_seen_at": at(-5 / 3 if ws == "WS-FIN-A1" else 0),
                   "session": ({"occupied_via": "traversal", "occupant_name": n} if busy else None)}
                  for a, n, d, pc, ws, busy in ADMINS if d == did]
        workers = [{"account_id": acct, "role": "worker", "name": user, "status": "active" if online else "inactive",
                    "pc_id": pc, "hostname": host, "pc_type": "client_pc", "online": online,
                    "last_seen_at": at(-seen), "session": _session(host)}
                   for pc, host, user, acct, d, online, seen in MACHINES if d == did]
        out.append({"department_id": did, "name": name, "admins": admins, "workers": workers})
    return {"viewer": {"role": role}, "departments": out}


def sessions_today(role: str, dept_id: int | None) -> dict[str, Any]:
    # the concept's lanes: [host, from, to (None = now), occupant, via]
    lanes = [("LOG-02", 2.23, 2.52, "A. Quaye", "traversal"), ("LOG-01", 7.97, None, "Esi", "native"),
             ("OPS-01", 8.2, None, "Kojo", "native"), ("OPS-03", 9.4, 12.5, "Yaw", "native"),
             ("OPS-03", 12.5, 13.18, "R. Mensah", "traversal"), ("OPS-03", 13.2, None, "Yaw", "native"),
             ("OPS-04", 8.0, 10.1, "Adjoa", "native"), ("OPS-04", 10.1, 10.9, "R. Mensah", "traversal"),
             ("OPS-04", 10.92, 12.97, "Adjoa", "native"), ("OPS-04", 12.97, None, "R. Mensah", "traversal"),
             ("OPS-05", 9.18, None, "Nana", "native"), ("OPS-06", 8.67, None, "Kwame", "native"),
             ("OPS-07", 8.1, 10.7, "Ama", "native"), ("OPS-07", 10.7, None, "You", "traversal"),
             ("FIN-01", 8.52, None, "Afi", "native"), ("FIN-02", 8.5, 9.3, "Kofi", "native"),
             ("FIN-02", 9.68, None, "Kofi", "native")]
    out = []
    for k, (host, a, b, who, via) in enumerate(lanes):
        if role == "admin" and HOST[host][4] != dept_id:
            continue
        out.append({"session_id": 700 + k, "pc_id": HOST[host][0], "hostname": host, "occupant_name": who,
                    "occupied_via": via, "entered_at": today(a), "ended_at": today(b) if b is not None else None})
    return {"sessions": out}


VIOLATIONS = [  # id, pc, host, file, tag, hours ago, marked by
    (1042, 7, "OPS-07", "budget-2026.xlsx", "restricted", 3.3, "R. Mensah"),
    (1041, 3, "OPS-03", "salaries.csv", "admin", 3.8, "R. Mensah"),
]


def violations(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for vid, pc, host, f, tag, h, _by in VIOLATIONS:
        if role == "admin" and HOST[host][4] != dept_id:
            continue
        out.append({"violation_id": vid, "found_on_pc_id": pc, "hostname": host, "filename": f,
                    "path": {"OPS-07": r"C:\Users\Ama\Documents", "OPS-03": r"C:\Users\Yaw\Desktop"}.get(host, ""),
                    "resource_tag": tag, "detected_at": at(-h), "resolved_at": None})
    return {"violations": out}


def rollout(role: str, dept_id: int | None) -> dict[str, Any]:
    behind = [{"pc_id": 6, "hostname": "OPS-06", "department_id": 1, "version": "1.4.1", "failures": 2,
               "last_attempt_at": at(-26), "escalated": False},
              {"pc_id": 22, "hostname": "LOG-02", "department_id": 3, "version": "1.4.0", "failures": 1,
               "last_attempt_at": at(-76), "escalated": True}]
    depts = [{"department_id": 1, "name": "Operations", "on_current": 6, "total": 7},
             {"department_id": 2, "name": "Finance", "on_current": 2, "total": 2},
             {"department_id": 3, "name": "Logistics", "on_current": 1, "total": 2}]
    if role == "admin":
        behind = [b for b in behind if b["department_id"] == dept_id]
        depts = [d for d in depts if d["department_id"] == dept_id]
    return {"version": {"id": 3, "version_string": "1.4.2", "approved_at": at(-15 * 24)},
            "departments": depts, "pcs_behind": behind}


def pings(role: str, account: int) -> dict[str, Any]:
    # as the Engine answers: one row per ping (the pings table), oldest first; a second ping is a second row
    def ping(i, sender, receiver, name, h):
        return {"id": i, "sender_account_id": sender, "receiver_account_id": receiver, "from_name": name, "sent_at": at(h), "addressed_at": None}
    ps = [ping(5, 21, 7, "Kojo", -3.6), ping(7, 21, 7, "Kojo", -3.2)] if account == 7 or role == "admin" else []
    if role == "super_user":
        ps = [ping(6, 8, 1, "K. Boateng", -0.7), ping(8, 8, 1, "K. Boateng", -0.3)]
    return {"unaddressed": len(ps), "pings": ps, "indicator": "unaddressed_ping" if ps else None}


def deviations(role: str, dept_id: int | None, include_resolved: bool = False) -> dict[str, Any]:
    def dev(i, pc, acct, exp_host, got, h, resolved=None):
        return {"id": i, "expectation": "account_bound_to_one_pc", "observed_pc_id": pc, "observed_account_id": acct,
                "detail": {"expected_hostname": exp_host, "announced_hostname": got}, "surfaced_to_account_id": acct,
                "resolved_at": at(resolved) if resolved is not None else None, "detected_at": at(h)}
    out = [dev(87, 5, 25, "OPS-05", "WS-OPS-05", -4.1),
           dev(84, 22, 42, "LOG-02", "LOG-02-OLD", -30.5),
           dev(79, 12, 32, "FIN-02", "FIN-02.finance.local", -54.0, resolved=-50.0),
           dev(76, 3, 23, "OPS-03", "YAW-LAPTOP", -98.0, resolved=-97.0)]
    if not include_resolved:
        out = [d for d in out if d["resolved_at"] is None]
    if role == "admin":
        out = [d for d in out if d["observed_pc_id"] in {m[0] for m in MACHINES if m[4] == dept_id}]
    return {"deviations": out}


# deviations.list / deviations.get as the Engine answers them (engine/console/deviations.py): each points at its rule
B = {"B-1": (1, "Restricted files stay where they are"), "B-2": (2, "One session on a machine at a time"),
     "B-3": (3, "Machines run the approved version"), "B-4": (4, "A machine's certificate matches its name")}
DEVS = [  # id, rule, severity, kind, who, who_sub, dept, host, hours ago, short, expected, happened, outcome, note, by
    (301, "B-1", "critical", "worker", "Ama", "OPS-07 · Operations", 1, "OPS-07", 3.3, "Copy of budget-2026.xlsx on OPS-07",
     "Stay on WS-OPS-A1, where R. Mensah marked it", r"A copy in C:\Users\Ama\Documents", "open", None, None),
    (302, "B-1", "high", "worker", "Yaw", "OPS-03 · Operations", 1, "OPS-03", 3.8, "Copy of salaries.csv on OPS-03",
     r"Stay in C:\HR\Payroll on WS-OPS-A1", r"A copy in C:\Users\Yaw\Desktop", "open", None, None),
    (287, "B-4", "medium", "pc", "OPS-05", "Operations", 1, "OPS-05", 4.1, "OPS-05 presented another name",
     "The certificate names OPS-05", "The certificate names WS-OPS-05", "open", None, None),
    (284, "B-3", "high", "pc", "LOG-02", "Logistics", 3, "LOG-02", 76, "LOG-02 still on 1.4.0, five days on",
     "1.4.2 within two days of approval", "Still on 1.4.0 after five days", "open", None, None),
    (279, "B-4", "medium", "pc", "FIN-02", "Finance", 2, "FIN-02", 54, "FIN-02 presented another name",
     "The certificate names FIN-02", "The certificate names FIN-02.finance.local", "explained", "The new image set the long name; renamed back.", "You"),
]


def _dev(d):
    i, rule, sev, kind, who, sub, dept, host, h, short, exp, hap, out, note, by = d
    return {"id": i, "code": f"D-{i}", "rule": {"id": B[rule][0], "code": rule, "name": B[rule][1], "locked": True, "sentence_now": B[rule][1]},
            "severity": sev, "kind": kind, "kind_label": {"pc": "PC", "worker": "Worker", "admin": "Admin", "dept": "Department"}[kind],
            "who": who, "who_sub": sub, "department_id": dept, "department_name": dict(DEPTS)[dept], "pc_id": HOST[host][0], "host": host,
            "at": at(-h), "value": None, "short": short, "expected": exp, "happened": hap, "outcome": out,
            "outcome_label": out.capitalize(), "note": note, "by": by, "decided_at": at(-h + 4) if out != "open" else None}


# rules.list / rules.library as the Engine answers them (engine/console/rules.py)
RULES = [  # id, code, name, shape, spec, builtin, enabled, this week, open
    (1, "B-1", "Restricted files stay where they are", "never", {"trigger": "file", "who": "everyone", "depts": "all", "severity": "high", "resp": {"report": True, "admin": True}}, True, True, 2, 2),
    (2, "B-2", "One session on a machine at a time", "never", {"trigger": "second", "who": "everyone", "depts": "all", "severity": "medium", "resp": {"report": False, "admin": False}}, True, True, 0, 0),
    (3, "B-3", "Machines run the approved version", "follow", {"trigger": "version", "expect": "updated", "within": 2880, "who": "machines", "depts": "all", "severity": "high", "resp": {"report": True, "admin": True}}, True, True, 1, 1),
    (4, "B-4", "A machine's certificate matches its name", "never", {"trigger": "cert", "who": "machines", "depts": "all", "severity": "medium", "resp": {"report": True, "admin": True}}, True, True, 2, 1),
    (5, "O-5", "Unanswered help request", "follow", {"trigger": "help", "expect": "answer", "within": 60, "who": "admins", "depts": "all", "severity": "medium", "resp": {"report": True, "admin": True}}, False, True, 1, 1),
    (6, "O-6", "Admins stay out of machines at night", "limit", {"reading": "outhours", "limit": {"n": 0, "per": "week"}, "who": "admins", "depts": "all", "severity": "high", "resp": {"report": True, "admin": False}}, False, True, 1, 1),
]
SENT = {1: "A copy of a restricted file appears where it is not allowed: always a deviation.", 2: "A second session starts on a machine already in use: always a deviation.",
        3: "A new version is approved, then the machine runs that version within 2 days.", 4: "A machine presents a name that does not match what it was registered with: always a deviation.",
        5: "A worker messages for help, then an Admin answers the message within 1 hour.", 6: "Admin entries outside working hours: none per week."}


def rules_list() -> dict[str, Any]:
    out = [{"id": i, "code": c, "name": n, "shape": sh, "locked": b, "on": True if b else en, "spec": sp, "sentence": SENT[i],
            "scope": {"everyone": "Everyone", "machines": "Machines", "admins": "Admins"}[sp["who"]] + ", every department",
            "set_by": "Falcon" if b else "You", "since": at(-24 * (30 - i)), "deviations_this_week": w, "open_this_week": o}
           for i, c, n, sh, sp, b, en, w, o in RULES]
    return {"rules": out, "summary": {"rules": len(out), "on": len(out), "broken_this_week": sum(1 for r in out if r["deviations_this_week"]), "kept": sum(1 for r in out if not r["deviations_this_week"])}}


def rules_library() -> dict[str, Any]:
    lib = [{"key": "restricted-leaves", "name": "Restricted file leaves its folder", "shape": "never", "summary": "A copy of a marked file appears where its mark does not allow it.",
            "spec": {"trigger": "file", "who": "everyone", "depts": "all", "resp": {"report": True, "admin": True}}},
           {"key": "unanswered-help", "name": "Unanswered help request", "shape": "follow", "summary": "A worker messaged for help and nobody answered in time.",
            "spec": {"trigger": "help", "expect": "answer", "within": 60, "who": "admins", "depts": "all", "resp": {"report": True, "admin": True}}},
           {"key": "past-update-limit", "name": "Machine past the update limit", "shape": "follow", "summary": "A machine is still not on the approved version after the time allowed.",
            "spec": {"trigger": "version", "expect": "updated", "within": 2880, "who": "machines", "depts": "all", "resp": {"report": True, "admin": True}}},
           {"key": "admin-outside", "name": "Admin outside their department", "shape": "limit", "summary": "An Admin entering other departments' machines more than the line allows.",
            "spec": {"reading": "crossdept", "limit": {"n": 0, "per": "week"}, "who": "admins", "depts": "all", "resp": {"report": True, "admin": False}}},
           {"key": "out-of-hours", "name": "Out-of-hours session", "shape": "limit", "summary": "An Admin entering machines outside working hours.",
            "spec": {"reading": "outhours", "limit": {"n": 0, "per": "week"}, "who": "admins", "depts": "all", "resp": {"report": True, "admin": False}}}]
    return {"patterns": lib}


def deviations_list() -> dict[str, Any]:
    ds = [_dev(d) for d in DEVS]
    return {"deviations": ds, "summary": {"total": len(ds), "open": sum(1 for d in ds if d["outcome"] == "open")}, "by_rule": [], "per_day": []}


def deviations_get(i: int) -> dict[str, Any]:
    d = next((_dev(x) for x in DEVS if x[0] == i), None)
    if d is None:
        return {}
    ctx = [{"at": at(-(next(x for x in DEVS if x[0] == i)[8]) - 0.6), "who": "Ama" if d["host"] == "OPS-07" else "Someone", "what": f"Signed in on {d['host']}", "kind": "session"},
           {"at": at(-(next(x for x in DEVS if x[0] == i)[8]) + 0.02), "who": "Automation", "what": f"Took a screenshot of {d['host']}", "kind": "action"},
           {"at": d["at"], "who": "System", "what": f"Recorded: {d['rule']['name']}", "kind": "deviation"}]
    ev = [f"{d['who'] if d['kind'] == 'worker' else 'Its person'} was signed in to {d['host']} at the time.", f"No issue was open on {d['host']} at the time."]
    return {"deviation": d, "context": sorted(ctx, key=lambda e: e["at"]), "evidence": ev}


# --- the registry: machines with their keys, refused connections, a machine asking to join ------------------
GEN = {"OPS-05": 2, "OPS-06": 2, "LOG-02": 3}


def machines_list(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for pc, host, user, acct, dept, online, seen in MACHINES:
        c = _CM[host]
        # version 1: an Admin reaches every department
        out.append({"pc_id": pc, "hostname": host, "department_id": dept, "key_generation": GEN.get(host, 1),
                    "owner": {"account_id": acct, "name": user}, "ip": c["ip"], "online": online, "health": c["status"], "note": c["note"],
                    "version": c["ver"], "behind": c["ver"] != "1.4.2", "last_seen_at": at(-seen),
                    # the readings now, as machines.list carries them from each machine's last report
                    "cpu": c["cpu"], "memory": c["mem"], "disk": c["disk"],
                    "held_by_you": host == "OPS-07"})
    for acct, host, pc in ((7, "WS-OPS-A1", 101), (9, "WS-OPS-A2", 102), (8, "WS-FIN-A1", 103)):
        out.append({"pc_id": pc, "hostname": host, "department_id": None, "key_generation": 1, "pc_type": "admin_workstation",
                    "owner": {"account_id": acct, "name": None}, "ip": f"10.20.1.{pc - 90}", "online": True, "version": "1.4.2", "last_seen_at": at(0)})
    return {"machines": out}


def refused() -> dict[str, Any]:
    rows = []
    for i in range(14):
        rows.append({"id": 90000 + i, "action": "auth.failed", "target_id": "q8Zr-fin-new", "occurred_at": at(-5.2 - i * 3.1),
                     "detail": {"reason": "client_id is not provisioned or its account is not active", "peer": "('10.20.6.40', 51544)"}})
    for i in range(3):
        rows.append({"id": 90100 + i, "action": "auth.failed", "target_id": "Lg02-xk3", "occurred_at": at(-15.2 - i * 0.2),
                     "detail": {"reason": "challenge failed", "peer": "('10.20.9.201', 50012)"}})
    return {"entries": rows}


def rollout_gate(role: str, dept_id: int | None) -> dict[str, Any]:
    """rollout.gate as the Engine answers it (engine/console/rollout.py)."""
    ms = [m for m in MACHINES if role != "admin" or m[4] == dept_id]
    rows = []
    for pc, host, user, acct, dept, online, seen in ms:
        if host not in ("OPS-06", "LOG-02"):
            continue
        rows.append({"pc_id": pc, "hostname": host, "department_id": dept, "department_name": dict(DEPTS)[dept],
                     "running": "1.4.1" if host == "OPS-06" else "1.4.0", "should_run": "1.4.2", "attempts": 2 if host == "OPS-06" else 1,
                     "last_attempt_at": at(-50) if host == "OPS-06" else at(-77.5), "last_error": "A file was in use" if host == "OPS-06" else "Update share unreachable",
                     "next_try": "Next idle window" if online else "When it is back online", "online": online,
                     "state": "retrying" if host == "OPS-06" else "escalated", "escalated_at": at(-76) if host == "LOG-02" else None,
                     "escalated_to": "you" if host == "LOG-02" else None, "left_out": None})
    days = [("2026-09-26", 2, ["OPS-01", "OPS-02"], "1.4.2 approved"), ("2026-09-27", 5, ["OPS-03", "OPS-04", "OPS-05"], None), ("2026-09-28", 7, ["OPS-07", "FIN-01"], None),
            ("2026-09-29", 8, ["FIN-02"], None), ("2026-09-30", 9, ["LOG-01"], None), ("2026-10-01", 9, [], None)]
    return {"current": {"version": "1.4.2", "approved_at": at(-24 * 5), "approved_by": "A. Quaye"},
            "next": {"version": "1.4.3", "staged_at": at(-20), "note": None},
            "strip": {"running": len(ms) - len(rows), "total": len(ms), "pct": round(100 * (len(ms) - len(rows)) / max(1, len(ms))), "holding": len(rows), "left_out": 0,
                      "failed_installs": sum(r["attempts"] for r in rows), "failed_hosts": [{"hostname": r["hostname"], "n": r["attempts"]} for r in rows]},
            "holding": rows, "adoption": [{"day": d, "n": n, "joined": j, "note": note} for d, n, j, note in days], "can_approve": False}


def registry_refused() -> dict[str, Any]:
    """registry.refused as the Engine answers it (engine/console/registry.py): one row per who tried and from where."""
    return {"refused": [
        {"id": "door:10.20.9.201:Lg02-xk3", "address": "10.20.9.201", "client_id": "Lg02-xk3", "kind": "wrong_key", "why": "wrong key for LOG-02, from an address LOG-02 never uses",
         "tone": "bad", "advice": "rekey", "tries": 3, "last": at(-15.2), "first": at(-15.6), "claimed_name": "LOG-02", "pc_id": 22, "machine": "LOG-02", "same_address": False,
         "host": "Claims to be LOG-02", "blocked": False,
         "say": "A machine claimed to be LOG-02 with a key that does not match, from an address LOG-02 has never used. Make LOG-02 a new key and block the address until you know who it is."},
        {"id": "door:10.20.6.40:q8Zr-fin-new", "address": "10.20.6.40", "client_id": "q8Zr-fin-new", "kind": "unknown", "why": "not registered", "tone": "wait", "advice": "register",
         "tries": 14, "last": at(-5.2), "first": at(-45.5), "claimed_name": "FIN-03", "pc_id": None, "machine": None, "same_address": None, "host": "FIN-03", "blocked": False,
         "say": "A machine nobody registered keeps trying to connect. If it belongs to a department, register it; it gets a key and stops being refused."}],
        "days": 7, "summary": {"groups": 2, "tries": 17, "bad": 1}}


def registry_accounts(account: int) -> dict[str, Any]:
    rows = []
    for a, n, d, pc, ws, busy in ADMINS:
        rows.append({"account_id": a, "name": n, "you": a == account, "role": "admin", "department_id": d, "department_name": dict(DEPTS)[d], "pc_id": pc, "workstation": ws,
                     "key_generation": 1, "online": True, "last_seen_at": at(0), "hours_limited": False, "now": "Signed in now"})
    return {"accounts": rows, "summary": {"accounts": len(rows)}}


def enroll_list(role: str) -> dict[str, Any]:
    return {"requests": [{"id": 4, "hostname": "OPS-08", "os": "Windows 11 Pro", "mac": "3c:52:82:aa:10:08", "peer": "10.20.4.18",
                          "requested_department_id": 1, "requested_level": "worker", "created_at": at(-0.6), "expires_at": at(23.4)}]}


# --- flows as flow.list answers them: the concept's eight (docs/design/concepts-admin.html, EXISTING_FLOWS) ----------------
_WS = {"WS-OPS-A1": 101, "WS-OPS-A2": 102, "WS-FIN-A1": 103}
FLOWS = [  # id, name, by (account, name), sources [(host, path, paused)], stages [(type, op)], destinations [(host or ?picker, path, paused)],
    # status, pause reason, consent, files copied (all time, today), last sync (hours from now), made (hours from now)
    (1, "payroll", (7, "R. Mensah"), [("OPS-01", "/payroll/", None)], [("transformation", "Add a date")], [("FIN-01", "/payroll/", None)], "paused", "restricted:consent", "not_required", (64, 31), -0.15, -400),
    (2, "payroll-pdf", (8, "K. Boateng"), [("FIN-01", "/payroll/", None)], [("transformation", "To PDF")], [("FIN-02", "/payroll-pdf/", None), ("FIN-02", "/archive/", None)], "active", None, "not_required", (41, 24), -0.13, -400),
    (3, "weekly", (7, "R. Mensah"), [("OPS-07", "/weekly/", None)], [("categorization", "By file type")], [("LOG-01", "/weekly/", None), ("LOG-01", "/archive/", "destination:path_missing")], "active", None, "not_required", (38, 23), -0.3, -400),
    (4, "weekly-digest", (9, "A. Quaye"), [("LOG-01", "/weekly/", None)], [("transformation", "Into one ZIP")], [("OPS-02", "/reports/", None)], "active", None, "not_required", (5, 1), -1.25, -400),
    (5, "intake", (7, "R. Mensah"), [("OPS-03", "/intake/", None)], [], [("?WS-FIN-A1", "", None)], "paused", "consent:pending", "pending", (0, 0), None, -50.67),
    (6, "budget-review", (7, "R. Mensah"), [("WS-OPS-A1", "/reports/budget/", None)], [("transformation", "To PDF")], [("?WS-FIN-A1", "", None)], "paused", "consent:pending", "pending", (0, 0), None, -3.0),
    (7, "ops-pack", (7, "R. Mensah"), [("OPS-02", "/reports/", None), ("OPS-05", "/exports/", "source:path_missing")], [("transformation", "Into one ZIP")], [("WS-OPS-A1", "/packs/", None)], "active", None, "not_required", (7, 1), -0.83, -400),
    (8, "board-pack", (9, "A. Quaye"), [("WS-OPS-A2", "/board/", None)], [("transformation", "To PDF")], [("WS-OPS-A1", "/board/", None), ("WS-FIN-A1", "/board/", None)], "active", None, "not_required", (12, 1), -1.67, -400),
    (9, "scan-archive", (7, "R. Mensah"), [("OPS-04", "/scans/", None)], [], [("WS-OPS-A1", "/scans/", None)], "active", None, "not_required", (212, 0), -384, -900),
    # an ask to this console: K. Boateng wants to send R. Mensah files; R. Mensah picks the folder
    (10, "month-end", (8, "K. Boateng"), [("FIN-01", "/month-end/", None)], [("transformation", "Into one ZIP")], [("?WS-OPS-A1", "", None)], "paused", "consent:pending", "pending", (0, 0), None, -1.7),
]
# the last sync of each flow, as flow.runs answers it: when (hours from now), the one before, each file (name, outcome, KB before, after), what did not go
FLOW_RUNS = {
    1: (-0.15, [-0.65, -1.15, -1.65], [("timesheet-0930.xlsx", "changed", 184, 212), ("2026-09-29-timesheet.xlsx", "new", 0, 190)], [("consent", "held for its owner's consent")]),
    2: (-0.13, [-0.63, -1.13], [("timesheet-0930.pdf", "new", 0, 96), ("timesheet-0929.pdf", "changed", 88, 92)], []),
    3: (-0.3, [-0.65, -1.3], [("manifest-0930.pdf", "new", 0, 340), ("report.xlsx", "kept_beside", 1100, 1320)], [("destination", "destination:path_missing")]),
    4: (-1.25, [-25.25], [("weekly-w40.zip", "new", 0, 2400)], []),
    7: (-0.83, [-24.83], [("pack-0930.zip", "changed", 5100, 5600), ("exports-0930.csv", "new", 0, 210)], []),
    8: (-1.67, [-45.17], [("minutes-2026-09.pdf", "new", 0, 820), ("agenda-oct.pdf", "changed", 120, 134)], []),
}


def _pc(host: str) -> int | None:
    return _WS.get(host) or (HOST[host][0] if host in HOST else None)


def _step_kind(op: str) -> str:
    """A step as the Engine stores it, {kind, op, label, settings}: which of the tree's kinds this sample's step is in."""
    return "bundling" if op.startswith("Into one") else "renaming" if op.startswith(("Add ", "Replace ")) else "choosing" if op.startswith("By ") else "conversion"


def flows() -> list[dict[str, Any]]:
    out = []
    for fid, name, (by, byname), srcs, stages, dests, status, reason, consent, (total, today_n), last, made in FLOWS:
        st = [{"id": fid * 10 + k, "parent_stage_id": None if k == 0 else fid * 10 + k - 1, "stage_type": _step_kind(op), "config": {"kind": _step_kind(op), "op": op, "label": op, "settings": {}}} for k, (t, op) in enumerate(stages)]
        tail = st[-1]["id"] if st else None
        ds = []
        for k, (host, path, paused) in enumerate(dests):
            pick = host.startswith("?")
            h = host.lstrip("?")
            ds.append({"id": fid * 10 + k, "destination_pc_id": _pc(h), "destination_hostname": h, "parent_stage_id": tail, "owner_account_id": next((a[0] for a in ADMINS if a[4] == h), None),
                       "destination_path": path or None, "let_them_choose": pick, "paused_reason": paused,
                       "suggestion": "The destination folder is gone. Make it, or point the flow somewhere else." if paused else None,
                       "last_sync": {"synced_at": at(last)} if last is not None and not paused else None})
        out.append({"id": fid, "name": name, "created_by_account_id": by, "created_by_name": byname, "created_at": at(made),
                    "source_pc_id": _pc(srcs[0][0]), "source_hostname": srcs[0][0], "source_path": srcs[0][1], "source_kind": "folder",
                    "sources": [{"source_pc_id": _pc(h), "source_hostname": h, "source_path": pth, "source_kind": "folder", "pause_reason": gone, "paused_at": at(-1.5) if gone else None} for h, pth, gone in srcs],
                    "status": status, "pause_reason": reason, "consent_status": consent,
                    "suggestion": None, "files_copied": {"total": total, "today": today_n, "last_at": at(last) if last is not None else None},
                    "stages": st, "destinations": ds})
    return out


def flow_runs(fid: int) -> dict[str, Any]:
    r = FLOW_RUNS.get(fid)
    if r is None:
        return {"flow_id": fid, "last": None, "waiting": [], "earlier": [], "runs": 0}
    last, earlier, files, waiting = r
    items = [{"path": n, "relative_path": n, "bundle": False, "outcome": o, "bytes_before": b * 1000, "bytes_after": c * 1000, "destination_id": None, "machine": None, "at": at(last)} for n, o, b, c in files]
    return {"flow_id": fid, "last": {"started_at": at(last), "ended_at": at(last), "files": len(items), "counts": {}, "bytes": 0, "items": items},
            "waiting": [{"kind": k, "why": w} for k, w in waiting], "earlier": [{"started_at": at(h), "ended_at": at(h), "files": 1, "counts": {}, "bytes": 0} for h in earlier], "runs": 1 + len(earlier)}


# --- issues as the Engine keeps them (issues.list / issues.get / issues.act) ------------------------------------
ISSUES = [  # the concept's eighteen (docs/design/concepts-admin.html, ISSUES): id, code, type, severity, title, subject, pc, hours old,
    # target hours, state, label, escalated, detail
    (41, "INC-1042", "file", "critical", "Restricted file copied where it isn't allowed", "budget-2026.xlsx", 7, 3.303, 1, "open", "Open", False, {"folder": "C:\\Users\\Ama\\Documents", "size": "84 KB", "file": "budget-2026.xlsx", "mark": {"host": "WS-OPS-A1", "path": "C:\\Finance\\budget-2026.xlsx", "keep": "machine", "by": "R. Mensah", "kind": "file"}}),
    (42, "UPD-0318", "update", "high", "Update past the escalation limit", "1.4.0 → 1.4.2", 22, 75.833, 24, "open", "Escalated", True, {"cur": "1.4.0", "target": "1.4.2", "attempts": "1, Mon 07:45", "err": "Could not reach the update share"}),
    (43, "INC-1041", "file", "high", "Restricted file copied where it isn't allowed", "salaries.csv", 3, 3.833, 1, "open", "Open", False, {"folder": "C:\\Users\\Yaw\\Desktop", "size": "212 KB", "file": "salaries.csv", "mark": {"host": "WS-OPS-A1", "path": "C:\\HR\\Payroll\\", "keep": "path", "by": "R. Mensah", "kind": "folder"}}),
    (44, "DEV-0087", "deviation", "medium", "Certificate hostname mismatch", "presented WS-OPS-05", 5, 4.153, 8, "open", "Open", False, {"expected": "OPS-05", "presented": "WS-OPS-05", "fp": "5c:1e:…:a9"}),
    (45, "FLW-0012", "flow", "low", "Flow waiting for a folder", "intake → K. Boateng", 3, 57.333, 72, "waiting", "Waiting", False, {"flow": "intake", "from": "OPS-03 /intake/", "to": "a folder K. Boateng picks on WS-FIN-A1", "consent": "K. Boateng", "asked": "2 days ago, by R. Mensah"}),
    (46, "UPD-0322", "update", "low", "One version behind", "1.4.1 → 1.4.2", 6, 26.003, 72, "waiting", "Retrying", False, {"cur": "1.4.1", "target": "1.4.2", "attempts": "2, last Wed 11:20", "err": "Installer exit 1603, a file was in use"}),
    (47, "INC-1050", "file", "high", "Restricted file copied where it isn't allowed", "board-minutes-2026-09.docx", 11, 1.933, 1, "open", "Open", False, {"folder": "C:\\Users\\Afi\\Downloads", "size": "—", "file": "board-minutes-2026-09.docx", "mark": {"host": "WS-FIN-A1", "path": "D:\\Board\\minutes\\board-minutes-2026-09.docx", "keep": "machine", "by": "K. Boateng", "kind": "file"}}),
    (48, "INC-1051", "file", "critical", "Restricted file copied where it isn't allowed", "loi-northline.pdf", 2, 4.583, 1, "open", "Open", False, {"folder": "C:\\Users\\Public\\Shared", "size": "—", "file": "loi-northline.pdf", "mark": {"host": "WS-FIN-A1", "path": "D:\\Acquisitions\\", "keep": "path", "by": "K. Boateng", "kind": "folder"}}),
    (49, "INC-1052", "file", "high", "Restricted file copied where it isn't allowed", "valuation-model.xlsx", 21, 33.833, 1, "open", "Open", False, {"folder": "C:\\Users\\Esi\\Desktop\\new folder", "size": "—", "file": "valuation-model.xlsx", "mark": {"host": "WS-FIN-A1", "path": "D:\\Acquisitions\\", "keep": "path", "by": "K. Boateng", "kind": "folder"}}),
    (50, "INC-1053", "file", "medium", "Restricted file copied where it isn't allowed", "strategy-2027.pptx", 5, 63.333, 1, "open", "Open", False, {"folder": "C:\\Users\\Nana\\Documents", "size": "—", "file": "strategy-2027.pptx", "mark": {"host": "WS-FIN-A1", "path": "C:\\Users\\KBoateng\\Documents\\strategy-2027.pptx", "keep": "path", "by": "K. Boateng", "kind": "file"}}),
    (51, "INC-1054", "file", "high", "Restricted file copied where it isn't allowed", "payroll-2025-12.csv", 3, 5.433, 1, "open", "Open", False, {"folder": "C:\\Users\\Yaw\\Documents", "size": "—", "file": "payroll-2025-12.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (52, "INC-1055", "file", "high", "Restricted file copied where it isn't allowed", "payroll-2025-11.csv", 12, 7.133, 1, "open", "Open", False, {"folder": "C:\\Users\\Kofi\\Documents", "size": "—", "file": "payroll-2025-11.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (53, "INC-1056", "file", "medium", "Restricted file copied where it isn't allowed", "payroll-2025-10.csv", 6, 43.333, 1, "open", "Open", False, {"folder": "C:\\Users\\Kwame\\Documents", "size": "—", "file": "payroll-2025-10.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (54, "INC-1057", "file", "medium", "Restricted file copied where it isn't allowed", "payroll-2025-09.csv", 1, 53.333, 1, "open", "Open", False, {"folder": "C:\\Users\\Kojo\\Documents", "size": "—", "file": "payroll-2025-09.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (55, "INC-1058", "file", "low", "Restricted file copied where it isn't allowed", "payroll-2025-08.csv", 11, 73.333, 1, "open", "Open", False, {"folder": "C:\\Users\\Afi\\Documents", "size": "—", "file": "payroll-2025-08.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (56, "INC-1059", "file", "low", "Restricted file copied where it isn't allowed", "payroll-2025-07.csv", 4, 88.333, 1, "open", "Open", False, {"folder": "C:\\Users\\Adjoa\\Documents", "size": "—", "file": "payroll-2025-07.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (57, "INC-1060", "file", "low", "Restricted file copied where it isn't allowed", "payroll-2025-06.csv", 21, 103.333, 1, "open", "Open", False, {"folder": "C:\\Users\\Esi\\Documents", "size": "—", "file": "payroll-2025-06.csv", "mark": {"host": "WS-FIN-A1", "path": "E:\\Archive\\Payroll\\", "keep": "machine", "by": "K. Boateng", "kind": "folder"}}),
    (58, "INC-1070", "file", "high", "Restricted file copied where it isn't allowed", "payroll-2026-09.xlsx", 5, 0.933, 1, "open", "Open", False, {"folder": "C:\\Users\\Nana\\Downloads", "size": "—", "file": "payroll-2026-09.xlsx", "mark": {"host": "WS-OPS-A1", "path": "C:\\HR\\Payroll\\", "keep": "path", "by": "R. Mensah", "kind": "folder"}}),
]
_TARGET = {"file": 1, "update": 24, "deviation": 8, "flow": 72, "offline": 72}
_TLABEL = {"file": "Restricted file", "update": "Stuck update", "deviation": "Deviation", "flow": "Flow blocked", "offline": "Not checking in"}


def _issue(t: tuple, account: int) -> dict[str, Any]:
    iid, code, type_, sev, title, subject, pc, age, target, state, label, esc, detail = t
    m = next(x for x in MACHINES if x[0] == pc)
    return {"id": iid, "code": code, "type": type_, "type_label": _TLABEL[type_], "severity": sev, "title": title, "subject": subject,
            "pc_id": pc, "host": m[1], "department_id": m[4], "department_name": {1: "Operations", 2: "Finance", 3: "Logistics"}[m[4]],
            "opened_at": at(-age), "age_hours": age, "target_hours": target, "past_target": state != "resolved" and age > target,
            "state": state, "label": label, "escalated": esc, "resolved_at": None, "resolution": None, "detail": detail}


def issues_list(role: str, dept_id: int | None, account: int) -> dict[str, Any]:
    out = [_issue(t, account) for t in ISSUES]      # version 1: an Admin reaches every department
    return {"issues": out, "summary": {"open": sum(i["state"] == "open" for i in out), "waiting": sum(i["state"] == "waiting" for i in out),
                                       "past_target": sum(i["past_target"] for i in out), "done_today": 2, "mine": 0}}


def issues_get(iid: int, account: int) -> dict[str, Any]:
    """issues.get as engine/console/plays.py answers it, in the concept's words for its eighteen issues."""
    t = next(x for x in ISSUES if x[0] == iid)
    i = _issue(t, account)
    d, host = i["detail"], i["host"]
    who = next(x[2] for x in MACHINES if x[0] == i["pc_id"])
    online = next(x[5] for x in MACHINES if x[0] == i["pc_id"])
    why: list[str] = []
    if i["type"] == "file":
        k = d["mark"]
        home = k["host"] if k["keep"] == "machine" else f"{k['host']} {k['path']}"
        lead = f"A copy of a file marked restricted is on {host}. It is kept to {'the machine ' + k['host'] if k['keep'] == 'machine' else 'one place on ' + k['host']}, so nowhere else may have it."
        facts = [["File", d["file"]], ["Found in", d["folder"]], ["Size", d["size"]], ["Allowed only on", home], ["Marked by", k["by"] + (f", as part of {k['path']}" if k["kind"] == "folder" else "")]]
        options = []
        if who and online:
            options.append({"key": "ask", "title": f"Ask {who} to delete it", "desc": f"{who} sees which file and why. The issue closes on its own when the copy is gone.", "verb": "Ask", "done": "Waiting"})
        elif not who:
            why.append("Nobody is signed in, so there is nobody to tell.")
        if online:
            options.append({"key": "delete", "title": "Delete this copy", "desc": f"Deletes it from {host} only. The original on {k['host']} is not touched.", "verb": "Delete copy", "done": "Waiting"})
        options.append({"key": "allow", "title": f"Allow it on {host} too", "desc": "Adds this one place to the mark, with your reason. It is not reported again.", "verb": "Allow it", "done": "Resolved", "need": "reason"})
    elif i["type"] == "deviation":
        lead = f"{host} presented a certificate that does not match what it was registered with."
        facts = [["Registered as", d["expected"]], ["Presented", d["presented"]], ["First seen", "Today " + at(-i["age_hours"])[11:16]], ["Fingerprint", d["fp"]]]
        options = [{"key": "accept", "title": f"Accept {d['presented']}", "desc": f"Registers the machine as {d['presented']} and pins its new certificate.", "verb": "Accept", "done": "Resolved"},
                   {"key": "reverse", "title": f"Put it back to {d['expected']}", "desc": "A new certificate is sent the next time the machine checks in.", "verb": "Put it back", "done": "Waiting"}]
    elif i["type"] == "flow":
        lead = f"The {d['flow']} flow starts when {d['consent']} picks a folder on their workstation for it. Picking it is how they agree."
        facts = [["Flow", d["flow"]], ["From", d["from"]], ["To", d["to"]], ["Asked", d["asked"]]]
        options = [{"key": "remind", "title": f"Remind {d['consent']}", "desc": "Sends the request again, with your name on it.", "verb": "Remind", "done": "Waiting"},
                   {"key": "dest", "title": "Send it to a Worker's machine instead", "desc": "You pick the folder there, and nobody has to agree; only another Admin's machine asks first.", "verb": "Change it", "done": "Resolved", "need": "pick",
                    "pick": ["OPS-01 /intake/", "OPS-04 /intake/", "WS-OPS-A1 /intake/"], "hint": "Pick a destination"},
                   {"key": "withdraw", "title": "Withdraw the flow", "desc": "Nothing has been copied yet. The request is closed.", "verb": "Withdraw", "done": "Resolved"}]
    else:
        lead = f"{host} is on {d['cur']} and should be on {d['target']}."
        facts = [["Running", d["cur"]], ["Should run", d["target"]], ["Attempts", d["attempts"]], ["Last error", d["err"]]]
        if online:
            options = [{"key": "idle", "title": "Retry when it is idle", "desc": "The default. The next idle window is usually after 17:30.", "verb": "Keep this", "done": "Waiting"},
                       {"key": "now", "title": "Retry now", "desc": f"{who or 'Whoever is signed in'} may see a restart prompt.", "verb": "Retry now", "done": "Waiting"}]
        else:
            why.append(f"{host} is offline, so it can only retry when it is back.")
            facts.append(["Offline since", "Today 02:20"])
            options = [{"key": "wait", "title": "Retry when it is back online", "desc": f"The update runs as soon as {host} checks in again.", "verb": "Keep waiting", "done": "Waiting"}]
        options.append({"key": "exclude", "title": "Leave it out of the 1.4.3 gate", "desc": f"The next version can then be approved without {host}. It stays on {d['cur']} until it updates.", "verb": "Leave it out", "done": "Resolved", "need": "reason"})
    age, target = i["age_hours"], i["target_hours"]
    timeline = [{"at": at(-age), "who": "System", "what": f"{i['type_label']} raised on {host}: {i['subject']}", "kind": "raised", "you": False},
                {"at": at(-age + 0.01), "who": "System", "what": "Report written; every Admin sees it, and any of them may act on it", "kind": "system", "you": False},
                {"at": at(target - age), "who": "System", "what": f"Passed its target time ({target} h)" if age > target else f"Target time ({target} h)", "kind": "violation" if age > target else "system", "you": False}]
    return {"issue": i, "detail": d, "lead": lead, "facts": facts, "options": options, "why": why, "timeline": timeline}


# --- restricted marks (marks.list / marks.get / marks.tree) ------------------------------------------------------
_RS = json.loads((Path(__file__).with_name("preview_concept_restricted.json")).read_text(encoding="utf-8"))
_MARK_PC = {"WS-OPS-A1": 101, "WS-OPS-A2": 102, "WS-FIN-A1": 103}


def _mark_id(code: str) -> int:
    return int(code.split("-")[1])


def _day_at(word: str) -> str:
    day, month = word.split()
    return datetime(2026, {"Sep": 9, "Oct": 10}[month], int(day), 9, 0, tzinfo=NOW.tzinfo).isoformat()


def _mark_host(host: str) -> int:
    return _MARK_PC.get(host) or next((m[0] for m in MACHINES if m[1] == host), 0)


def marks_list(role: str, account: int) -> dict[str, Any]:
    ms = [{"id": _mark_id(k["id"]), "code": k["id"], "kind": k["kind"], "name": k["name"], "pc_id": _mark_host(k["host"]), "host": k["host"], "path": k["path"], "keep": k["keep"],
           "keep_label": "Anywhere on the PC" if k["keep"] == "machine" else "Only in its place", "by": {"account_id": _BY.get(k["by"], 0), "name": k["by"], "you": k["by"] == "R. Mensah"}, "files": k["files"], "versions": k["versions"],
           "copies": len(k["copies"]), "worst": k["copies"][0]["sev"] if k["copies"] else None, "created_at": _day_at(k["at"])} for k in _RS["marks"]]
    return {"marks": ms, "summary": {"marks": len(ms), "files": sum(m["files"] for m in ms), "copies": sum(m["copies"] for m in ms), "with_copies": sum(1 for m in ms if m["copies"])}}


def marks_get(mid: int, account: int) -> dict[str, Any]:
    m = next(x for x in marks_list("admin", account)["marks"] if x["id"] == mid)
    k = next(x for x in _RS["marks"] if _mark_id(x["id"]) == mid)
    who = {x[1]: x[2] for x in MACHINES}
    copies = [{"issue_id": next(i[0] for i in ISSUES if i[1] == c["id"]), "code": c["id"], "severity": c["sev"], "state": "open", "label": "Open", "host": c["host"], "file": c["file"], "folder": c["folder"],
               "path": c["folder"] + "\\" + c["file"], "signed_in": who.get(c["host"]), "opened_at": _at(c["at"]), "age_hours": CONCEPT_NOW - c["at"], "came_by": {"how": "copied", "sure": True, "said": c["how"]}}
              for c in k["copies"]]
    allowed = [{"allowance_id": i + 1, "pc_id": _mark_host(x["host"]), "host": x["host"], "path": x["folder"] + ("\\" + x["file"] if x.get("file") else ""), "reason": x["why"], "by": "You", "at": _day_at(x["at"])}
               for i, x in enumerate(_RS["allowed"]) if _mark_id(x["mark"]) == mid]
    flows = [{"consent_id": 9, "flow_id": next((f[0] for f in FLOWS if f[1] == c["flow"]), 0), "flow": c["flow"], "what": c["what"], "from": c["from"], "to": c["to"], "today": c["today"], "last_at": _at(c["last"]),
              "since": _day_at(c["since"]), "source_path": c["from"], "by": "You", "expires_at": None, "flow_status": "active", "take_back": "flow.restricted_revoke"}
             for c in _RS["carry"] if _mark_id(c["mark"]) == mid and not c.get("held")]
    lately = [{"at": _at(e[0]), "who": e[1], "what": e[2], "where": e[3]} for e in _RS["log"].get(k["id"], [])]
    return {"mark": m, "copies": copies, "allowed": allowed, "lately": lately, "flows_allowed": flows, "resolved_copies": [],
            "change": {"keep": "path" if m["keep"] == "machine" else "machine", "effect": {"would_flag": 0, "would_clear": 0}}}


def restricted_waiting() -> list[dict[str, Any]]:
    """Flows held at something of yours (flow.restricted_waiting), as the concept has them."""
    return [{"id": 5, "flow_id": next((f[0] for f in FLOWS if f[1] == c["flow"]), 0), "name": c["flow"], "mark_id": _mark_id(c["mark"]), "what": c["what"], "from": c["from"], "to": c["to"],
             "sample_path": c["from"] + c["what"], "asked_at": _at(c["held"])} for c in _RS["carry"] if c.get("held")]


def marks_tree() -> dict[str, Any]:
    # the concept's sample: what the index has seen on the Admin's own PC, with M-3 (a file) and M-4 (a folder) marked
    spec = ["C:/Finance/budget-2026.xlsx", "C:/Finance/forecast-q4.xlsx", "C:/Finance/suppliers.xlsx",
            "C:/Finance/Invoices/invoices-q3.csv", "C:/Finance/Invoices/invoices-q2.csv", "C:/Finance/Invoices/credit-notes.xlsx",
            "C:/HR/Payroll/salaries.csv", "C:/HR/Payroll/overtime-sep.csv", "C:/HR/Payroll/pension.xlsx",
            "C:/HR/Reviews/reviews-2026.docx", "C:/HR/Reviews/reviews-2025.docx", "C:/HR/Contracts/staff-contract-template.docx", "C:/HR/Contracts/nda-template.docx",
            "C:/Users/RMensah/Documents/headcount-plan-2027.xlsx", "C:/Users/RMensah/Documents/notes.docx", "C:/Users/RMensah/Documents/ops-review-sep.pptx",
            "C:/Users/RMensah/Desktop/todo.txt", "C:/Users/RMensah/Downloads/vendor-quote.pdf",
            "D:/Board/minutes-2026-09.docx", "D:/Board/minutes-2026-08.docx", "D:/Board/strategy-2027.pptx", "D:/Archive/2024-accounts.zip", "D:/Archive/2025-accounts.zip"]
    files = [{"path": f, "name": f.rsplit("/", 1)[1], "marked": 1 if f == "C:/Finance/budget-2026.xlsx" else None,
              "covered_by": 2 if f.startswith("C:/HR/Payroll/") else None} for f in spec]
    folders: dict[str, int] = {}
    for f in spec:
        folders[f.rsplit("/", 1)[0]] = folders.get(f.rsplit("/", 1)[0], 0) + 1
    return {"pc_id": 101, "hostname": "WS-OPS-A1", "files": files, "folders": [{"path": k, "files": n} for k, n in sorted(folders.items())], "truncated": False}


def machines_get(pc: int, rng: str) -> dict[str, Any]:
    host = next((m[1] for m in MACHINES if m[0] == pc), None)
    c = _CM.get(host)
    if c is None:
        return {"machine": {"pc_id": pc}, "range": rng, "series": {}, "processes": {"items": []}, "about": {}, "keyboard": {}, "check_ins": [], "sessions": [], "files": {}, "events": []}
    n = len(c["series"]) - 1
    def ser(k: int) -> list[dict[str, Any]]:
        return [{"at": at(-24 + i * 24 / n), "v": p[k]} for i, p in enumerate(c["series"]) if p[k] is not None]
    ab, use = c["about"], c["use"]
    who = next(m[2] for m in MACHINES if m[0] == pc) or "SYSTEM"
    return {"machine": {"pc_id": pc, "ip": c["ip"], "os": ab["os"], "agent_started_at": at(-ab["up"])}, "range": rng,
            "series": {"cpu": ser(0), "memory": ser(1), "disk": [], "net_kbps": []},
            "processes": {"at": at(-0.05), "items": [{"pid": 1000 + i, "name": p[0], "cpu": round(p[1], 1), "memory_mb": p[2], "user": who} for i, p in enumerate(c["procs"])]},
            "about": {"os": ab["os"], "memory_total_mb": ab["ram"] * 1024, "disk_total_gb": ab["size"], "disk_percent": c["disk"], "boot_at": at(-ab["up"]), "registered_at": datetime.strptime(ab["reg"], "%d %b %Y").replace(tzinfo=NOW.tzinfo).isoformat()},
            "keyboard": {"state": "offline" if c["status"] == "offline" else "in_use" if use["now"] else "idle", "idle_s": int(use["idle"] * 3600), "quarters": []},
            "check_ins": [{"day": at(-24 * (len(c["days"]) - 1 - i))[:10], "yes": y} for i, y in enumerate(c["days"])],
            "sessions": [{"started_at": at(t - CONCEPT_NOW), "ended_at": None if dd is None else at(t - CONCEPT_NOW + dd)} for t, dd in c["sessions"]], "files": {}, "events": []}


# --- the audit trail, 7 days ---------------------------------------------------------------------------
def _nz(seed: float, k: float) -> float:
    x = math.sin(k * 127.1 + seed * 311.7) * 43758.5453
    return x - math.floor(x)


def _audit_action(kind: str, what: str) -> str:
    """The Engine's action name for one of the concept's audit lines."""
    if kind == "session":
        return "session.traversed" if what.startswith("Entered") else "session.ended" if what.startswith("Left") else "session.native"
    if kind == "action":
        return "control.event_fired" if " notified " in what else "control.action_run"
    if kind == "flow":
        return "flow.create" if what.startswith("Created") else "flow.sync"
    if kind == "rollout":
        return "update.check" if what.startswith("Checked") else "update.escalated" if "left for an Admin" in what else "update.failed"
    return {"deviation": "deviation.hostname", "violation": "resource.violation"}.get(kind, kind)


_AUDIT = json.loads((Path(__file__).with_name("preview_concept_audit.json")).read_text(encoding="utf-8"))["audit"]


def audit(role: str, dept_id: int | None, limit: int) -> dict[str, Any]:
    """The concept's audit trail, as audit.query answers it (version 1: an Admin reads every department's)."""
    out = [{"id": 10000 + k, "occurred_at": at(t - CONCEPT_NOW), "actor_name": who, "summary": what, "target_hostname": host,
            "action": _audit_action(kind, what)} for k, (t, who, what, host, kind, _notable) in enumerate(_AUDIT) if t <= CONCEPT_NOW]
    out.sort(key=lambda e: e["occurred_at"], reverse=True)
    return {"entries": out[:limit]}


# --- tasks ----------------------------------------------------------------------------------------------
# id, title, assignee account, assigner (account, name), status, created h, started h, soft h, final h (concept clock),
# items: (type, intent, name, status, signal hours), linked index for used_with_file
TASKS = [  # the concept's ten (docs/design/concepts-admin.html, TASKS): id, title, assignee, (assigner, name), status, given,
    # started, soft deadline, final deadline, targets (type, intent, name, status, when each was seen); hours from today's midnight
    (208, "Reconcile the Q3 invoices", 21, (7, "R. Mensah"), "in_progress", -63, -38.75, 36, 41,
     [("file", "update", "reconciliation.xlsx", "passed", [-38, -30, -28, -7.27, 9.03, 12.97]),
      ("program", "used_with_file", "EXCEL.EXE", "passed", [-37, -29, -6, 9.03, 10.5, 12.0]),
      ("file", "create", "q3-summary.docx", "pending", [])]),
    (207, "Update the supplier contact sheet", 22, (9, "A. Quaye"), "active", 9, None, None, 113,
     [("file", "update", "supplier-contacts.xlsx", "pending", [])]),
    (205, "Prepare the September payroll export", 31, (8, "K. Boateng"), "in_progress", -135, -134, None, -7,
     [("file", "create", "payroll-sep.csv", "passed", [-7.5]),
      ("file", "update", "payroll-sep.xlsx", "passed", [-120, -96, -30]),
      ("program", "used_with_file", "EXCEL.EXE", "passed", [-120, -30])]),
    (201, "Archive the August delivery notes", 41, (9, "A. Quaye"), "in_progress", -160, -150, -55, -31,
     [("file", "exists", "/archive/2026-08/", "passed", [-61.9]),
      ("file", "create", "delivery-notes-aug.zip", "failed", [])]),
    (206, "Send the weekly route plan", 41, (9, "A. Quaye"), "in_progress", -40, -39, 30, 41,
     [("file", "update", "routes-w40.csv", "passed", [-38, -20, -14, 9.5]),
      ("file", "create", "route-plan-w40.pdf", "pending", [])]),
    (204, "Clear duplicate files from the shared drive", 25, (7, "R. Mensah"), "in_progress", -90, -80, None, 113,
     [("file", "exists", "/common/duplicates/", "passed", [-66, -62, -58]),
      ("file", "create", "duplicates-report.xlsx", "pending", [])]),
    (203, "Install the label printer driver", 26, (9, "A. Quaye"), "in_progress", -100, -98, None, -10,
     [("program", "installed_available", "LabelPrint.exe", "passed", [-33.75])]),
    (202, "Submit the Q3 expense claims", 31, (8, "K. Boateng"), "completed", -150, -149, None, -60,
     [("file", "update", "expenses-q3.xlsx", "passed", [-140, -100, -62]),
      ("program", "used", "OUTLOOK.EXE", "passed", [-61.5])]),
    (200, "Back up the Documents folder", 27, (7, "R. Mensah"), "completed", -160, -158, None, -100,
     [("file", "create", "documents-backup.zip", "passed", [-109])]),
    (199, "Rename the August scans", 32, (8, "K. Boateng"), "completed", -165, -164, None, -120,
     [("file", "update", "/scans/2026-08/", "passed", [-144, -130])]),
]
NAMES = {21: "Kojo", 22: "Efua", 25: "Nana", 26: "Kwame", 27: "Ama", 23: "Yaw", 31: "Afi", 32: "Kofi", 41: "Esi"}


def _task(t: tuple) -> dict[str, Any]:
    tid, title, who, (by, byname), status, created, started, soft, final, items = t
    pc = next((m[0] for m in MACHINES if m[3] == who), None)
    return {"id": tid, "description_raw": title, "assignee_account_id": who, "assignee_name": NAMES.get(who, "?"),
            "assignee_pc_id": pc, "checks_total": len(items), "checks_passed": sum(1 for x in items if x[3] == "passed"),
            "assigner_account_id": by, "assigner_name": byname, "status": status,
            "verification_mode": "stack", "created_at": today(created), "started_at": today(started) if started is not None else None,
            "soft_deadline_at": at(soft - CONCEPT_NOW) if soft is not None else None,
            "final_deadline_at": at(final - CONCEPT_NOW), "completed_at": today(final + 4) if status == "completed" else None}


def task_list() -> dict[str, Any]:
    return {"tasks": [_task(t) for t in TASKS]}


def task_get(tid: int) -> dict[str, Any] | None:
    t = next((x for x in TASKS if x[0] == tid), None)
    if t is None:
        return None
    view = _task(t)
    items, ex = [], []
    for k, (typ, intent, name, st, sig) in enumerate(t[9]):
        iid = tid * 10 + k
        items.append({"id": iid, "sequence": k, "target_type": typ, "intent": intent,
                      "proposed_filename": name if typ == "file" else None, "program_name": name if typ == "program" else None,
                      "status": st, "populated_by": "llm", "passed_at": today(min(sig)) if st == "passed" and sig else None,
                      "linked_file_verification_item_id": tid * 10 if intent == "used_with_file" else None})
        ex += [{"verification_item_id": iid, "signal_type": "file.modified" if typ == "file" else "program.used",
                "observed_at": today(h), "value": None} for h in sig]
    view["items"], view["expectations"] = items, sorted(ex, key=lambda e: e["observed_at"], reverse=True)
    return {"task": view}


def dept_tasks(role: str, account: int) -> dict[str, Any]:
    rows = [(14, "Collect the signed leave forms from every team", 1, -20, 28, {7: "ongoing", 9: "seen"}),
            (13, "Prepare the stock count for the auditors", 2, -50, 3, {8: "done"}),
            (12, "Move last year's tender files to the archive", 1, -2, 74, {7: "told", 9: "told"}),
            (11, "Confirm who covers the front desk during the training week", 1, -70, -5, {7: "seen", 9: "ongoing"})]
    names = {7: "R. Mensah", 9: "A. Quaye", 8: "K. Boateng"}
    order = ["told", "seen", "ongoing", "done"]
    out = []
    for tid, title, dept, given, due, st in rows:
        if role == "admin" and account not in st:
            continue
        admins = [{"account_id": a, "name": names[a], "state": v, "state_at": at(-1) if v != "told" else None,
                   "seen_at": at(-2) if v != "told" else None} for a, v in st.items()]
        if role == "admin":
            admins = [a for a in admins if a["account_id"] == account]
        view = {"id": tid, "title": title, "department_id": dept, "assigner_name": "A. Quaye", "created_at": at(given),
                "deadline_at": at(due), "completed_at": None,
                "standing": max(st.values(), key=order.index), "told": len(st), "notes": [], "admins": admins}
        if role == "admin":
            view["my_state"] = st[account]
        out.append(view)
    res = {"tasks": out}
    if role == "admin":
        res["unseen"] = sum(1 for v in out if v["my_state"] == "told")
    return res


# --- messages -------------------------------------------------------------------------------------------
ACCOUNTS = {7: "R. Mensah", 9: "A. Quaye", 8: "K. Boateng", 21: "Kojo", 23: "Yaw", 27: "Ama", 31: "Afi", 41: "Esi"}
# id, initiator (lower), superior (higher), turn, opened (concept clock), closed, messages [(clock, sender, text)]
CHANNELS = [
    (20, 27, 7, "sender", 8.9, None, [(9.0, 7, "Is budget-2026.xlsx still open on your PC? It should not be there."),
                                      (9.25, 27, "It was sent to me to read before the meeting. I closed it."),
                                      (10.1, 7, "Thanks. Please delete your copy; it is marked to stay on WS-OPS-A1.")]),
    (18, 9, 7, "superior", 11.5, None, [(11.7, 9, "Before Friday's count, who covers the weekend?"),
                                        (12.1, 7, "I can take Saturday.")]),
    (16, 31, 8, "superior", 10.4, None, [(10.5, 8, "Go ahead, Afi."),
                                         (10.6, 31, "Someone on my team keeps taking my files off the shared drive and renaming them.")]),
    (15, 23, 7, "sender", -20.5, -19.4, [(-20.4, 7, "What is it, Yaw?"), (-20.1, 23, "The printer on the second floor will not take my jobs."),
                                         (-19.5, 7, "Fixed: it was paused. Try again.")]),
]


def _visible(c: tuple, account: int) -> bool:
    return account in (c[1], c[2])


def channels(account: int) -> dict[str, Any]:
    return {"channels": [{"id": c[0], "initiator_account_id": c[1], "superior_account_id": c[2], "turn": c[3],
                          "initiator_name": ACCOUNTS.get(c[1]), "opened_at": today(c[4]),
                          "closed_at": today(c[5]) if c[5] is not None else None}
                         for c in CHANNELS if _visible(c, account)]}


# everyone a console may message, as `assistance.people` answers: the other Admins and the workers (each a request)
_ADMINS = {7: ("R. Mensah", "Operations"), 9: ("A. Quaye", "Operations"), 8: ("K. Boateng", "Finance")}


def people(role: str, account: int) -> list[dict[str, Any]]:
    if role == "super_user":
        return [{"account_id": i, "name": n, "role": "admin", "department_name": d, "hostname": None, "request": False}
                for i, (n, d) in _ADMINS.items()]
    out = [{"account_id": i, "name": n, "role": "admin", "department_name": d, "hostname": None, "request": True}
            for i, (n, d) in _ADMINS.items() if i != account]
    out += [{"account_id": i, "name": ACCOUNTS[i], "role": "worker", "department_name": None, "hostname": h, "request": True}
            for i, h in ((21, "OPS-01"), (23, "OPS-03"), (27, "OPS-07"))]
    return out


def channel(cid: int, account: int) -> dict[str, Any] | None:
    c = next((x for x in CHANNELS if x[0] == cid), None)
    if c is None:
        return None
    turn_of = c[1] if c[3] == "sender" else c[2]
    return {"channel": {"id": c[0], "initiator_account_id": c[1], "superior_account_id": c[2], "subordinate_account_id": c[1],
                        "turn": c[3], "opened_at": today(c[4]), "closed_at": today(c[5]) if c[5] is not None else None,
                        "names": {str(c[1]): ACCOUNTS.get(c[1]), str(c[2]): ACCOUNTS.get(c[2])},
                        "my_turn": c[5] is None and account == turn_of,      # waiting on me; no turn lock since 22 Oct 2026
                        "can_close": c[5] is None and account == c[2]},
            "messages": [{"id": k, "sender_account_id": who, "body": text, "sent_at": today(t)} for k, (t, who, text) in enumerate(c[6])]}


# --- automation ------------------------------------------------------------------------------------------
# The concept's rules, its action library and every run of the week with what it returned (docs/design/concepts-admin.html).
_AU = json.loads((Path(__file__).with_name("preview_concept_automation.json")).read_text(encoding="utf-8"))
LIB = {i + 1: a for i, a in enumerate(_AU["lib"])}
_ACT = {n: i for i, a in LIB.items() for n in a["names"]}
_ACT["Back up the Documents folder"] = 20                   # a rule's own step, not in the library
OPS = [1, 2, 3, 4, 5, 6, 7]
_WEEKDAYS = [0, 1, 2, 3, 4]
# what each concept rule is in the Engine's terms: type, machines, match
_SPEC = {"usb": ("usb.inserted", OPS, {}), "restricted": ("resource.violation", None, {}), "cpu": ("threshold.cpu", OPS, {"percent": 90, "duration_s": 300}),
         "daily": ("time.recurring", None, {"at": "09:00", "days": _WEEKDAYS}), "signin": ("threshold.signin", OPS, {"count": 5, "window_s": 600}),
         "backup": ("time.recurring", OPS, {"at": "12:00", "days": _WEEKDAYS}), "printer": ("printer.offline", OPS, {}), "night": ("time.recurring", OPS, {"at": "20:00", "days": []})}
_HAND = {"usb": {4: 1}, "backup": {6: 1}, "daily": {3: 1}}   # runs by hand, by day of the week shown (6 is today)
_WORD = {"Success": "success", "Failed": "failed", "Timed out": "failed", "Stopped by you": "terminated"}
_MONTHS = {"Sep": 9, "Oct": 10}
AU_RULES = [dict(r, event_id=i + 1) for i, r in enumerate(_AU["rules"])]
_RULE_ID = {r["id"]: r["event_id"] for r in AU_RULES}
_BY = {"R. Mensah": 7, "A. Quaye": 9, "K. Boateng": 8}


def _at(t: float) -> str:
    """A time on the concept's axis, to the minute: the concept rounds where the console's clock would cut."""
    return at(round(t * 60) / 60 - CONCEPT_NOW)


def _mpc(host: str) -> int:
    return next((m[0] for m in MACHINES if m[1] == host), 0)


def _made(word: str) -> str:
    day, month = word.split()
    return datetime(2026, _MONTHS[month], int(day), 9, 0, tzinfo=NOW.tzinfo).isoformat()


def _rule_action(name: str, limit: int) -> dict[str, Any]:
    aid = _ACT[name]
    a = LIB.get(aid)
    kind = a["cat"].lower() if a else "custom"
    return {"id": aid, "name": name, "action_kind": kind, "builtin_type": None, "timeout_seconds": limit, "description": a["desc"] if a else None}


def events(role: str) -> dict[str, Any]:
    out = []
    for r in AU_RULES:
        typ, pcs, match = _SPEC[r["id"]]
        out.append({"id": r["event_id"], "enabled": not r["off"], "org_wide": False, "read_only": False, "created_at": _made(r["created"]), "created_by_account_id": _BY[r["by"]],
                    "name": r["name"], "condition_spec": {"type": typ, "pc_ids": pcs, "match": match}, "last_fired_at": None,
                    "actions": [_rule_action(n, lim) for n, lim in r["actions"]]})
    return {"events": out, "types": {}}


def all_runs() -> list[dict[str, Any]]:
    """Every run of the week as actions.runs answers it, from the rules the Actions page counts and by hand."""
    out = []
    for i, x in enumerate(_AU["runs"]):
        rule = next((r for r in AU_RULES if r["id"] == x["rule"]), None)
        out.append({"run_id": 50000 + i, "action_id": _ACT.get(x["action"], 0), "action": x["action"], "pc_id": _mpc(x["host"]), "host": x["host"], "at": _at(x["t"]),
                    "took_s": x["sec"], "limit_s": x["timeout"], "outcome": x["outcome"], "summary": x["out"]["summary"], "exit": x["exit"], "has_image": x["out"]["kind"] == "image",
                    "event_id": rule["event_id"] if rule else None, "by": f"rule: {rule['name']}" if rule else "hand", "who": x["by"]})
    return out


def run_output(run_id: int) -> dict[str, Any]:
    """control.execution for a run of the week: what the concept shows it returned."""
    x = _AU["runs"][run_id - 50000] if 50000 <= run_id < 50000 + len(_AU["runs"]) else None
    if x is None:
        return {"execution": {"id": run_id, "status": "success", "has_image": False, "summary": None}, "output": ["Recorded on the machine.", "exit code 0"], "result": None, "expired": False}
    o = x["out"]
    return {"execution": {"id": run_id, "status": _WORD[x["outcome"]], "outcome": x["outcome"], "has_image": o["kind"] == "image", "summary": o["summary"], "exit_code": x["exit"]},
            "output": (o.get("text") or "").splitlines(), "result": {"columns": o["cols"], "rows": o["rows"]} if o["kind"] == "list" else None, "expired": False}


def run_image(run_id: int) -> dict[str, Any]:
    src = _AU["runs"][run_id - 50000]["out"].get("src") or ""
    return {"data": base64.b64encode(src.encode("utf-8")).decode("ascii"), "mime": "image/svg+xml"}


def action_list() -> dict[str, Any]:
    acts: dict[str, list[dict[str, Any]]] = {"control": [], "monitoring": [], "custom": []}
    for aid, a in LIB.items():
        kind = a["cat"].lower()
        row = {"id": aid, "name": a["name"], "action_kind": kind, "builtin_type": None, "timeout_seconds": a["limit"], "description": a["desc"], "impact": a["impact"], "risky": a["risky"]}
        if kind == "custom":
            row.update({"custom_script_language": a["lang"].lower(), "custom_script": a["script"], "created_by_name": a["by"], "created_at": _made(a["created"])})
        acts[kind].append(row)
    return {"builtin": {}, "actions": acts}


def actions_board() -> dict[str, Any]:
    runs, out = all_runs(), []
    for aid, a in LIB.items():
        mine = [r for r in runs if r["action_id"] == aid]
        used = [{"event_id": _RULE_ID[i], "name": next(r["name"] for r in AU_RULES if r["id"] == i)} for i in a["used"]]
        out.append({"action_id": aid, "name": a["name"], "kind": a["cat"].lower(), "builtin_type": None, "timeout_s": a["limit"], "used_by": used, "runs": len(mine),
                    "by_hand": sum(1 for r in mine if r["by"] == "hand"), "problems": sum(1 for r in mine if r["outcome"] in ("Failed", "Timed out")),
                    "last_run": {"outcome": mine[0]["outcome"], "at": mine[0]["at"], "host": mine[0]["host"]} if mine else None, "days": []})
    return {"actions": out, "days": [], "period_days": 7,
            "strip": {"actions": len(out), "runs": len(runs), "by_hand": sum(1 for r in runs if r["by"] == "hand"),
                      "problems": sum(1 for r in runs if r["outcome"] in ("Failed", "Timed out"))}}


def _coming() -> list[dict[str, Any]]:
    """The concept's next scheduled runs: tonight, then tomorrow and Monday (today is a Thursday)."""
    return [{"at": at(d * 24 + h - CONCEPT_NOW), "event_id": _RULE_ID[i], "name": next(r["name"] for r in AU_RULES if r["id"] == i), "actions": len(next(r for r in AU_RULES if r["id"] == i)["actions"])}
            for d, h, i in ((0, 20, "night"), (1, 9, "daily"), (1, 12, "backup"), (4, 9, "daily"), (4, 12, "backup"))]


def automation_board(role: str) -> dict[str, Any]:
    """automation.board as the Engine answers it (engine/console/automation.py), for the concept's rules."""
    rules = []
    for r in AU_RULES:
        typ, pcs, _m = _SPEC[r["id"]]
        latest = r["fir"][0]["runs"] if r["fir"] else []
        counts: dict[str, int] = {}
        for x in latest:
            counts[x[4]] = counts.get(x[4], 0) + 1
        ok = counts.get("Success", 0)
        summary = None if not latest else ("Succeeded" if ok == 1 else f"All {ok} succeeded") if len(counts) == 1 and ok else \
            ", ".join(f"{counts[k]} {k.lower()}" for k in ("Timed out", "Failed", "Stopped by you", "Success") if counts.get(k))
        rules.append({"event_id": r["event_id"], "name": r["name"], "named": True, "type": typ, "kind": r["kind"].lower(), "when": r["when"], "owner": r["by"], "org_wide": False, "read_only": False,
                      "on": not r["off"], "scope": "every machine" if not pcs else f"{len(pcs)} machine(s)", "actions": [{"action_id": _ACT[n], "name": n} for n, _l in r["actions"]],
                      "fired": len(r["fir"]), "last_fired_at": at(r["fir"][0]["t"] - CONCEPT_NOW) if r["fir"] else None, "last_run": summary,
                      "last_run_problem": any(x[4] in ("Failed", "Timed out") for x in latest), "problems": sum(1 for f in r["fir"] for x in f["runs"] if x[4] in ("Failed", "Timed out"))})
    return {"rules": rules, "coming_up": _coming(), "days": [], "period_days": 7, "strip": {}}


def event_history(eid: int) -> dict[str, Any]:
    r = next((x for x in AU_RULES if x["event_id"] == eid), None)
    if r is None:
        return {"firings": []}
    firings, k = [], 0
    for f in r["fir"]:
        many = "machines" in f["host"]
        rr = []
        for host, name, _limit, sec, outcome, ex in f["runs"]:
            k += 1
            h = round(f["t"] * 60) / 60 - CONCEPT_NOW
            rr.append({"id": eid * 1000 + k, "action_id": _ACT.get(name, 0), "target_pc_id": _mpc(host), "host": host, "status": _WORD[outcome], "outcome": outcome, "started_at": at(h),
                       "ended_at": at(h + sec / 3600), "exit_code": ex or (1 if outcome == "Failed" else 0), "summary": None})
        firings.append({"at": _at(f["t"]), "pc_id": 0 if many else _mpc(f["host"]), "hostname": None if many else f["host"], "detail": f["detail"], "subject": None, "runs": rr,
                        "machines": len({x["target_pc_id"] for x in rr}) if many else 1})
    for day, n in _HAND.get(r["id"], {}).items():           # runs by hand count in the week's bars
        firings.extend({"at": at((day - 6) * 24 + 8 - CONCEPT_NOW), "pc_id": 1, "hostname": "OPS-01", "detail": None, "subject": None, "runs": [], "machines": 1, "by_hand": True} for _ in range(n))
    return {"event_id": eid, "firings": firings, "fired_today": 0, "running": []}


# --- announcements (alerts.sent) ------------------------------------------------------------------------
def alerts_sent() -> list[dict[str, Any]]:
    rows = [(5, "announcement", "New printer on the first floor", "The new printer by the stairs is ready. Pick FLOOR-1 when you print; the old one goes on Monday.", "Everyone", "R. Mensah", 33, "scheduled"),
            (4, "announcement", "Office closed on Monday 5 Oct", "The building is closed on Monday 5 October for the electrical inspection. Nobody can come in that day, including the warehouse. Work from home if you can.", "Everyone", "A. Quaye", 8.67, "delivered"),
            (3, "emergency", "Leave the building now", "The fire alarm in the warehouse has gone off. Use the stairs, not the lift, and meet at the car park by the main gate.", "Everyone", "A. Quaye", -8.67, "delivered"),
            (2, "warning", "Emails asking for parcel fees", "Emails asking you to pay a parcel fee are fake. Do not click them; delete them.", "Logistics", "R. Mensah", -77, "delivered"),
            (1, "announcement", "New parking rules from 1 Oct", "Staff parking moves to the back lot from 1 October.", "Everyone", "R. Mensah", -170, "withdrawn")]
    return [{"id": i, "alert_type": k, "title": t, "body": b, "audience_label": a, "from_name": by, "from_you": by == "R. Mensah", "deliver_at": at(h - CONCEPT_NOW), "status": st} for i, k, t, b, a, by, h, st in rows]


# --- reports ----------------------------------------------------------------------------------------------
# id, category, summary, hours ago, addressed (hours after, by), department it came from
REPORTS = [
    (3001, "resource_violation", "Copy of restricted budget-2026.xlsx on OPS-07", 3.3, None, 1),
    (3002, "resource_violation", "Copy of restricted salaries.csv on OPS-03", 3.8, (0.7, "R. Mensah"), 1),
    (3003, "deviation", "OPS-05 presented WS-OPS-05, expected OPS-05", 4.1, None, 1),
    (3004, "update_status", "LOG-02 update past the escalation limit", 76, None, 3),
    (3005, "update_status", "OPS-06 one version behind, 2 failed attempts", 26, (2.2, "A. Quaye"), 1),
    (3006, "flow_failure", "weekly: the branch to LOG-01 /archive/ paused", 30, (0.5, "R. Mensah"), 1),
    (3008, "about_admin", "A. Quaye entered LOG-02 outside working hours, 17 min", 11, None, 1),
    (3009, "about_admin", "A. Quaye entered LOG-01 outside working hours, 18 min", 141, None, 1),
]
ROUTING = {"resource_violation": [1, 2, 3], "flow_failure": [1, 2], "update_status": [1, 2, 3], "deviation": [1, 2, 3]}


def reports(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for rid, cat, summary, h, addr, dept in REPORTS:
        if role == "admin" and (cat == "about_admin" or dept != dept_id or dept_id not in ROUTING.get(cat, [])):
            continue
        out.append({"id": rid, "category": cat, "summary": summary, "generated_at": at(-h), "seen_at": None,
                    "addressed_at": at(-h + addr[0]) if addr else None})
    return {"reports": out}


REPORT_HOST = {3001: "OPS-07", 3002: "OPS-03", 3003: "OPS-05", 3004: "LOG-02", 3005: "OPS-06", 3006: "OPS-07", 3008: "LOG-02", 3009: "LOG-01"}
REPORT_LABEL = {"resource_violation": "Restricted file", "deviation": "Deviation", "update_status": "Update stuck", "flow_failure": "Flow failed",
                "about_admin": "About an Admin"}


def board(role: str, dept_id: int | None) -> dict[str, Any]:
    """reports.board as the Engine answers it (engine/console/overview.py): each report with whose it is."""
    with_admin = {d for _a, _n, d, *_ in ADMINS}
    names = dict(DEPTS)

    def owner(cat: str, d: int) -> str:
        if cat == "about_admin":
            return "fixed"
        if d not in with_admin:
            return "noadmin"
        return "dept" if d in ROUTING.get(cat, []) else "unrouted"
    views = []
    for rid, cat, summary, h, addr, d in REPORTS:
        o = owner(cat, d)
        if role == "admin" and (o != "dept" or d != dept_id):
            continue
        host = REPORT_HOST[rid]
        views.append({"id": rid, "category": cat, "label": REPORT_LABEL.get(cat, cat), "summary": summary, "at": at(-h),
                      "pc_id": HOST[host][0], "host": host, "department_id": d, "department_name": names[d], "owner": o, "seen": False,
                      "addressed": {"by": addr[1], "at": at(-h + addr[0]), "took_minutes": round(addr[0] * 60)} if addr else None})
    took = sorted(v["addressed"]["took_minutes"] for v in views if v["addressed"] and v["owner"] == "dept")
    med = took[len(took) // 2] if took else None
    handling = []
    if role == "super_user":
        for d, n in DEPTS:
            mine = [v for v in views if v["department_id"] == d and v["owner"] == "dept"]
            t = sorted(v["addressed"]["took_minutes"] for v in mine if v["addressed"])
            handling.append({"department_id": d, "name": n, "has_admin": d in with_admin, "all": len([v for v in views if v["department_id"] == d]),
                             "done": len(t), "waiting": len(mine) - len(t), "to_you": sum(1 for v in views if v["department_id"] == d and v["owner"] != "dept" and not v["addressed"]),
                             "median_minutes": t[len(t) // 2] if t else None})
    strip = {"waiting": sum(1 for v in views if v["owner"] != "dept" and not v["addressed"]) if role == "super_user" else sum(1 for v in views if not v["addressed"]),
             "with_department": sum(1 for v in views if v["owner"] == "dept" and not v["addressed"]) if role == "super_user" else None,
             "addressed": sum(1 for v in views if v["addressed"]), "typical_minutes": med}
    return {"reports": views, "strip": strip, "handling": handling, "categories": sorted({v["category"] for v in views})}


# the concept's conversations (amConvs): id, kind, title, other accounts, unread, messages (hours from now, from, body); and its one request to talk
CONVS = [
    (31, "direct", "K. Boateng", [8], 1, [(-1.4, 8, "About intake: I will pick its folder on WS-FIN-A1 this afternoon.")]),
    (32, "admins", "Admins", [9, 8], 2, [(-27, 9, "Before Friday's count, who covers the weekend?"), (-26.2, 7, "I can take Saturday."), (-2.4, 9, "Sunday is mine then. We will both be on call by phone.")]),
    (20, "direct", "Ama", [27], 0, [(-4.333, 7, "Is budget-2026.xlsx still open on your PC? It should not be there."), (-4.083, 27, "It was sent to me to read before the meeting. I closed it."),
                                    (-3.233, 7, "Thanks. Please delete your copy; it is marked to stay on WS-OPS-A1.")]),
    (15, "direct", "Yaw", [23], 0, [(-33.733, 7, "What is it, Yaw?"), (-33.433, 23, "The printer on the second floor will not take my jobs."), (-32.833, 7, "Fixed: it was paused. Try again.")]),
]
REQUESTS = [{"id": 1, "from": "Esi", "account_id": 41, "host": "LOG-01", "at": at(-0.85), "line": "The label printer prints blank labels"}]


def _chat(type_: str, payload: dict[str, Any], account: int) -> dict[str, Any]:
    """The version 1 conversations (engine/resource/conversations.py), with the concept's sample."""
    def view(c: tuple) -> dict[str, Any]:
        cid, kind, title, others, unread, msgs = c
        last = msgs[-1]
        return {"conversation_id": cid, "kind": kind, "title": title, "members": [{"account_id": a, "name": ACCOUNTS.get(a)} for a in [account] + others],
                "last": {"body": last[2], "from_account_id": last[1], "from": ACCOUNTS.get(last[1]), "at": at(last[0])}, "unread": unread, "seen_by": []}
    if type_ == "chat.list":
        vs = sorted((view(c) for c in CONVS), key=lambda v: v["last"]["at"], reverse=True)
        return {"conversations": vs, "unread": sum(v["unread"] for v in vs)}
    if type_ == "chat.requests":
        return {"requests": REQUESTS}
    if type_ == "chat.people":
        people = [{"account_id": a, "name": n, "role": "admin" if a in (7, 8, 9) else "worker", "pc_id": a, "hostname": next((x[4] for x in ADMINS if x[0] == a), None) or
                   next((m[1] for m in MACHINES if len(m) > 2 and m[2] == n), "OPS-01"), "department": "Operations", "online": True} for a, n in ACCOUNTS.items() if a != account]
        return {"people": people, "admins_group": True}
    if type_ == "chat.get":
        c = next((x for x in CONVS if x[0] == int(payload.get("conversation_id") or 0)), None)
        if c is None:
            return {"conversation": None, "messages": [], "more": False, "reads": []}
        return {"conversation": view(c), "more": False, "reads": [],
                "messages": [{"message_id": c[0] * 100 + i, "from_account_id": w, "from": ACCOUNTS.get(w), "body": t, "at": at(h), "mine": w == account, "file": None} for i, (h, w, t) in enumerate(c[5])]}
    if type_ == "chat.open":
        c = next((x for x in CONVS if payload.get("account_id") in x[3]), CONVS[0])
        return {"conversation": view(c)}
    if type_ == "chat.send":
        return {"message_id": 1, "at": at(0)}
    return {"conversation_id": payload.get("conversation_id"), "read": True}


_TODOS_DONE: set[int] = {4}


def _todos() -> dict[str, Any]:
    """todo.list as the Engine answers it (engine/task/todos.py): the Admin's own to-dos; the strip is what is past its date or due
    within the hour."""
    # the concept's (TODOS), hours from now: due 08:20 today, Fri 17:20, Sun 15:20, and one done
    rows = [(1, "Confirm who covers the front desk during the training week", -5.0), (2, "Collect the signed leave forms from every team", 28.0),
            (3, "Move last year's tender files to the archive", 74.0), (4, "Update the fire-drill list for every floor", -18.0)]
    todos = []
    for i, text, h in rows:
        done = i in _TODOS_DONE
        todos.append({"id": i, "text": text, "due_at": at(h), "done": done, "done_at": at(-15.33) if done else None, "overdue": not done and h < 0, "on_strip": not done and h < 1})
    return {"todos": todos, "open": sum(1 for t in todos if not t["done"]), "strip": [t for t in todos if t["on_strip"]]}


def answer(type_: str, payload: dict[str, Any], role: str, account: int, dept_id: int | None) -> Any:
    """The sample's answer to one call, or None when the sample does not cover it."""
    if type_.startswith(("detective.", "proposals.")):
        import preview_detective
        return preview_detective.answer(type_, payload, role, dept_id)
    if type_.startswith("chat."):
        return _chat(type_, payload, account)
    if type_ == "todo.list":
        return _todos()
    if type_ == "todo.done":
        _TODOS_DONE.add(int(payload.get("todo_id") or 0))
        return {"todo": next((t for t in _todos()["todos"] if t["id"] == int(payload.get("todo_id") or 0)), None)}
    if type_ == "alerts.sent":
        return {"alerts": alerts_sent()}
    if type_ == "flow.steps":
        ops = {"Choosing": ["By file type", "By name", "By size"], "Conversion": ["To PDF", "To DOCX", "To another image type", "Zip each file"],
               "Renaming": ["Add a date", "Add text", "Replace text in the name"], "Bundling": ["Into one ZIP", "Into one PDF"]}
        return {"tree": [{"category": "all", "label": "Steps", "kinds": [{"kind": k.lower(), "label": k, "ops": [{"op": o, "label": o} for o in v]} for k, v in ops.items()]}], "order": []}
    if type_ == "flow.restricted_waiting":
        return {"waiting": restricted_waiting()}
    if type_ == "flow.restricted":
        return {"consents": [{"id": 5, "flow_id": 1, "name": "payroll", "state": "asked", "asked_at": at(-0.43), "sample_path": "OPS-01 /payroll/salaries.csv"}] if int(payload.get("flow_id") or 0) == 1 else [],
                "can_decide": [5]}
    if type_ == "flow.runs":
        return flow_runs(int(payload.get("flow_id") or 0))
    if type_ == "calendar.board":
        return calendar_board()
    if type_ == "hierarchy.tree":
        return tree(role, dept_id)
    if type_ == "hierarchy.sessions_today":
        return sessions_today(role, dept_id)
    if type_ == "resource.violations":
        return violations(role, dept_id)
    if type_ == "updates.rollout_health":
        return rollout(role, dept_id)
    if type_ == "assistance.ping_status":
        return pings(role, account)
    if type_ == "rollout.gate":
        return rollout_gate(role, dept_id)
    if type_ == "registry.refused":
        return registry_refused()
    if type_ == "registry.accounts":
        return registry_accounts(account)
    if type_ in ("registry.block", "registry.unblock"):
        return {"address": payload.get("address")}
    if type_ == "rules.list":
        return rules_list()
    if type_ == "rules.library":
        return rules_library()
    if type_ == "rules.try":
        return {"deviations": 3, "would_clear": 1 if (payload.get("within") or 0) >= 90 else 0, "would_remain": 3 - (1 if (payload.get("within") or 0) >= 90 else 0), "counted": 3}
    if type_ == "deviations.list":
        return deviations_list()
    if type_ == "deviations.get":
        return deviations_get(int(payload.get("deviation_id") or 0))
    if type_ == "deviations.outcome":
        return {"deviation": next((_dev(x) for x in DEVS if x[0] == int(payload.get("deviation_id") or 0)), {})}
    if type_ == "audit.deviations":
        return deviations(role, dept_id, bool(payload.get("include_resolved")))
    if type_ == "hierarchy.traverse":
        pc = int(payload.get("pc_id") or 0)
        return {"session": {"session_id": 900 + pc, "pc_id": pc, "occupied_via": "traversal", "occupant_account_id": account,
                            "entered_at": at(0), "deadline_at": at(0.5)}}
    if type_ == "hierarchy.end_session":
        return {"session_id": payload.get("session_id"), "status": "ended"}
    if type_ == "marks.list":
        return marks_list(role, account)
    if type_ == "marks.get":
        return marks_get(int(payload.get("mark_id") or 0), account)
    if type_ == "marks.tree":
        return marks_tree()
    if type_ == "issues.list":
        return issues_list(role, dept_id, account)
    if type_ == "issues.get":
        return issues_get(int(payload.get("issue_id") or 0), account)
    if type_ == "issues.act":
        return {"issue": {**_issue(next(x for x in ISSUES if x[0] == int(payload.get("issue_id") or 0)), account), "state": "waiting"}, "done": "ok"}
    if type_ == "machines.get":
        return machines_get(int(payload.get("pc_id") or 0), str(payload.get("range") or "24h"))
    if type_ == "machines.list":
        return machines_list(role, dept_id)
    if type_ == "enroll.list":
        return enroll_list(role)
    if type_ == "audit.recent" and payload.get("prefix") == "auth.failed":
        return refused()
    if type_ == "audit.recent":
        return audit(role, dept_id, int(payload.get("limit") or 100))
    if type_ == "task.list":
        return task_list()
    if type_ == "task.get":
        return task_get(int(payload.get("task_id") or 0))
    if type_ == "assistance.channels":
        return channels(account)
    if type_ == "assistance.channel":
        return channel(int(payload.get("channel_id") or 0), account)
    if type_ == "assistance.my_admins":
        return {"admins": []}
    if type_ == "assistance.people":
        return {"people": people(role, account)}
    if type_ == "index.folders":
        fs = [r"C:\Finance", r"C:\Finance\Invoices", r"C:\HR", r"C:\HR\Payroll", r"C:\HR\Reviews", r"C:\HR\Contracts",
              r"C:\Users\RMensah\Documents", r"C:\Users\RMensah\Desktop", r"D:\Board", r"D:\Archive"]
        return {"pc_id": 101, "hostname": "WS-OPS-A1", "folders": [{"path": f, "name": f.split("\\")[-1], "files": 3 + (len(f) * 7) % 40} for f in fs]}
    if type_ == "reports.list":
        return reports(role, dept_id)
    if type_ == "reports.board":
        return board(role, dept_id)
    if type_ == "reports.routing_get":
        return {"categories": list({r[1] for r in REPORTS}), "fixed": ["about_admin"],
                "routing": [{"category": c, "routed_department_id": d, "department_name": dict(DEPTS)[d]} for c, ds in ROUTING.items() for d in ds]}
    if type_ == "reports.addressed_view":
        return {"addressed": [{"report_id": r[0], "addressed_by_name": r[4][1], "addressed_at": at(-r[3] + r[4][0]), "department_name": dict(DEPTS)[r[5]]}
                              for r in REPORTS if r[4]]}
    if type_ == "control.action_list":
        return action_list()
    if type_ == "actions.board":
        return actions_board()
    if type_ == "actions.runs":
        aid = payload.get("action_id")
        rs = [r for r in all_runs() if aid is None or r["action_id"] == aid]
        return {"runs": rs[: int(payload.get("limit") or 50)], "total": len(rs)}
    if type_ == "automation.board":
        return automation_board(role)
    if type_ == "control.event_test":
        return {"event_id": payload.get("event_id"), "pc_id": payload.get("pc_id"), "runs": []}
    if type_ == "control.event_list":
        return events(role)
    if type_ == "control.event_history":
        return event_history(int(payload.get("event_id") or 0))
    if type_ == "control.action_try":
        return {"execution_id": 77, "pc_id": payload.get("pc_id"), "hostname": "OPS-01"}
    if type_ == "control.execution":
        return run_output(int(payload.get("execution_id") or 0))
    if type_ == "control.execution_image_get":
        return run_image(int(payload.get("execution_id") or 0))
    if type_ == "hierarchy.pc_state":
        pc = int(payload.get("pc_id") or 0)
        m = next((x for x in MACHINES if x[0] == pc), None)
        if not m:
            return None
        cpu = {"OPS-03": 94.0, "OPS-07": 71.0, "OPS-05": 63.0}.get(m[1], 8 + (pc * 7) % 25)
        return {"pc_id": pc, "hostname": m[1], "online": m[5], "last_seen_at": at(-m[6]),
                "levels": {"cpu": cpu, "memory": 52.0, "idle_s": 3.0, "at": at(0)} if m[5] else None}
    return None
