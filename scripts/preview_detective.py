"""Detective's sample for `preview.py`: real cases, played through the real matcher.

The scripted scenarios (`detective_scenarios.py`) are run through `common.detective.Detective`, and each case is shaped the way the Engine's handlers shape it
(`engine/detective/__init__.py`: the case row, its findings, the graph, the board, the rule options). So the page is looked at with exactly what it would be given.
Only the machine names, the dates (moved to the last hours) and a few reviewed cases, written rules and suggestions are made up here.
"""
from __future__ import annotations

import dataclasses
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from detective_scenarios import SCENARIOS, play

from common.detective import Case, Finding, graph_of, rule_options, sig_to_dict

# scenario -> (host, pc, department, hours ago it ended, how it was left: open | reviewed outcome)
PLAN = [
    ("leak", "FIN-02", 12, 2, 1.2, "open"),
    ("ransom", "OPS-03", 3, 1, 0.6, "open"),
    ("goes_dark", "OPS-06", 6, 1, 3.4, "open"),
    ("snooping", "OPS-05", 5, 1, 5.0, "escalated"),
    ("printscreens", "FIN-01", 11, 2, 7.5, "open"),
    ("weekly_collector", "LOG-01", 21, 3, 20.0, "open"),
    ("sole_copy_deleted", "OPS-01", 1, 1, 26.0, "open"),
    ("log_cleared", "OPS-07", 7, 1, 30.0, "open"),
    ("flow_to_drive", "OPS-02", 2, 1, 50.0, "dismissed"),
    ("backups_then_files", "LOG-02", 22, 3, 80.0, "explained"),
]


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _shift(case: Case, ago_hours: float, now: float | None = None) -> list[Finding]:
    """The scenario's own clock is last week: move every moment so the case ends `ago_hours` before now (or before `now`, for a sample set at another clock)."""
    delta = ((now if now is not None else time.time()) - ago_hours * 3600) - case.last_at
    out = []
    for f in case.findings:
        out.append(dataclasses.replace(f, at=f.at + delta, evidence=[dataclasses.replace(e, at=e.at + delta) for e in f.evidence]))
    return out


def build(now: float | None = None) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    detail: dict[int, dict[str, Any]] = {}
    reviewers = {"dismissed": "R. Mensah", "explained": "K. Boateng", "escalated": "R. Mensah"}
    notes = {"dismissed": "The flow is Finance's weekly pack; it goes to the shared drive on purpose.", "explained": "Month-end clean-up that Logistics does every quarter."}
    for n, (name, host, pc, dept, ago, left) in enumerate(PLAN, start=1):
        det, _ = play(SCENARIOS[name]())
        found = sorted(det.cases, key=lambda c: c.weight, reverse=True)
        if not found:
            continue
        case = found[0]
        shifted = _shift(case, ago, now)
        held = Case(pc=pc, findings=shifted)
        first = min(f.at for f in shifted)
        last = max(f.at for f in shifted)
        stage, latest, nxt = held.stage
        view = {"id": n, "pc_id": pc, "department_id": dept, "host": host, "intent": held.intent, "level": held.level, "weight": round(held.weight, 3), "stage_count": stage,
                "stage_name": latest, "next_stage": nxt, "not_yet": held.not_yet(), "behaviours": sorted(held.behaviours), "headline": held.headline(), "story": held.story(),
                "first_at": _iso(first), "last_at": _iso(last), "status": "open" if left == "open" else left, "note": notes.get(left), "model_says": None,
                "reviewed_by": reviewers.get(left), "ago": ago, "dept": {1: "ops", 2: "fin", 3: "log"}[dept]}
        if held.level == "quiet":
            continue
        cases.append(view)
        sigs = []
        seen = set()
        for f in shifted:
            for e in f.evidence:
                if e not in seen:
                    seen.add(e)
                    sigs.append(e)
        detail[n] = {"case": view,
                     "findings": [{"behaviour": f.behaviour, "graph": f.graph, "weight": round(f.weight, 3), "at": _iso(f.at), "summary": f.summary, "innocent": f.innocent,
                                   "why": list(dict.fromkeys(f.why)), "things": sorted(f.things)[:50], "evidence": [sig_to_dict(e) for e in f.evidence[-80:]]}
                                  for f in shifted if not f.graph.startswith("coverage_")],
                     "graph": graph_of(sigs), "rule_options": rule_options(shifted), "board": held.board()}
    # the one that reads as "model says" shows what the local model's second opinion looks like
    for c in cases:
        if c["host"] == "FIN-02":
            c["model_says"] = "Taking files out"
            detail[c["id"]]["case"]["model_says"] = "Taking files out"
    return {"cases": cases, "detail": detail}


