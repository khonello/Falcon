"""A stand-in for the Falcon store (docs/STORE-CONTRACT.md), so the Engine, the setups and the tests are built against the real API before
the store exists. NOT the store: no real sign-in, no payments, a test signing key anyone can derive.

    python scripts/store_stub.py [--port 8787] [--state data/store-stub.json]

Everything signed here is signed with the TEST key (kid "test-1"), which Falcon trusts only when FALCON_STORE_TEST_KEY=1. Sign-in is
automatic: /oauth/authorize signs in as `login_hint` (default owner@test.local) at once and redirects back, PKCE and all, so the setups'
real sign-in code runs unchanged against it. The device sign-in (a server with no browser) is the same: opening the link it gives
(`/device?user_code=...`) signs in as `login_hint` at once. Two calls exist only here, for tests and drills: POST /_test/grants (a Paddle purchase) and
POST /_test/members (the owner inviting someone). In the tests it runs in-process: `StoreStub().start()`.

Needs `cryptography` (to sign): environ-engine has it.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.signed import canonical
from common.store_keys import TEST_KID

TEST_SEED = hashlib.sha256(b"falcon store TEST key - trusted only with FALCON_STORE_TEST_KEY=1").digest()
DEFAULT_MEMBER = "owner@test.local"
CLAIM_MINUTES = 10
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


def now_iso(offset: float = 0.0) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def sign(doc: dict[str, Any]) -> dict[str, Any]:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.from_private_bytes(TEST_SEED)
    return {"doc": doc, "kid": TEST_KID, "sig": base64.b64encode(key.sign(canonical(doc))).decode("ascii")}


def _id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class State:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.data: dict[str, Any] = {"companies": {}, "engines": {}, "grants": [], "codes": {}, "tokens": {}, "claims": [], "devices": {}}
        if path and path.is_file():
            self.data.update(json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")

    # --- what the store knows ---------------------------------------------------------------------------------------

    def companies_of(self, email: str) -> list[dict[str, Any]]:
        return [dict(c, company_id=cid) for cid, c in self.data["companies"].items() if email in c["members"]]

    def company_doc(self, engine_id: str) -> dict[str, Any]:
        e = self.data["engines"][engine_id]
        c = self.data["companies"][e["company_id"]]
        return sign({"kind": "company", "company_id": e["company_id"], "company_name": c["name"], "engine_id": engine_id,
                     "names": e["names"], "port": e["port"], "certificates": e["certificates"], "issued_at": now_iso()})

    def add_grant(self, engine_id: str, role: str, seats: int, valid_from: str | None = None, valid_until: str | None = None) -> dict[str, Any]:
        e = self.data["engines"][engine_id]
        g = sign({"kind": "grant", "grant_id": _id("g"), "company_id": e["company_id"], "engine_id": engine_id, "role": role, "seats": int(seats),
                  "valid_from": valid_from or now_iso(), "valid_until": valid_until or now_iso(365 * 86400), "paddle_ref": _id("sub"),
                  "issued_at": now_iso()})
        self.data["grants"].append(g)
        return g


class StoreStub:
    def __init__(self, port: int = 0, state: Path | None = None) -> None:
        self.state = State(state)
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:                # quiet
                return

            def _send(self, code: int, body: Any = None, headers: dict[str, str] | None = None) -> None:
                raw = b"" if body is None else json.dumps(body).encode("utf-8")
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                if body is not None:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _peek(self) -> dict[str, Any]:
                if not hasattr(self, "_kept"):
                    self._kept = self._read_body()
                return self._kept

            def _body(self) -> dict[str, Any]:
                return self._peek()

            def _read_body(self) -> dict[str, Any]:
                n = int(self.headers.get("Content-Length") or 0)
                if not n:
                    return {}
                raw = self.rfile.read(n)
                ctype = self.headers.get("Content-Type", "")
                if "application/x-www-form-urlencoded" in ctype:
                    return {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode("utf-8")).items()}
                return json.loads(raw.decode("utf-8") or "{}")

            def _bearer(self) -> str:
                auth = self.headers.get("Authorization", "")
                return auth[7:] if auth.startswith("Bearer ") else ""

            def _member(self) -> str | None:
                tok = stub.state.data["tokens"].get(self._bearer())
                return tok["email"] if tok and tok["expires"] > time.time() else None

            def _engine(self, engine_id: str) -> dict[str, Any] | None:
                e = stub.state.data["engines"].get(engine_id)
                return e if e and secrets.compare_digest(e["token"], self._bearer()) else None

            def do_GET(self) -> None:
                with stub.state.lock:
                    self._route("GET")

            def do_POST(self) -> None:
                with stub.state.lock:
                    self._route("POST")

            def do_PUT(self) -> None:
                with stub.state.lock:
                    self._route("PUT")

            def _route(self, method: str) -> None:
                self.__dict__.pop("_kept", None)                                # one request's body, never the one before it
                url = urllib.parse.urlparse(self.path)
                parts = [p for p in url.path.split("/") if p]
                q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
                d = stub.state.data
                try:
                    if method == "GET" and url.path == "/oauth/authorize":
                        code = secrets.token_urlsafe(16)
                        d["codes"][code] = {"email": q.get("login_hint") or DEFAULT_MEMBER, "challenge": q.get("code_challenge", ""),
                                            "redirect_uri": q.get("redirect_uri", ""), "expires": time.time() + 300}
                        sep = "&" if "?" in q.get("redirect_uri", "") else "?"
                        return self._send(302, None, {"Location": f"{q['redirect_uri']}{sep}code={code}&state={urllib.parse.quote(q.get('state', ''))}"})
                    if method == "POST" and url.path == "/oauth/device_authorization":
                        device, user = secrets.token_urlsafe(24), "-".join(secrets.token_hex(2).upper() for _ in range(2))
                        d.setdefault("devices", {})[device] = {"user_code": user, "email": None, "expires": time.time() + 600}
                        base = f"http://{self.headers.get('Host')}"
                        return self._send(200, {"device_code": device, "user_code": user, "verification_uri": f"{base}/device",
                                                "verification_uri_complete": f"{base}/device?user_code={user}", "interval": 1, "expires_in": 600})
                    if method == "GET" and url.path == "/device":
                        for dev in d.setdefault("devices", {}).values():
                            if dev["user_code"] == q.get("user_code"):
                                dev["email"] = q.get("login_hint") or DEFAULT_MEMBER
                                return self._send(200, {"signed_in": dev["email"]})
                        return self._send(404, {"error": "no such code"})
                    if method == "POST" and url.path == "/oauth/token" and self._peek().get("grant_type") == DEVICE_GRANT:
                        dev = d.setdefault("devices", {}).get(self._body().get("device_code", ""))
                        if dev is None or dev["expires"] < time.time():
                            return self._send(400, {"error": "expired_token"})
                        if dev["email"] is None:
                            return self._send(400, {"error": "authorization_pending"})
                        token = secrets.token_urlsafe(24)
                        d["tokens"][token] = {"email": dev["email"], "expires": time.time() + 600}
                        return self._send(200, {"access_token": token, "token_type": "Bearer", "expires_in": 600})
                    if method == "POST" and url.path == "/oauth/token":
                        b = self._body()
                        c = d["codes"].pop(b.get("code", ""), None)
                        verifier = b.get("code_verifier", "")
                        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
                        if not c or c["expires"] < time.time() or c["redirect_uri"] != b.get("redirect_uri") or c["challenge"] != challenge:
                            return self._send(400, {"error": "invalid_grant"})
                        token = secrets.token_urlsafe(24)
                        d["tokens"][token] = {"email": c["email"], "expires": time.time() + 600}
                        return self._send(200, {"access_token": token, "token_type": "Bearer", "expires_in": 600})
                    if method == "GET" and url.path == "/.well-known/falcon-store-keys.json":
                        from cryptography.hazmat.primitives import serialization
                        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                            Ed25519PrivateKey,
                        )

                        pub = Ed25519PrivateKey.from_private_bytes(TEST_SEED).public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
                        return self._send(200, {"keys": [{"kid": TEST_KID, "ed25519_public_key": base64.b64encode(pub).decode()}]})
                    if parts[:2] == ["_test", "grants"] and method == "POST":
                        b = self._body()
                        g = stub.state.add_grant(b["engine_id"], b["role"], b["seats"], b.get("valid_from"), b.get("valid_until"))
                        stub.state.save()
                        return self._send(200, g)
                    if parts[:2] == ["_test", "members"] and method == "POST":
                        b = self._body()
                        d["companies"][b["company_id"]]["members"].append(b["email"])
                        stub.state.save()
                        return self._send(200, {})
                    if parts[:1] != ["api"]:
                        return self._send(404, {"error": "not_found"})
                    # --- the engine's own calls (its token) ---
                    if len(parts) >= 4 and parts[1] == "engines" and parts[3] in ("grants", "certificates", "usage"):
                        e = self._engine(parts[2])
                        if e is None:
                            return self._send(401, {"error": "not this engine's token"})
                        if parts[3] == "grants" and method == "GET":
                            return self._send(200, {"grants": [g for g in d["grants"] if g["doc"]["engine_id"] == parts[2]]})
                        if parts[3] == "certificates" and method == "PUT":
                            e["certificates"] = list(self._body()["certificates"])
                            stub.state.save()
                            return self._send(200, {"company": stub.state.company_doc(parts[2])})
                        if parts[3] == "usage" and method == "POST":
                            e["usage"] = self._body()
                            stub.state.save()
                            return self._send(200, {})
                    # --- a signed-in member's calls ---
                    email = self._member()
                    if email is None:
                        return self._send(401, {"error": "sign in first"})
                    if parts == ["api", "me", "companies"] and method == "GET":
                        return self._send(200, {"companies": [{"company_id": c["company_id"], "name": c["name"], "owner": c["owner"]}
                                                              for c in stub.state.companies_of(email)]})
                    if parts == ["api", "companies"] and method == "POST":
                        cid = _id("c")
                        d["companies"][cid] = {"name": str(self._body().get("name") or "A company"), "owner": email, "members": [email]}
                        stub.state.save()
                        return self._send(200, {"company_id": cid})
                    if len(parts) == 4 and parts[1] == "companies" and parts[3] == "engines" and method == "POST":
                        if parts[2] not in {c["company_id"] for c in stub.state.companies_of(email)}:
                            return self._send(403, {"error": "not a member of this company"})
                        b = self._body()
                        eid = _id("e")
                        d["engines"][eid] = {"company_id": parts[2], "names": list(b["names"]), "port": int(b["port"]),
                                             "certificates": [b["certificate"]], "token": secrets.token_urlsafe(32), "usage": {}}
                        stub.state.save()
                        return self._send(200, {"engine_id": eid, "engine_token": d["engines"][eid]["token"], "company": stub.state.company_doc(eid),
                                                "grants": [g for g in d["grants"] if g["doc"]["engine_id"] == eid]})
                    if parts == ["api", "me", "engines"] and method == "GET":
                        mine = {c["company_id"] for c in stub.state.companies_of(email)}
                        out = []
                        for eid, e in d["engines"].items():
                            if e["company_id"] in mine:
                                bought = sum(g["doc"]["seats"] for g in d["grants"] if g["doc"]["engine_id"] == eid and g["doc"]["role"] == "admin")
                                out.append({"engine_id": eid, "company_name": d["companies"][e["company_id"]]["name"], "names": e["names"],
                                            "admin_seats_free_hint": bought - int(e.get("usage", {}).get("admin_in_use", 0))})
                        return self._send(200, {"engines": out})
                    if len(parts) == 4 and parts[1] == "engines" and parts[3] == "admin-claims" and method == "POST":
                        e = d["engines"].get(parts[2])
                        if e is None or e["company_id"] not in {c["company_id"] for c in stub.state.companies_of(email)}:
                            return self._send(403, {"error": "not a member of this Engine's company"})
                        b = self._body()
                        claim = sign({"kind": "admin_claim", "claim_id": _id("a"), "company_id": e["company_id"], "engine_id": parts[2],
                                      "member_email": email, "hostname": str(b.get("hostname") or ""), "hardware_id": str(b.get("hardware_id") or ""),
                                      "issued_at": now_iso(), "expires_at": now_iso(CLAIM_MINUTES * 60)})
                        d["claims"].append(claim)
                        stub.state.save()
                        return self._send(200, {"claim": claim, "company": stub.state.company_doc(parts[2])})
                    return self._send(404, {"error": "not_found"})
                except (KeyError, ValueError, TypeError) as exc:
                    return self._send(400, {"error": f"bad request: {exc}"})

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def start(self) -> StoreStub:
        self.thread = threading.Thread(target=self.server.serve_forever, name="store-stub", daemon=True)
        self.thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--state", type=Path, help="keep what it knows in this file across runs")
    a = ap.parse_args()
    stub = StoreStub(a.port, a.state)
    print(f"store stub on {stub.url} (TEST key {TEST_KID}: trusted only with FALCON_STORE_TEST_KEY=1)", flush=True)
    try:
        stub.server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
