"""The stand-in store (scripts/store_stub.py) answers the contract's API (docs/STORE-CONTRACT.md section 3), so everything built against it
works against the real store: the setups' sign-in (PKCE, loopback), an Engine registering, its grants, a certificate change, Admin claims."""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import secrets
import urllib.parse

import pytest

pytest.importorskip("cryptography")                                         # the stand-in store signs with it

from common import signed
from scripts.store_stub import StoreStub


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    stub = StoreStub().start()
    yield stub
    stub.stop()


def call(store, method, path, body=None, token=None, form=False):
    host, port = store.url.removeprefix("http://").split(":")
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = None
    if body is not None:
        if form:
            data, headers["Content-Type"] = urllib.parse.urlencode(body), "application/x-www-form-urlencoded"
        else:
            data, headers["Content-Type"] = json.dumps(body), "application/json"
    conn.request(method, path, body=data, headers=headers)
    r = conn.getresponse()
    raw = r.read()
    return r.status, (json.loads(raw) if raw else None), r.getheader("Location")


def sign_in(store, email="owner@test.local"):
    """What a setup does: PKCE, a loopback redirect, then the code exchanged for a short-lived token."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = "http://127.0.0.1:9/callback"
    q = urllib.parse.urlencode({"client_id": "falcon-setup", "redirect_uri": redirect, "state": "s1", "code_challenge": challenge,
                                "code_challenge_method": "S256", "login_hint": email})
    status, _, location = call(store, "GET", f"/oauth/authorize?{q}")
    assert status == 302 and location.startswith(redirect)
    back = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(location).query))
    assert back["state"] == "s1"
    status, _bad, _ = call(store, "POST", "/oauth/token", {"grant_type": "authorization_code", "code": back["code"], "redirect_uri": redirect,
                                                          "code_verifier": "not-it"}, form=True)
    assert status == 400                                                              # PKCE: only the setup that asked may finish
    q2 = urllib.parse.urlencode({"client_id": "falcon-setup", "redirect_uri": redirect, "state": "s2", "code_challenge": challenge,
                                 "code_challenge_method": "S256", "login_hint": email})
    location = call(store, "GET", f"/oauth/authorize?{q2}")[2]
    code = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(location).query))["code"]
    status, tok, _ = call(store, "POST", "/oauth/token", {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect,
                                                          "code_verifier": verifier}, form=True)
    assert status == 200
    return tok["access_token"]


def test_an_engine_registers_gets_its_grants_and_changes_its_certificate(store):
    member = sign_in(store)
    cid = call(store, "POST", "/api/companies", {"name": "Acme Ltd"}, member)[1]["company_id"]
    status, reg, _ = call(store, "POST", f"/api/companies/{cid}/engines", {"names": ["falcon.internal"], "port": 7400, "certificate": "CERT-1"}, member)
    assert status == 200 and reg["grants"] == []
    company = signed.check(reg["company"], "company")
    assert company["names"] == ["falcon.internal"] and company["certificates"] == ["CERT-1"] and company["company_name"] == "Acme Ltd"
    eid, etoken = reg["engine_id"], reg["engine_token"]
    call(store, "POST", "/_test/grants", {"engine_id": eid, "role": "worker", "seats": 20})                 # a Paddle purchase
    call(store, "POST", "/_test/grants", {"engine_id": eid, "role": "admin", "seats": 3})
    status, got, _ = call(store, "GET", f"/api/engines/{eid}/grants", token=etoken)
    seats = sorted((signed.check(g, "grant")["role"], signed.check(g, "grant")["seats"]) for g in got["grants"])
    assert status == 200 and seats == [("admin", 3), ("worker", 20)]
    assert call(store, "GET", f"/api/engines/{eid}/grants", token="someone-else")[0] == 401
    status, rolled, _ = call(store, "PUT", f"/api/engines/{eid}/certificates", {"certificates": ["CERT-1", "CERT-2"]}, etoken)
    assert status == 200 and signed.check(rolled["company"], "company")["certificates"] == ["CERT-1", "CERT-2"]


def test_an_admin_claim_goes_only_to_a_member_of_the_engine_s_company(store):
    owner = sign_in(store)
    cid = call(store, "POST", "/api/companies", {"name": "Acme Ltd"}, owner)[1]["company_id"]
    eid = call(store, "POST", f"/api/companies/{cid}/engines", {"names": ["falcon.internal"], "port": 7400, "certificate": "C"}, owner)[1]["engine_id"]
    stranger = sign_in(store, "stranger@elsewhere.test")
    assert call(store, "POST", f"/api/engines/{eid}/admin-claims", {"hostname": "IT-01", "hardware_id": "hw1"}, stranger)[0] == 403
    call(store, "POST", "/_test/members", {"company_id": cid, "email": "kofi@acme.test"})                    # the owner invites Kofi
    kofi = sign_in(store, "kofi@acme.test")
    engines = call(store, "GET", "/api/me/engines", token=kofi)[1]["engines"]
    assert [e["engine_id"] for e in engines] == [eid]
    status, got, _ = call(store, "POST", f"/api/engines/{eid}/admin-claims", {"hostname": "IT-01", "hardware_id": "hw1"}, kofi)
    claim = signed.check(got["claim"], "admin_claim")
    assert status == 200 and claim["member_email"] == "kofi@acme.test" and claim["engine_id"] == eid and claim["hostname"] == "IT-01"
    assert claim["expires_at"] > claim["issued_at"]
    assert signed.check(got["company"], "company")["engine_id"] == eid
    assert call(store, "GET", "/api/me/engines")[0] == 401                                                  # nobody signed in
