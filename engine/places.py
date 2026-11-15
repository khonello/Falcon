"""Each machine's places, as its Worker read them from Windows: whose Desktop, Documents, Downloads is where (common/places.py).

    index.places      {places: [{kind, path, user, guessed?}]}    a machine telling its own (at every connect, and when they change)
    index.places_get  {pc_id}                                      an Admin looking: {pc_id, hostname, as_of, places}

Held in memory: a Worker tells them again at every connect, so a restarted Engine has them back as each machine returns. Until a machine has said,
`place_of` answers from the usual layout (`guessed`). Every file event Detective reads is given its place through `place_of`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from common.places import Place, Places, clean, guess
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_department_scope, require_role
from protocol import ErrorCode, ProtocolError

_machines: dict[int, tuple[datetime, Places]] = {}


def reset_state() -> None:
    _machines.clear()


def place_of(pc_id: int | None, path: str) -> Place | None:
    known = _machines.get(pc_id) if pc_id is not None else None
    return known[1].of(path) if known is not None else guess(path)


def told(pc_id: int) -> bool:
    return pc_id in _machines


@handler("index.places")
async def index_places(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    pc_id = ctx.identity.pc_id
    if pc_id is None:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only a machine tells its own places")
    places = clean(payload.get("places"))
    before = _machines.get(pc_id)
    _machines[pc_id] = (datetime.now(timezone.utc), Places(places))
    if before is None or before[1].entries() != _machines[pc_id][1].entries():
        await ctx.engine.audit.record(ctx, "index.places", target_type="pcs", target_id=pc_id, pc_id=pc_id,
                                      detail={"places": len(places), "people": len({p["user"] for p in places if p["user"]}),
                                              "guessed": sum(1 for p in places if p["guessed"])})
    return {"accepted": len(places)}


@handler("index.places_get")
async def index_places_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    pc_id = int_field(payload, "pc_id")
    pc = await ctx.engine.db.accounts.pc(pc_id)
    if pc is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such pc")
    require_department_scope(ident, pc["department_id"])
    known = _machines.get(pc_id)
    return {"pc_id": pc_id, "hostname": pc["hostname"], "as_of": known[0].isoformat() if known else None,
            "places": known[1].entries() if known else []}
