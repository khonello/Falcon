"""A machine's health, in the console's one vocabulary (Machines, Overview's fleet map, Registry).

    healthy   nothing open on it
    warning   something to look at, not urgent (a low or medium issue)
    high      a high issue is open
    critical  a critical issue is open
    offline   it is not connected

Health is **the most serious thing open on the machine**, so it is read from the open issues (`issues`, ENGINE-CONCEPT-NEEDS
WP2). A machine that is not connected is offline whatever else is open on it; the issue still shows in its note.
"""

from __future__ import annotations

from typing import Any

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
HEALTH_OF_SEVERITY = {"critical": "critical", "high": "high", "medium": "warning", "low": "warning"}


async def open_signals(db: Any, pc_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """The open things on each machine, most serious first: [{severity, title, issue_id?}]."""
    out: dict[int, list[dict[str, Any]]] = {pc: [] for pc in pc_ids}
    if not pc_ids:
        return out
    issues = getattr(db, "issues", None)           # the ticket store arrives with the Issues work package
    if issues is None:
        return out
    for r in await issues.open_for_pcs(pc_ids):
        out[r["pc_id"]].append({"severity": r["severity"], "title": r["title"], "issue_id": r["id"], "subject": r["subject"]})
    for sigs in out.values():
        sigs.sort(key=lambda s: SEVERITY_RANK.get(s["severity"], 9))
    return out


def health_of(online: bool, signals: list[dict[str, Any]]) -> tuple[str, str]:
    """(health, note) for one machine."""
    top = signals[0] if signals else None
    note = top["title"] + (f": {top['subject']}" if top.get("subject") else "") if top else ""
    if not online:
        return "offline", ("Not checking in" + (f" · {note}" if note else ""))
    if top is None:
        return "healthy", ""
    return HEALTH_OF_SEVERITY.get(top["severity"], "warning"), note
