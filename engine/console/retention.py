"""Old machine days: asked about, never deleted by themselves (the user, 3 Nov 2026).

`pc_days` keeps one row per machine per day: whether it checked in, and the quarter hours someone was at its keyboard (the Machines page
uses the last week). On the audit trail's 90-day clock, the days older than that are not purged in silence: an issue asks the Admins, and
any Admin decides on the Issues page:

    Delete them   the machine days older than the window are deleted (audited, with how many), the issue closes
    Keep them     nothing is deleted, the issue closes, and the question comes back ASK_AGAIN_DAYS later ("the cycle continues")

One open issue at a time (source `pc_days`/0); while it is open its counts follow the table, and Delete always uses the window as it is on
the day it is pressed. The check runs daily with the retention job.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.server import Engine

SOURCE = ("pc_days", 0)
ASK_AGAIN_DAYS = 30


def cutoff(engine: Engine, today: date | None = None) -> date:
    return (today or datetime.now().astimezone().date()) - timedelta(days=engine.audit.retention_days)


async def ask_about_machine_days(engine: Engine, *, now: datetime | None = None) -> int | None:
    """Raise (or bring up to date) the issue when machine days have passed the window. Returns the issue id, or None when nothing is due."""
    if not engine.db.connected:
        return None
    now = now or datetime.now(timezone.utc)
    before = cutoff(engine, now.astimezone().date())
    old = await engine.db.accounts.days_before(before)
    if not old["rows"]:
        return None
    detail = {"kind": "pc_days", "rows": old["rows"], "machines": old["machines"], "oldest": old["oldest"].isoformat() if old["oldest"] else None,
              "before": before.isoformat(), "window_days": engine.audit.retention_days}
    title = "Old machine records are due to be deleted"
    subject = f"{old['rows']} days of records on {old['machines']} machine{'s' if old['machines'] != 1 else ''}"
    open_ = await engine.db.issues.by_source(*SOURCE)
    if open_ is not None:
        await engine.db.issues.set_detail(open_["id"], detail)
        await engine.db.issues.set_severity(open_["id"], "low", title=title, subject=subject)
        return int(open_["id"])
    last = await engine.db.issues.last_resolved(*SOURCE)
    if last is not None and last["resolution"] == "Kept them" and now - last["resolved_at"] < timedelta(days=ASK_AGAIN_DAYS):
        return None                                                 # kept lately: asked again when the cycle comes round
    from engine.console import issues

    issue_id, _ = await issues.raise_issue(engine, type_="retention", severity="low", title=title, subject=subject,
                                           source_table=SOURCE[0], source_id=SOURCE[1], detail=detail)
    return issue_id


def view(issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[dict[str, Any]], list[str]]:
    """What the issue says, and its two buttons (engine/console/plays.py draws them)."""
    from engine.console.plays import _opt

    d = issue["detail"] or {}
    lead = (f"The Engine keeps a record of each machine's day: whether it checked in, and when someone was at its keyboard. "
            f"{d.get('rows', 0)} of those days are older than {d.get('window_days', 90)} days. Nothing is deleted until you choose.")
    facts = [["Records", f"{d.get('rows', 0)} days"], ["Machines", d.get("machines", 0)], ["Oldest", d.get("oldest")], ["Older than", d.get("before")]]
    return lead, facts, [
        _opt("delete_old", "Delete them", f"The machine days older than {d.get('window_days', 90)} days are deleted for good. The last week, which the "
             "Machines page shows, is never touched.", "Delete them", "Resolved"),
        _opt("keep_old", "Keep them", f"Nothing is deleted. You are asked again in {ASK_AGAIN_DAYS} days.", "Keep them", "Resolved")], []


async def act(ctx: Any, issue: dict[str, Any], key: str) -> dict[str, Any]:
    from engine.console.plays import _finish

    engine, who = ctx.engine, (ctx.viewed_by or ctx.identity).account_id
    if key == "keep_old":
        await engine.db.issues.log(issue["id"], "acted", "Kept the old machine records", who)
        await engine.audit.record(ctx, "retention.kept", target_type="issues", target_id=issue["id"], detail={"table": "pc_days", "rows": issue["detail"].get("rows")})
        return await _finish(ctx, issue, "Kept them")
    before = cutoff(engine)
    n = await engine.db.accounts.delete_days_before(before)
    await engine.audit.record(ctx, "retention.deleted", target_type="issues", target_id=issue["id"], detail={"table": "pc_days", "rows": n, "before": before.isoformat()})
    await engine.db.issues.log(issue["id"], "acted", f"Deleted {n} old machine day{'s' if n != 1 else ''}", who)
    return await _finish(ctx, issue, "Deleted them")
