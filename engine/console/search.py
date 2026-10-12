"""Search (Ctrl K): one box that finds a machine, a person, a task, a flow, an issue, a rule or a department.

    search.find {q, kinds?: [...], limit?: 8}  -> {"results": [{kind, id, title, sub, department_id?, page}], "q"}

Each kind is limited to what the caller may see: the Super User everything, an Admin their own department. People are found by the name the caller gives them
(Display Names are never searched across other people's naming), machines by hostname, tasks by their text, flows by their source path, issues by code,
title or machine, rules by name, departments by name. `page` says where the console opens the result.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role
from protocol import ErrorCode, ProtocolError

KINDS = ("machine", "person", "task", "flow", "issue", "rule", "department")


@handler("search.find")
async def find(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    q = " ".join(str(payload.get("q") or "").split())[:80]
    if len(q) < 2:
        return {"results": [], "q": q}
    kinds = payload.get("kinds") or list(KINDS)
    if not isinstance(kinds, list) or not set(kinds) <= set(KINDS):
        raise ProtocolError(ErrorCode.INVALID, f"kinds must be some of {', '.join(KINDS)}")
    limit = max(1, min(int_field(payload, "limit", required=False) or 8, 25))
    db = ctx.engine.db
    dept = ident.department_id if ident.role == "admin" else None
    out = await db.search.find(q, [k for k in kinds if k != "person"], dept, limit)
    people: list[dict[str, Any]] = []
    if "person" in kinds:
        accounts = await db.search.accounts(dept)
        names = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in accounts]) if accounts else {}
        for acct in accounts:
            name = names.get(acct["id"]) or ""
            if q.lower() in name.lower() and len(people) < limit:
                people.append({"kind": "person", "id": acct["id"], "title": name, "sub": f"{acct['role'].replace('_', ' ')} · {acct['department_name'] or 'Head office'}",
                               "department_id": acct["department_id"], "page": "registry"})
    order = {k: i for i, k in enumerate(KINDS)}
    return {"q": q, "results": sorted(out + people, key=lambda r: order[r["kind"]])}
