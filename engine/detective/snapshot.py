"""The machine's picture, compared with the last one (proposals item 3; worker_client/machine_snapshot.py takes it). Detective's alone: no page shows it.

    detective.snapshot   {at, snapshot}     a machine sending its picture (two minutes after connecting, then every six hours)

What changed between the two becomes a Detective signal (Sig verb "system"), weighed by `common.detective.SYSTEM_CHANGES`. Each is light alone: what it
adds to is the rest of the case on that machine. Only sections both pictures have are compared, so a part that could not be read is never taken for
"everything was removed". The first picture of a machine is the baseline: nothing is read from it. If Falcon's own actions ran on the machine since
the last picture, what changed may be theirs, and weighs half.

Storage is read through the places, so the same drop means different things: a person's own places holding far less is "Documents shrank"; space
freed in Temp, the Recycle Bin or Windows Update's downloads is a clean-up and says nothing. Only places measured whole in both pictures are compared.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from common.detective import Sig
from common.places import WORDS
from engine.dispatch import Context, handler
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

GIB = 1024 ** 3
SECTIONS = ("drives", "places", "admins", "accounts", "startup", "services", "tasks", "programs", "shares", "defender", "logs")
MAX_BYTES = 512 * 1024                       # a picture is a few tens of KB; past this it is not one
MAX_CHANGES = 40                             # what one picture may raise (a machine re-imaged overnight would otherwise flood Detective)
OWN_KINDS = ("desktop", "documents", "downloads", "pictures", "videos", "music", "onedrive")
SHRANK = (GIB, 0.25)                         # a person's place holding this much less (bytes), and this share less, is "shrank"
FILLED = (5 * GIB, 0.5)
WIPERS = ("eraser", "sdelete", "ccleaner", "bleachbit", "privazer", "file shredder", "hardwipe", "secure delete", "blancco", "wipefile")
ENCRYPTORS = ("veracrypt", "truecrypt", "axcrypt", "gpg4win", "kleopatra", "cryptomator", "boxcryptor", "diskcryptor", "folder lock")


def _gb(n: float) -> str:
    return f"{n / GIB:.1f} GB"


def _new(prev: list[Any], now: list[Any]) -> list[str]:
    before = {str(x) for x in prev}
    return [str(x) for x in now if str(x) not in before]


def _program(entry: str) -> str:
    return entry.rsplit(" ", 1)[0] if entry.rsplit(" ", 1)[-1][:1].isdigit() else entry


def changes(prev: dict[str, Any], now: dict[str, Any]) -> list[dict[str, Any]]:
    """What changed from one picture to the next, as {change, words, scale?}. Pure: the tests call it directly."""
    out: list[dict[str, Any]] = []
    both = [s for s in SECTIONS if isinstance(prev.get(s), (list, dict)) and isinstance(now.get(s), (list, dict))]

    def add(change: str, words: str, **more: Any) -> None:
        out.append({"change": change, "words": words, **more})

    if "admins" in both:
        for who in _new(prev["admins"], now["admins"]):
            add("admin_added", f"{who} was made an administrator of the machine")
    if "accounts" in both:
        for who in _new(prev["accounts"], now["accounts"]):
            add("account_added", f"a new local account was made: {who}")
    if "startup" in both:
        for entry in _new(prev["startup"], now["startup"]):
            add("starts_by_itself", f"something new starts by itself at sign-in ({entry[:160]})")
    if "services" in both:
        for entry in _new(prev["services"], now["services"]):
            add("service_added", f"a new service starts by itself ({entry[:160]})")
    if "tasks" in both:
        for entry in _new(prev["tasks"], now["tasks"]):
            add("task_added", f"a new scheduled task: {entry[:160]}")
    if "programs" in both:
        for entry in _new(prev["programs"], now["programs"]):
            low = entry.lower()
            if any(w in low for w in WIPERS):
                add("wiper_installed", f"{_program(entry)} was installed: it destroys files beyond recovery")
            elif any(w in low for w in ENCRYPTORS):
                add("encryptor_installed", f"{_program(entry)} was installed: it locks files away")
    if "shares" in both:
        for entry in _new(prev["shares"], now["shares"]):
            name, _, path = entry.partition(" = ")
            if not name.endswith("$"):                    # C$, ADMIN$, IPC$ are Windows' own
                add("share_added", f"a folder was shared on the network: {path or name}")
    if "defender" in both:
        p, n = prev["defender"], now["defender"]
        if n.get("realtime_off") and not p.get("realtime_off"):
            add("protection_off", "Defender's real-time protection was turned off")
        for key, value in n.items():
            if key.startswith("firewall_off_") and value and p.get(key) is False:
                add("firewall_off", f"the firewall was turned off for the {key[len('firewall_off_'):]} profile")
    if "logs" in both:
        for name, size in now["logs"].items():
            was = prev["logs"].get(name)
            if isinstance(was, int) and isinstance(size, int) and was > 1024 * 1024 and size < was * 0.5:
                add("log_shrank", f"the {name} event log is much smaller than it was ({was // 1024} KB to {size // 1024} KB): it was emptied")
    if "places" in both:
        out += _places(prev["places"], now["places"])
    return out[:MAX_CHANGES]


def _places(prev: list[dict[str, Any]], now: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A person's own places, measured whole in both pictures, that hold far less (or far more) than before."""
    def key(p: dict[str, Any]) -> tuple[str, str, str]:
        return (str(p.get("kind")), str(p.get("user")), str(p.get("path", "")).lower())

    before = {key(p): p for p in prev if not p.get("partial")}
    out: list[dict[str, Any]] = []
    for p in now:
        was = before.get(key(p))
        if was is None or p.get("partial") or p.get("kind") not in OWN_KINDS:
            continue                                      # (Temp, the Recycle Bin and Windows Update emptying is a clean-up: nothing to read)
        b0, b1 = int(was.get("bytes") or 0), int(p.get("bytes") or 0)
        where = f"{p['user']}'s {WORDS.get(p['kind'], p['kind'])}" if p.get("user") else WORDS.get(p["kind"], p["kind"])
        if b0 - b1 >= SHRANK[0] and b1 <= b0 * (1 - SHRANK[1]):
            gone = b0 - b1
            out.append({"change": "documents_shrank", "words": f"{where} holds {_gb(gone)} less than it did ({_gb(b0)} to {_gb(b1)}; "
                        f"{int(was.get('files') or 0) - int(p.get('files') or 0)} fewer files)",
                        "scale": 1.5 if gone >= 10 * GIB or b1 <= b0 * 0.25 else 1.0})
        elif b1 - b0 >= FILLED[0] and b1 >= b0 * (1 + FILLED[1]):
            out.append({"change": "filled_up", "words": f"{where} holds {_gb(b1 - b0)} more than it did ({_gb(b0)} to {_gb(b1)})"})
    return out