_BUILT: dict[str, Any] | None = None


def built() -> dict[str, Any]:
    global _BUILT
    if _BUILT is None:
        _BUILT = build()
    return _BUILT


RULES = [
    {"id": 1, "pc_id": 2, "host": "OPS-02", "graph": "drive_after_staging", "kind": "drive", "value": "E: (Finance weekly backup)", "made_at": "2026-10-12T09:00:00+00:00"},
    {"id": 2, "pc_id": 22, "host": "LOG-02", "graph": "mass_removal", "kind": "program", "value": "cleanmgr.exe", "made_at": "2026-10-09T15:20:00+00:00"},
    {"id": 3, "pc_id": 11, "host": "FIN-01", "graph": "many_zipped", "kind": "folder", "value": "C:\\Finance\\Archive", "made_at": "2026-10-05T11:02:00+00:00"},
]


def proposals() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"id": 1, "kind": "pause_flow", "title": "Pause flow #3 (Finance weekly pack)? Its source machine FIN-02 has an urgent case open.", "pc_id": 12, "department_id": 2, "created_at": now, "state": "open"},
        {"id": 2, "kind": "mark_folder", "title": "Mark C:\\Finance\\Payroll on FIN-02 as restricted? Files from there were gathered and sent out.", "pc_id": 12, "department_id": 2, "created_at": now, "state": "open"},
        {"id": 3, "kind": "follow_up_task", "title": "Ask the Operations Admin to follow up on OPS-03 (files renamed to one odd ending)?", "pc_id": 3, "department_id": 1, "created_at": now, "state": "open"},
    ]


def overview(role: str, dept: int | None) -> dict[str, Any]:
    cs = [c for c in built()["cases"] if role == "super_user" or c["department_id"] == dept]
    op = [c for c in cs if c["status"] == "open"]
    by_level = {lv: sum(1 for c in op if c["level"] == lv) for lv in ("noted", "case", "urgent")}
    by_intent: dict[str, int] = {}
    for c in op:
        if c["level"] in ("case", "urgent"):
            by_intent[c["intent"]] = by_intent.get(c["intent"], 0) + 1
    return {"by_level": by_level, "by_intent": by_intent, "reviewed": sum(1 for c in cs if c["status"] != "open")}


def answer(type_: str, payload: dict[str, Any], role: str, dept: int | None) -> Any:
    b = built()
    if type_ == "detective.overview":
        return overview(role, dept)
    if type_ == "detective.cases":
        status = payload.get("status")
        rows = [c for c in b["cases"] if role == "super_user" or c["department_id"] == dept]
        if status == "reviewed":
            rows = [c for c in rows if c["status"] != "open"]
        elif status == "escalated":
            rows = [c for c in rows if c["status"] == "escalated"]
        else:
            levels = ("noted", "case", "urgent") if payload.get("include_noted") else ("case", "urgent")
            rows = [c for c in rows if c["status"] == "open" and c["level"] in levels]
        return {"cases": sorted(rows, key=lambda c: ({"urgent": 0, "case": 1, "noted": 2}[c["level"]], -c["weight"]))}
    if type_ == "detective.case":
        return b["detail"].get(int(payload.get("case_id") or 0))
    if type_ == "detective.rules":
        return {"rules": RULES if role == "super_user" else [r for r in RULES if r["pc_id"] in (1, 2, 3, 4, 5, 6, 7)]}
    if type_ in ("detective.review", "detective.rule_revoke"):
        return {"status": "ok", "rules": []}
    if type_ == "proposals.list":
        return {"proposals": [p for p in proposals() if role == "super_user" or p["department_id"] == dept]}
    if type_ == "proposals.decide":
        return {"paused": True} if payload.get("accept") else {"dismissed": True}
    return None
