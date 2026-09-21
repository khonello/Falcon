"""Message envelope and framing.

Framing: newline-delimited JSON (one UTF-8 JSON object per line) over TCP+TLS
(implementation-spec.md §2.2, §8.3).

Every message carries the auth fields from day one (spec §8.1) — the Engine's check on them is
stubbed during development and filled in last. The shape never changes; only the check does.

    {"kind": "request",  "id": "...", "type": "hierarchy.traverse", "auth": {...}, "payload": {...}}
    {"kind": "response", "id": "...", "ok": true,  "result": {...}}
    {"kind": "response", "id": "...", "ok": false, "error": {"code": "...", "message": "..."}}
    {"kind": "push",                  "type": "session.ended",     "payload": {...}}

`type` is dotted `<area>.<operation>`; areas mirror the Engine's package layout
(auth, hierarchy, task, flow, resource, assistance, control, index, updates, system).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Kind(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    PUSH = "push"


class ErrorCode(str, Enum):
    BAD_MESSAGE = "bad_message"
    UNKNOWN_TYPE = "unknown_type"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"          # e.g. session occupied, index collision, flow cycle
    INVALID = "invalid"            # payload failed validation
    TIMEOUT = "timeout"            # distinct from INTERNAL per spec §7.3
    INTERNAL = "internal"
    NOT_IMPLEMENTED = "not_implemented"


class ProtocolError(Exception):
    def __init__(self, code: ErrorCode, message: str = "") -> None:
        super().__init__(message or code.value)
        self.code = code
        self.message = message or code.value


@dataclass
class Envelope:
    kind: Kind
    id: str | None = None
    type: str | None = None
    auth: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    ok: bool | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind.value}
        if self.id is not None:
            d["id"] = self.id
        if self.kind is Kind.RESPONSE:
            d["ok"] = bool(self.ok)
            if self.ok:
                d["result"] = self.result or {}
            else:
                d["error"] = self.error or {}
        else:
            d["type"] = self.type
            d["payload"] = self.payload
            if self.kind is Kind.REQUEST:
                d["auth"] = self.auth
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Envelope":
        try:
            kind = Kind(d["kind"])
        except (KeyError, ValueError) as exc:
            raise ProtocolError(ErrorCode.BAD_MESSAGE, "missing or invalid 'kind'") from exc
        env = cls(
            kind=kind,
            id=d.get("id"),
            type=d.get("type"),
            auth=d.get("auth") or {},
            payload=d.get("payload") or {},
            ok=d.get("ok"),
            result=d.get("result"),
            error=d.get("error"),
        )
        if kind in (Kind.REQUEST, Kind.PUSH) and not isinstance(env.type, str):
            raise ProtocolError(ErrorCode.BAD_MESSAGE, "missing 'type'")
        if kind is Kind.REQUEST and not isinstance(env.id, str):
            raise ProtocolError(ErrorCode.BAD_MESSAGE, "request missing 'id'")
        if not isinstance(env.payload, dict):
            raise ProtocolError(ErrorCode.BAD_MESSAGE, "'payload' must be an object")
        return env


# --- constructors -------------------------------------------------------------------------------

def request(type_: str, payload: dict[str, Any] | None = None, *,
            auth: dict[str, Any] | None = None, id_: str | None = None) -> Envelope:
    return Envelope(kind=Kind.REQUEST, id=id_ or uuid.uuid4().hex, type=type_,
                    auth=auth or {}, payload=payload or {})


def response(req_id: str, result: dict[str, Any] | None = None) -> Envelope:
    return Envelope(kind=Kind.RESPONSE, id=req_id, ok=True, result=result or {})


def error_response(req_id: str | None, code: ErrorCode, message: str = "") -> Envelope:
    return Envelope(kind=Kind.RESPONSE, id=req_id, ok=False,
                    error={"code": code.value, "message": message or code.value})


def push(type_: str, payload: dict[str, Any] | None = None) -> Envelope:
    return Envelope(kind=Kind.PUSH, type=type_, payload=payload or {})


# --- framing ------------------------------------------------------------------------------------

def encode(env: Envelope) -> bytes:
    """One JSON object, one line. Newlines inside strings are escaped by json.dumps."""
    return (json.dumps(env.to_dict(), separators=(",", ":")) + "\n").encode("utf-8")


def decode(line: bytes) -> Envelope:
    try:
        data = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(ErrorCode.BAD_MESSAGE, f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProtocolError(ErrorCode.BAD_MESSAGE, "message must be a JSON object")
    return Envelope.from_dict(data)