def _clean(snapshot: Any) -> dict[str, Any]:
    return {k: v for k, v in (snapshot or {}).items() if k in SECTIONS} if isinstance(snapshot, dict) else {}


async def take_in(engine: Engine, pc_id: int, taken_at: datetime, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare with the last picture, feed what changed to Detective, keep this one. Returns what changed."""
    from engine import detective

    db = engine.db.detective
    last = await db.snapshot(pc_id)
    found: list[dict[str, Any]] = []
    if last is not None and taken_at > last["taken_at"]:
        found = changes(last["data"] or {}, snapshot)
        if found:
            ran = await db.falcon_ran(pc_id, last["taken_at"])
            for c in found:
                info = {"change": c["change"], "words": c["words"], "scale": c.get("scale", 1.0), "since": last["taken_at"].isoformat()}
                if ran:
                    info["falcon_ran"] = ran
                await detective.feed_signal(engine, Sig(taken_at.timestamp(), pc_id, "system", thing=f"system:{c['change']}:{c['words'][:80]}",
                                                        by="unknown", info=info))
    if last is None or taken_at > last["taken_at"]:
        await db.put_snapshot(pc_id, taken_at, snapshot)
    return found


@handler("detective.snapshot")
async def detective_snapshot(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    pc_id = ctx.identity.pc_id
    if pc_id is None:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only a machine sends its own picture")
    if not ctx.engine.db.connected:
        return {"accepted": False}
    snapshot = _clean(payload.get("snapshot"))
    import json

    if not snapshot or len(json.dumps(snapshot)) > MAX_BYTES:
        raise ProtocolError(ErrorCode.INVALID, "not a machine picture")
    try:
        at = float(payload.get("at") or time.time())
    except (TypeError, ValueError):
        at = time.time()
    taken_at = datetime.fromtimestamp(min(at, time.time()), timezone.utc)       # a machine's clock running ahead never puts a picture in the future
    found = await take_in(ctx.engine, pc_id, taken_at, snapshot)
    return {"accepted": True, "changes": len(found)}
