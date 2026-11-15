"""The Admin setup's sign-in to the store (docs/SEATS-AND-SETUP.md section 5; docs/STORE-CONTRACT.md section 3).

    python -m installers.windows.store_signin --store https://<store> --out <private data folder> [--engine <engine_id>]

The person signs in in their browser (Google or email, on the store's own page), the way desktop applications sign in: OAuth 2.0 authorization
code with PKCE (RFC 7636) and a loopback redirect (RFC 8252). Nothing is typed into the setup. The store lists the company's Engines (chosen at
once if there is one), issues an Admin claim for this PC (signed, valid 10 minutes) and gives the Engine's signed company file. Both signatures
are checked here, with the keys built into Falcon, and both files are written into `--out`:

    admin-claim.json    the claim; the service knocks with it and is given its key at once (the claim works once)
    company.falcon      where the Engine is and its certificate(s)

The access token lives only in this process. Internet is required: there is no other way in for an Admin.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

CLIENT_ID = "falcon-setup"
SIGN_IN_MINUTES = 10


class SignInError(RuntimeError):
    pass


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _http(method: str, url: str, body: dict[str, Any] | None = None, token: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", "Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            said = json.loads(exc.read().decode("utf-8")).get("error") or exc.reason
        except ValueError:
            said = exc.reason
        raise SignInError(f"the store said: {said}") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise SignInError(f"the store at {url.split('/api')[0].split('/oauth')[0]} cannot be reached ({exc}): the Admin setup needs the internet") from exc


def sign_in(store: str, *, open_browser: Callable[[str], Any] = webbrowser.open, wait: float = SIGN_IN_MINUTES * 60) -> str:
    """The person signs in in their browser; returns a short-lived access token (kept in memory only)."""
    _http("GET", f"{store.rstrip('/')}/.well-known/falcon-store-keys.json", timeout=15)   # the store answers, before anyone is sent to sign in
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(16)
    got: dict[str, str] = {}
    done = threading.Event()

    class Callback(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            url = urllib.parse.urlparse(self.path)
            if url.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            if q.get("state") == state and not done.is_set():
                got.update(q)
                done.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<!doctype html><title>Falcon</title><p style='font-family:sans-serif'>Signed in. You can close this tab and go "
                             b"back to the Falcon setup.</p>")

    server = http.server.HTTPServer(("127.0.0.1", 0), Callback)
    redirect = f"http://127.0.0.1:{server.server_address[1]}/callback"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"{store.rstrip('/')}/oauth/authorize?" + urllib.parse.urlencode({
            "client_id": CLIENT_ID, "redirect_uri": redirect, "response_type": "code", "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256"})
        open_browser(url)
        if not done.wait(wait):
            raise SignInError(f"nobody signed in within {int(wait // 60)} minutes")
    finally:
        server.shutdown()
        server.server_close()
    if "code" not in got:
        raise SignInError(f"the sign-in was not completed ({got.get('error') or 'no code came back'})")
    tok = _http("POST", f"{store.rstrip('/')}/oauth/token", {"grant_type": "authorization_code", "code": got["code"], "redirect_uri": redirect,
                                                            "code_verifier": verifier, "client_id": CLIENT_ID})
    if not tok.get("access_token"):
        raise SignInError("the store gave no access token")
    return str(tok["access_token"])


def engines(store: str, token: str) -> list[dict[str, Any]]:
    return list(_http("GET", f"{store.rstrip('/')}/api/me/engines", token=token).get("engines") or [])


def claim(store: str, token: str, engine_id: str, hostname: str, hardware_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """An Admin claim for this PC and the Engine's company file, both checked here. Returns the two signed envelopes."""
    from common import signed

    got = _http("POST", f"{store.rstrip('/')}/api/engines/{urllib.parse.quote(engine_id)}/admin-claims",
                {"hostname": hostname, "hardware_id": hardware_id}, token=token)
    env_claim, env_company = got.get("claim"), got.get("company")
    try:
        c = signed.check(env_claim, "admin_claim")
        co = signed.check(env_company, "company")
    except signed.SignatureError as exc:
        raise SignInError(f"what the store sent cannot be trusted: {exc}") from exc
    if c.get("engine_id") != engine_id or co.get("engine_id") != engine_id:
        raise SignInError("the store answered for another Engine")
    if str(c.get("hostname") or "").lower() != hostname.lower():
        raise SignInError("the claim names another machine")
    return env_claim, env_company                                                      # type: ignore[return-value]


def run(store: str, out: Path, *, engine_id: str | None = None, open_browser: Callable[[str], Any] = webbrowser.open,
        say: Callable[[str], Any] = print) -> dict[str, Any]:
    from common.machine import hardware_id

    if not store:
        raise SignInError("the store's address is not known (--store)")
    say("Sign in to your company's Falcon account in the browser that opened (the owner, or a member the owner invited).")
    token = sign_in(store, open_browser=open_browser)
    found = engines(store, token)
    if not found:
        raise SignInError("this account's company has no Engine yet: install the Engine first (falcon-engine-setup.exe)")
    if engine_id is None:
        if len(found) > 1:
            names = ", ".join(f"{e['engine_id']} ({', '.join(e.get('names') or [])})" for e in found)
            raise SignInError(f"this company has {len(found)} Engines; say which (--engine): {names}")
        engine_id = str(found[0]["engine_id"])
    chosen = next((e for e in found if e["engine_id"] == engine_id), None)
    if chosen is None:
        raise SignInError(f"no Engine {engine_id} in this company")
    hint = chosen.get("admin_seats_free_hint")
    if isinstance(hint, int) and hint <= 0:
        raise SignInError("no Admin seat is free on this Engine: more are bought in the store, or an Admin takes a seat back")
    env_claim, env_company = claim(store, token, engine_id, socket.gethostname(), hardware_id())
    out.mkdir(parents=True, exist_ok=True)
    (out / "admin-claim.json").write_text(json.dumps(env_claim), encoding="utf-8")
    (out / "company.falcon").write_text(json.dumps(env_company), encoding="utf-8")
    say(f"Signed in as {env_claim['doc'].get('member_email')}; this PC's Admin seat on {chosen.get('company_name') or engine_id} is waiting for it.")
    return {"engine_id": engine_id, "claim": out / "admin-claim.json", "company": out / "company.falcon"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sign in to the store and claim this PC's Admin seat")
    ap.add_argument("--store", required=True, help="the store's address")
    ap.add_argument("--out", required=True, help="where the claim and the company file are written (the protected data folder)")
    ap.add_argument("--engine", help="which Engine, when the company has several")
    a = ap.parse_args(argv)
    try:
        run(a.store, Path(a.out), engine_id=a.engine)
    except SignInError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
