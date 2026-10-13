"""The console concept's "small" sample, as the Engine would answer it, dated around now.

`scripts/preview.py` answers every `falcon.call` from here, so the real QML can be looked at and
screenshotted beside the published concept (Falcon Concepts) with the same machines, people and
events. Times are hours relative to now (negative is earlier), the concept's own time axis.

Not product code: nothing imports this but the preview.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

REAL_NOW = datetime.now(timezone.utc).astimezone()
# the sample is laid out around the concept's 13:20, so the preview's clock reads 13:20 today whatever the real time
# is (the preview tells the console's Time the same skew): the day's charts then look as they do in the concept
NOW = REAL_NOW.replace(hour=13, minute=20, second=0, microsecond=0)
SKEW_MS = (NOW - REAL_NOW).total_seconds() * 1000


def at(hours: float) -> str:
    """An ISO time `hours` from now (negative: earlier)."""
    return (NOW + timedelta(hours=hours)).isoformat()


CONCEPT_NOW = 13 + 20 / 60       # the concept's "now", 13:20; the sample is laid out around it


def today(h: float) -> str:
    """The concept's clock hour `h` (13.33 is now), placed the same distance before the real now."""
    return at(min(h, CONCEPT_NOW) - CONCEPT_NOW)


# --- the estate --------------------------------------------------------------------------------------
# account ids: Super User 1; Admins 7 (R. Mensah), 9 (A. Quaye), 8 (K. Boateng); workers 21..
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
    (22, "LOG-02", "Abena", 42, 3, False, 11.0),
]
HOST = {m[1]: m for m in MACHINES}
# who is inside a machine now: host -> (occupant, account, via, entered hours ago)
HELD = {"OPS-04": ("R. Mensah", 7, "traversal", 0.4), "OPS-07": ("You", 1, "traversal", 2.6)}


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


def tree(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for did, name in DEPTS:
        if role == "admin" and did != dept_id:
            continue
        admins = [{"account_id": a, "role": "admin", "name": n, "status": "active", "pc_id": pc, "hostname": ws,
                   "pc_type": "admin_workstation", "online": True, "last_seen_at": at(0),
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
             ("FIN-02", 9.3, 9.67, "K. Boateng", "assisted"), ("FIN-02", 9.68, None, "Kofi", "native")]
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


# --- the registry: machines with their keys, refused connections, a machine asking to join ------------------
GEN = {"OPS-05": 2, "OPS-06": 2, "LOG-02": 3}


def machines_list(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for pc, host, user, acct, dept, online, seen in MACHINES:
        if role == "admin" and dept != dept_id:
            continue
        out.append({"pc_id": pc, "hostname": host, "department_id": dept, "key_generation": GEN.get(host, 1),
                    "owner": {"account_id": acct, "name": user}, "ip": f"10.20.{dept + 3}.{10 + pc}", "online": online,
                    "version": "1.4.0" if host == "LOG-02" else "1.4.1" if host == "OPS-06" else "1.4.2",
                    "behind": host in ("LOG-02", "OPS-06"), "last_seen_at": at(-seen),
                    # the readings now, as machines.list carries them from each machine's last report
                    "cpu": round(8 + 80 * _nz(7 + pc, 3), 1) if online else None, "memory": round(40 + 40 * _nz(9 + pc, 5), 1) if online else None,
                    "disk": round(30 + 65 * _nz(11 + pc, 2), 1) if online else None,
                    "held_by_you": host == "OPS-07"})
    for acct, host, pc in ((1, "ADM-01", 100), (7, "ADM-OPS-01", 101), (8, "ADM-FIN-01", 102), (9, "ADM-OPS-02", 103)):
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


def enroll_list(role: str) -> dict[str, Any]:
    return {"requests": [{"id": 4, "hostname": "OPS-08", "os": "Windows 11 Pro", "mac": "3c:52:82:aa:10:08", "peer": "10.20.4.18",
                          "requested_department_id": 1, "requested_level": "worker", "created_at": at(-0.6), "expires_at": at(23.4)}]}


# --- issues as the Engine keeps them (issues.list / issues.get / issues.act) ------------------------------------
ISSUES = [  # id, code, type, severity, title, subject, pc, hours old, owner account, state, label, escalated
    (41, "I-41", "file", "critical", "Restricted file copied where it isn't allowed", "budget-2026.xlsx", 7, 3.3, 7, "open", None, False),
    (42, "I-42", "file", "high", "Restricted file copied where it isn't allowed", "salaries.csv", 3, 3.8, 7, "open", None, False),
    (43, "I-43", "deviation", "medium", "Machine presented another name", "presented WS-OPS-05", 5, 4.1, 7, "open", None, False),
    (44, "I-44", "update", "high", "Update past the escalation limit", "1.4.0 → 1.4.2", 22, 76.0, None, "open", "Escalated", True),
    (45, "I-45", "update", "medium", "One version behind", "1.4.1 → 1.4.2, 2 failed attempts", 6, 26.0, 7, "waiting", "Retrying when idle", False),
    (46, "I-46", "offline", "medium", "Not checking in", "since 02:31", 22, 11.0, None, "open", "Escalated", True),
]
_TARGET = {"file": 1, "update": 24, "deviation": 8, "flow": 72, "offline": 72}
_TLABEL = {"file": "Restricted file", "update": "Stuck update", "deviation": "Deviation", "flow": "Flow blocked", "offline": "Not checking in"}


def _issue(t: tuple, account: int) -> dict[str, Any]:
    iid, code, type_, sev, title, subject, pc, age, owner, state, label, esc = t
    m = next(x for x in MACHINES if x[0] == pc)
    return {"id": iid, "code": code, "type": type_, "type_label": _TLABEL[type_], "severity": sev, "title": title, "subject": subject,
            "pc_id": pc, "host": m[1], "department_id": m[4], "department_name": {1: "Operations", 2: "Finance", 3: "Logistics"}[m[4]],
            "opened_at": at(-age), "age_hours": age, "target_hours": _TARGET[type_], "past_target": state != "resolved" and age > _TARGET[type_],
            "owner": {"account_id": owner, "name": NAMES.get(owner, "?"), "you": owner == account} if owner else None,
            "state": state, "label": label or {"open": "Open", "waiting": "Waiting"}[state], "escalated": esc, "resolved_at": None, "resolution": None}


def issues_list(role: str, dept_id: int | None, account: int) -> dict[str, Any]:
    out = [_issue(t, account) for t in ISSUES]
    if role == "admin":
        out = [i for i in out if i["department_id"] == dept_id]
    return {"issues": out, "summary": {"open": sum(i["state"] == "open" for i in out), "waiting": sum(i["state"] == "waiting" for i in out),
                                       "past_target": sum(i["past_target"] for i in out), "done_today": 2, "mine": 0}}


def issues_get(iid: int, account: int) -> dict[str, Any]:
    t = next(x for x in ISSUES if x[0] == iid)
    i = _issue(t, account)
    host, who = i["host"], next(x[2] for x in MACHINES if x[0] == i["pc_id"]) or "Nobody"
    if i["type"] == "file":
        lead = f"A copy of {i['subject']}, marked restricted, is on {host}. It may only be where it was marked."
        facts = [["File", i["subject"]], ["Found on", host], ["Signed in", who], ["Severity", i["severity"].capitalize()]]
        options = [{"key": "ask", "title": f"Ask {who} to delete it", "desc": f"{who} sees which file and why. The issue closes on its own when the copy is gone.", "verb": "Ask", "done": "Waiting"},
                   {"key": "delete", "title": "Delete this copy", "desc": f"Deletes it from {host} only. The original is not touched.", "verb": "Delete copy", "done": "Waiting"},
                   {"key": "allow", "title": f"Allow it on {host} too", "desc": "Adds this one place to what is allowed, with your reason. It is not reported again.", "verb": "Allow it", "done": "Resolved", "need": "reason"}]
    elif i["type"] == "deviation":
        lead = f"{host} presented a name it was not registered with."
        facts = [["Registered as", host], ["Presented", "WS-OPS-05"], ["Seen", "Today"]]
        options = [{"key": "accept", "title": "Accept WS-OPS-05", "desc": "Registers the machine as WS-OPS-05.", "verb": "Accept", "done": "Resolved"},
                   {"key": "reverse", "title": f"Put it back to {host}", "desc": f"Waits for the machine to present {host} again; the issue closes when it does.", "verb": "Put it back", "done": "Waiting"}]
    else:
        lead = f"{host} is behind the approved version." if i["type"] == "update" else f"{host} stopped checking in."
        facts = [["Machine", host], ["Since", i["opened_at"][11:16]]]
        options = [{"key": "wait", "title": "Wait for it to come back", "desc": f"It retries as soon as {host} checks in again.", "verb": "Keep waiting", "done": "Waiting"},
                   {"key": "exclude", "title": "Leave it out of the next version's gate", "desc": "The next version can then be approved without it.", "verb": "Leave it out", "done": "Resolved", "need": "reason"}]
    timeline = [{"at": i["opened_at"], "who": "System", "what": f"Raised: {i['title']}", "kind": "raised", "you": False}]
    return {"issue": i, "detail": {}, "lead": lead, "facts": facts, "options": options, "why": [], "timeline": timeline}


# --- restricted marks (marks.list / marks.get / marks.tree) ------------------------------------------------------
def marks_list(role: str, account: int) -> dict[str, Any]:
    ws, pc = ("WS-OPS-A1", 101) if account == 7 else ("ADM-01", 100)          # the console's own PC, as FakeIdentity says
    ms = [{"id": 3, "code": "M-3", "kind": "file", "name": "budget-2026.xlsx", "pc_id": pc, "host": ws, "path": "C:/Users/R.Mensah/Finance/budget-2026.xlsx",
           "keep": "machine", "keep_label": "Anywhere on the PC", "by": {"account_id": account, "name": "You", "you": True}, "files": 1, "versions": 13,
           "copies": 1, "worst": "critical", "created_at": at(-200)},
          {"id": 4, "code": "M-4", "kind": "folder", "name": "Payroll", "pc_id": pc, "host": ws, "path": "C:/HR/Payroll",
           "keep": "path", "keep_label": "Only in its place", "by": {"account_id": account, "name": "You", "you": True}, "files": 24, "versions": 31,
           "copies": 1, "worst": "high", "created_at": at(-400)},
          {"id": 5, "code": "M-5", "kind": "file", "name": "supplier-contracts-2026.pdf", "pc_id": pc, "host": ws, "path": "C:/Users/R.Mensah/Contracts/supplier-contracts-2026.pdf",
           "keep": "machine", "keep_label": "Anywhere on the PC", "by": {"account_id": account, "name": "You", "you": True}, "files": 1, "versions": 2,
           "copies": 0, "worst": None, "created_at": at(-90)}]
    return {"marks": ms, "summary": {"marks": 3, "files": 26, "copies": 2, "with_copies": 2}}


def marks_get(mid: int, account: int) -> dict[str, Any]:
    m = next(x for x in marks_list("admin", account)["marks"] if x["id"] == mid)
    copies = {3: [{"issue_id": 41, "code": "I-41", "severity": "critical", "state": "open", "label": "Open", "host": "OPS-07", "file": "budget-2026.xlsx",
                   "folder": "C:/Users/Ama/Documents", "path": "C:/Users/Ama/Documents/budget-2026.xlsx", "signed_in": "Ama", "opened_at": at(-3.3), "age_hours": 3.3}],
              4: [{"issue_id": 42, "code": "I-42", "severity": "high", "state": "open", "label": "Open", "host": "OPS-03", "file": "salaries.csv",
                   "folder": "C:/Users/Yaw/Desktop", "path": "C:/Users/Yaw/Desktop/salaries.csv", "signed_in": "Yaw", "opened_at": at(-3.8), "age_hours": 3.8}]}.get(mid, [])
    return {"mark": m, "copies": copies, "resolved_copies": [], "change": {"keep": "path" if m["keep"] == "machine" else "machine", "effect": {"would_flag": 0, "would_clear": 0}}}


def marks_tree() -> dict[str, Any]:
    folders = ["C:/Users/R.Mensah/Documents", "C:/Users/R.Mensah/Documents/Reports", "C:/Users/R.Mensah/Finance", "C:/Users/R.Mensah/Contracts",
               "C:/HR", "C:/HR/Payroll", "C:/HR/Leave", "C:/Shared/Templates"]
    return {"pc_id": 101, "hostname": "WS-OPS-A1", "files": [], "folders": [{"path": f, "files": 3 + (len(f) * 7) % 40} for f in folders], "truncated": False}


def machines_get(pc: int, rng: str) -> dict[str, Any]:
    hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}.get(rng, 24)
    step = hours / 48
    def ser(seed: float, base: float, amp: float) -> list[dict[str, Any]]:
        return [{"at": at(-hours + k * step), "v": round(max(0.0, min(100.0, base + amp * (_nz(seed + pc, k) - 0.5) * 2)), 1)} for k in range(49)]
    procs = [("EXCEL.EXE", 6.2, 412, "Kojo"), ("chrome.exe", 4.1, 880, "Kojo"), ("OUTLOOK.EXE", 1.3, 260, "Kojo"),
             ("falcon-worker.exe", 0.4, 48, "SYSTEM"), ("MsMpEng.exe", 0.9, 190, "SYSTEM"), ("explorer.exe", 0.2, 96, "Kojo")]
    return {"machine": {"pc_id": pc}, "range": rng,
            "series": {"cpu": ser(1, 28, 22), "memory": ser(2, 61, 8), "disk": ser(3, 47, 1), "net_kbps": ser(4, 40, 35)},
            "processes": {"at": at(-0.05), "items": [{"pid": 1000 + i, "name": n, "cpu": c, "memory_mb": m, "user": u} for i, (n, c, m, u) in enumerate(procs)]},
            "sessions": [], "files": {}, "events": []}


# --- the audit trail, 7 days ---------------------------------------------------------------------------
def _nz(seed: float, k: float) -> float:
    x = math.sin(k * 127.1 + seed * 311.7) * 43758.5453
    return x - math.floor(x)


def audit(role: str, dept_id: int | None, limit: int) -> dict[str, Any]:
    hosts = [m for m in MACHINES if m[2]]
    acts = ["Lock the screen", "Take a screenshot", "Check disk health", "Clear the temp folder", "Log event"]
    out: list[dict[str, Any]] = []
    k = 0
    h = -168.0
    while h < 0:
        t = NOW + timedelta(hours=h)
        working = t.weekday() < 5 and 8 <= t.hour < 17.5
        n = int((2.6 if working else 0.3) * _nz(41, h) * 1.6 + _nz(5, h * 4))
        for _ in range(n):
            r, m = _nz(9, k * 3 + 1), hosts[int(_nz(13, k) * len(hosts))]
            if r < 0.36:
                e = ("Automation", f"{acts[int(_nz(19, k) * len(acts))]} ran", m[1], "control.action_run")
            elif r < 0.58:
                e = (m[2], "Signed in" if _nz(23, k) > 0.5 else "Signed out", m[1], "session.native")
            elif r < 0.78:
                e = ("System", f"payroll synced {1 + int(_nz(29, k) * 12)} files to FIN-01", "OPS-01", "flow.sync")
            elif r < 0.9:
                e = (m[2], "Searched shared resources", m[1], "assistance.search")
            else:
                e = ("System", "Checked for updates", m[1], "update.check")
            if not (m[1] == "LOG-02" and h > -11):
                out.append({"id": 10000 + k, "occupied_at": None, "occurred_at": (t + timedelta(minutes=_nz(17, k) * 15)).isoformat(),
                            "actor_name": e[0], "summary": e[1], "target_hostname": e[2], "action": e[3]})
            k += 1
        h += 0.25
    notable = [
        (-3.3, "System", "Copy of restricted budget-2026.xlsx found", "OPS-07", "resource.violation"),
        (-3.8, "System", "Copy of restricted salaries.csv found", "OPS-03", "resource.violation"),
        (-4.1, "System", "Certificate presented WS-OPS-05, expected OPS-05", "OPS-05", "deviation.hostname"),
        (-3.6, "Kojo", "Pinged R. Mensah", "OPS-01", "assistance.ping"),
        (-3.1, "Kojo", "Pinged R. Mensah again", "OPS-01", "assistance.ping"),
        (-2.6, "You", "Entered OPS-07", "OPS-07", "session.traversed"),
        (-0.8, "R. Mensah", "Entered OPS-03", "OPS-03", "session.traversed"),
        (-0.6, "Automation", "CPU above 90% for 5 min on OPS-03, notified R. Mensah", "OPS-03", "control.event_fired"),
        (-0.4, "R. Mensah", "Entered OPS-04", "OPS-04", "session.traversed"),
        (-0.15, "R. Mensah", "Left OPS-03", "OPS-03", "session.ended"),
        (-11.1, "A. Quaye", "Entered LOG-02 (outside working hours)", "LOG-02", "session.traversed"),
        (-10.8, "A. Quaye", "Left LOG-02", "LOG-02", "session.ended"),
        (-76.0, "System", "LOG-02 update escalated to Super User", "LOG-02", "update.escalated"),
        (-26.0, "System", "1.4.2 install failed on OPS-06 (attempt 2)", "OPS-06", "update.failed"),
    ]
    for j, (hh, who, what, host, action) in enumerate(notable):
        out.append({"id": 90000 + j, "occurred_at": at(hh), "actor_name": who, "summary": what,
                    "target_hostname": host, "action": action})
    if role == "admin":
        out = [e for e in out if not e["target_hostname"] or HOST.get(e["target_hostname"], (0, 0, 0, 0, dept_id))[4] == dept_id]
    out.sort(key=lambda e: e["occurred_at"], reverse=True)
    return {"entries": out[:limit]}


# --- tasks ----------------------------------------------------------------------------------------------
# id, title, assignee account, assigner (account, name), status, created h, started h, soft h, final h (concept clock),
# items: (type, intent, name, status, signal hours), linked index for used_with_file
TASKS = [
    (208, "Reconcile the Q3 invoices", 21, (7, "R. Mensah"), "in_progress", -63, -38.75, 36, 41,
     [("file", "update", "reconciliation.xlsx", "passed", [-38, -30, -28, -7.3, 9.03, 12.97]),
      ("program", "used_with_file", "EXCEL.EXE", "passed", [-37, -29, -6, 9.03, 10.5, 12.0]),
      ("file", "create", "q3-summary.docx", "pending", [])]),
    (204, "Clear duplicate files from the shared drive", 25, (7, "R. Mensah"), "in_progress", -90, -80, None, 113,
     [("file", "exists", "/common/duplicates/", "passed", [-66, -62, -58]),
      ("file", "create", "duplicates-report.xlsx", "pending", [])]),
    (203, "Install the label printer driver", 26, (9, "A. Quaye"), "in_progress", -100, -98, None, -10,
     [("program", "installed_available", "LabelPrint.exe", "passed", [-34])]),
    (209, "Collect the laptop chargers from the meeting room", 27, (7, "R. Mensah"), "active", -70, None, None, -2,
     [("file", "create", "chargers-list.xlsx", "pending", [])]),
    (200, "Back up the Documents folder", 27, (7, "R. Mensah"), "completed", -160, -158, None, -100,
     [("file", "create", "documents-backup.zip", "passed", [-108.9])]),
]
NAMES = {21: "Kojo", 25: "Nana", 26: "Kwame", 27: "Ama", 23: "Yaw"}


def _task(t: tuple) -> dict[str, Any]:
    tid, title, who, (by, byname), status, created, started, soft, final, _items = t
    return {"id": tid, "description_raw": title, "assignee_account_id": who, "assignee_name": NAMES.get(who, "?"),
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
                      "status": st, "populated_by": "llm",
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
        view = {"id": tid, "title": title, "department_id": dept, "assigner_name": "Super User", "created_at": at(given),
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
ACCOUNTS = {1: "Super User", 7: "R. Mensah", 9: "A. Quaye", 8: "K. Boateng", 21: "Kojo", 23: "Yaw", 27: "Ama", 31: "Afi"}
# id, initiator (lower), superior (higher), turn, opened (concept clock), closed, messages [(clock, sender, text)], listeners {adder: [admin]}
CHANNELS = [
    (20, 27, 7, "sender", 8.9, None, [(9.0, 7, "Is budget-2026.xlsx still open on your PC? It should not be there."),
                                      (9.25, 27, "It was sent to me to read before the meeting. I closed it."),
                                      (10.1, 7, "Thanks. Please delete your copy; it is marked to stay on WS-OPS-A1.")], {7: [9]}),
    (18, 7, 1, "superior", 11.5, None, [(11.7, 1, "What do you need?"),
                                        (12.1, 7, "Can Update stuck reports for Operations come to us too? Two have waited on you since Wednesday.")], {}),
    (16, 31, 8, "superior", 10.4, None, [(10.5, 8, "Go ahead, Afi."),
                                         (10.6, 31, "Someone on my team keeps taking my files off the shared drive and renaming them.")], {8: [7]}),
    (15, 23, 7, "sender", -20.5, -19.4, [(-20.4, 7, "What is it, Yaw?"), (-20.1, 23, "The printer on the second floor will not take my jobs."),
                                         (-19.5, 7, "Fixed: it was paused. Try again.")], {}),
]


def _visible(c: tuple, account: int) -> bool:
    return account in (c[1], c[2]) or any(account in xs for xs in c[7].values())


def channels(account: int) -> dict[str, Any]:
    return {"channels": [{"id": c[0], "initiator_account_id": c[1], "superior_account_id": c[2], "turn": c[3],
                          "initiator_name": ACCOUNTS.get(c[1]), "opened_at": today(c[4]),
                          "closed_at": today(c[5]) if c[5] is not None else None}
                         for c in CHANNELS if _visible(c, account)]}


def channel(cid: int, account: int) -> dict[str, Any] | None:
    c = next((x for x in CHANNELS if x[0] == cid), None)
    if c is None:
        return None
    turn_of = c[1] if c[3] == "sender" else c[2]
    return {"channel": {"id": c[0], "initiator_account_id": c[1], "superior_account_id": c[2], "subordinate_account_id": c[1],
                        "turn": c[3], "opened_at": today(c[4]), "closed_at": today(c[5]) if c[5] is not None else None,
                        "names": {str(c[1]): ACCOUNTS.get(c[1]), str(c[2]): ACCOUNTS.get(c[2])},
                        "my_turn": c[5] is None and account == turn_of},
            "messages": [{"id": k, "sender_account_id": who, "body": text, "sent_at": today(t)} for k, (t, who, text) in enumerate(c[6])]}


# --- automation ------------------------------------------------------------------------------------------
LIB = {1: ("Take a screenshot", "monitoring", "screenshot", 30), 2: ("Snapshot USB contents", "monitoring", "usb_contents", 60),
       3: ("Log event", "monitoring", "log_event", 10), 4: ("Notify the Admin", "control", "notify", 10),
       5: ("Clear the temp folder", "custom", None, 90), 6: ("Check disk health", "monitoring", "disk_health", 60),
       7: ("Lock the screen", "control", "lock_session", 30)}
OPS = [1, 2, 3, 4, 5, 6, 7]
# id, type, pc_ids, match, actions, enabled, org-wide, firings [(hours ago, pc, [(action, outcome, secs)])]
EVENTS = [
    (1, "usb.inserted", OPS, {}, [1, 2, 3], True, False,
     [(0.3, 4, [(1, "success", 3), (2, "success", 38), (3, "success", 1)]), (1.9, 1, [(1, "success", 3), (2, "success", 41), (3, "success", 1)]),
      (3.3, 7, [(1, "success", 3), (2, "success", 35), (3, "success", 1)]), (26, 3, [(1, "success", 3), (2, "failed", 60), (3, "success", 1)]),
      (75, 5, [(1, "success", 3), (2, "success", 30), (3, "success", 1)])]),
    (2, "resource.violation", None, {"tier": "restricted"}, [4, 1], True, True,
     [(3.3, 7, [(4, "success", 1), (1, "success", 3)]), (3.8, 3, [(4, "success", 1), (1, "success", 3)])]),
    (3, "threshold.cpu", OPS, {"percent": 90, "duration_s": 300}, [4], True, False,
     [(0.6, 3, [(4, "success", 1)]), (26, 1, [(4, "success", 1)]), (146, 5, [(4, "success", 1)])]),
    (4, "time.recurring", None, {"at": "09:00", "days": [0, 1, 2, 3, 4]}, [5, 6], True, True,
     [(4.3 + 24 * d, 0, [(5, "success" if (d + k) % 9 else "failed", 30 + k) for k in range(5)] + [(6, "success", 10)]) for d in range(6)]),
]


def events(role: str) -> dict[str, Any]:
    out = []
    for eid, typ, pcs, match, acts, on, org, _f in EVENTS:
        out.append({"id": eid, "enabled": on, "org_wide": org, "read_only": role == "admin" and org,
                    "condition_spec": {"type": typ, "pc_ids": pcs, "match": match}, "last_fired_at": None,
                    "actions": [{"id": a, "name": LIB[a][0], "action_kind": LIB[a][1], "builtin_type": LIB[a][2], "timeout_seconds": LIB[a][3]} for a in acts]})
    return {"events": out, "types": {}}


def event_history(eid: int) -> dict[str, Any]:
    e = next((x for x in EVENTS if x[0] == eid), None)
    if e is None:
        return {"firings": []}
    firings, k = [], 0
    for h, pc, runs in e[7]:
        host = next((m[1] for m in MACHINES if m[0] == pc), None)
        rr = []
        for a, outcome, secs in runs:
            k += 1
            rr.append({"id": eid * 1000 + k, "action_id": a, "target_pc_id": pc or 1, "status": outcome, "started_at": at(-h),
                       "finished_at": at(-h + secs / 3600), "summary": "exit code 1" if outcome == "failed" else None})
        firings.append({"at": at(-h), "pc_id": pc, "hostname": host, "subject": None, "runs": rr, "machines": 1 if pc else 7})
    return {"event_id": eid, "firings": firings, "fired_today": 0, "running": []}


TEMP_PY = """import os
import time
from pathlib import Path

LIMIT_DAYS = 7
temp = Path(os.environ["TEMP"])
cutoff = time.time() - LIMIT_DAYS * 86400
removed = 0
for f in temp.rglob("*"):
    try:
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    except OSError:
        pass  # in use; try again next time
print(f"removed {removed} files")"""


# --- reports ----------------------------------------------------------------------------------------------
# id, category, summary, hours ago, addressed (hours after, by), department it came from
REPORTS = [
    (3001, "resource_violation", "Copy of restricted budget-2026.xlsx on OPS-07", 3.3, None, 1),
    (3002, "resource_violation", "Copy of restricted salaries.csv on OPS-03", 3.8, (0.7, "R. Mensah"), 1),
    (3003, "deviation", "OPS-05 presented WS-OPS-05, expected OPS-05", 4.1, None, 1),
    (3004, "update_status", "LOG-02 update past the escalation limit", 76, None, 3),
    (3005, "update_status", "OPS-06 one version behind, 2 failed attempts", 26, (2.2, "A. Quaye"), 1),
    (3006, "flow_failure", "weekly: the branch to LOG-01 /archive/ paused", 30, (0.5, "R. Mensah"), 1),
    (3007, "listener_report", "Afi: files on the shared drive renamed by a colleague", 2.6, None, 2),
    (3008, "about_admin", "A. Quaye entered LOG-02 outside working hours, 17 min", 11, None, 1),
    (3009, "about_admin", "A. Quaye entered LOG-01 outside working hours, 18 min", 141, None, 1),
]
ROUTING = {"resource_violation": [1, 2, 3], "flow_failure": [1, 2], "listener_report": [1], "update_status": [1, 2, 3], "deviation": [1, 2, 3]}


def reports(role: str, dept_id: int | None) -> dict[str, Any]:
    out = []
    for rid, cat, summary, h, addr, dept in REPORTS:
        if role == "admin" and (cat == "about_admin" or dept != dept_id or dept_id not in ROUTING.get(cat, [])):
            continue
        out.append({"id": rid, "category": cat, "summary": summary, "generated_at": at(-h), "seen_at": None,
                    "addressed_at": at(-h + addr[0]) if addr else None})
    return {"reports": out}


REPORT_HOST = {3001: "OPS-07", 3002: "OPS-03", 3003: "OPS-05", 3004: "LOG-02", 3005: "OPS-06", 3006: "OPS-07", 3007: "FIN-01", 3008: "LOG-02", 3009: "LOG-01"}
REPORT_LABEL = {"resource_violation": "Restricted file", "deviation": "Deviation", "update_status": "Update stuck", "flow_failure": "Flow failed",
                "listener_report": "Listener report", "about_admin": "About an Admin"}


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


def answer(type_: str, payload: dict[str, Any], role: str, account: int, dept_id: int | None) -> Any:
    """The sample's answer to one call, or None when the sample does not cover it."""
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
    if type_ == "task.dept_list":
        return dept_tasks(role, account)
    if type_ == "assistance.channels":
        return channels(account)
    if type_ == "assistance.channel":
        return channel(int(payload.get("channel_id") or 0), account)
    if type_ == "assistance.my_listeners":
        c = next((x for x in CHANNELS if x[0] == int(payload.get("channel_id") or 0)), None)
        return {"listeners": [{"listener_account_id": a, "name": ACCOUNTS[a]} for a in (c[7].get(account, []) if c else [])]}
    if type_ == "assistance.listener_candidates":
        c = next((x for x in CHANNELS if x[0] == int(payload.get("channel_id") or 0)), None)
        added = c[7].get(account, []) if c else []
        return {"candidates": [{"account_id": a, "name": n, "department_id": d, "department_name": dict(DEPTS)[d]}
                               for a, n, d, *_ in ADMINS if c and a not in (c[1], c[2]) and a not in added]}
    if type_ == "assistance.my_admins":
        return {"admins": [{"account_id": 1, "name": "Super User", "role": "super_user"}] if role == "admin" else []}
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
        acts = {"control": [], "monitoring": [], "custom": []}
        for aid, (name, kind, builtin, limit) in LIB.items():
            a = {"id": aid, "name": name, "action_kind": kind, "builtin_type": builtin, "timeout_seconds": limit,
                 "description": {"Take a screenshot": "Saves what is on screen to the record.", "Snapshot USB contents": "Lists every file on an inserted device, with its hash.",
                                 "Log event": "Writes one line to the audit log.", "Notify the Admin": "Tells an Admin, or you, inside the console.",
                                 "Check disk health": "Reads SMART status and free space.", "Lock the screen": "Locks the session. The user signs back in as usual.",
                                 "Clear the temp folder": "Deletes files older than 7 days in %TEMP%."}.get(name, "")}
            if kind == "custom":
                a.update({"custom_script_language": "python", "created_by_name": "R. Mensah",
                          "custom_script": TEMP_PY})
            acts[kind].append(a)
        return {"builtin": {}, "actions": acts}
    if type_ == "control.event_list":
        return events(role)
    if type_ == "control.event_history":
        return event_history(int(payload.get("event_id") or 0))
    if type_ == "control.execution":
        return {"execution": {"id": payload.get("execution_id"), "status": "success", "has_image": False, "summary": None},
                "output": ["Recorded on the machine.", "exit code 0"], "result": None, "expired": False}
    if type_ == "hierarchy.pc_state":
        pc = int(payload.get("pc_id") or 0)
        m = next((x for x in MACHINES if x[0] == pc), None)
        if not m:
            return None
        cpu = {"OPS-03": 94.0, "OPS-07": 71.0, "OPS-05": 63.0}.get(m[1], 8 + (pc * 7) % 25)
        return {"pc_id": pc, "hostname": m[1], "online": m[5], "last_seen_at": at(-m[6]),
                "levels": {"cpu": cpu, "memory": 52.0, "idle_s": 3.0, "at": at(0)} if m[5] else None}
    return None
