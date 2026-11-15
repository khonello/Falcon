"""The Engine setup registers the Engine with the store (installers/store_register.py; docs/SEATS-AND-SETUP.md section 4), against the stub,
with the real sign-in code."""

from __future__ import annotations

import json
import urllib.request

import pytest

from installers.common import InstallError

PEM = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----"


def _browser(url: str) -> None:
    urllib.request.urlopen(url, timeout=10).read()


@pytest.fixture
def store(monkeypatch, tmp_path):
    pytest.importorskip("cryptography")
    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    from scripts.store_stub import StoreStub

    s = StoreStub(state=tmp_path / "store-state.json").start()
    yield s
    s.stop()


def test_a_new_account_names_its_company_and_the_engine_is_registered_once(store, tmp_path):
    from common import signed
    from installers.store_register import register

    data = tmp_path / "data"
    with pytest.raises(InstallError, match="no company yet"):
        register(store.url, data, ["falcon.internal"], 7400, PEM, open_browser=_browser, say=lambda m: None)
    got = register(store.url, data, ["falcon.internal", "ENG-01"], 7400, PEM, company_name="Acme", open_browser=_browser, say=lambda m: None)
    assert not got["kept"] and got["engine_id"].startswith("e_")
    ident = json.loads((data / "store.json").read_text(encoding="utf-8"))
    assert set(ident) == {"store_url", "engine_id", "engine_token", "company_id"} and ident["engine_token"]
    company = signed.load(data / "company.falcon", "company")                       # the file every Worker setup is given, signed
    assert company["names"] == ["falcon.internal", "ENG-01"] and company["port"] == 7400 and company["company_name"] == "Acme"
    again = register(store.url, data, ["other"], 7400, PEM, open_browser=_browser, say=lambda m: None)
    assert again["kept"] and again["engine_id"] == got["engine_id"]                 # never registered twice
    assert len(store.state.data["engines"]) == 1


def test_an_account_in_one_company_needs_no_choosing_and_one_in_several_must_say(store, tmp_path):
    from installers.store_register import register

    d = store.state.data
    d["companies"]["c_a"] = {"name": "A", "owner": "owner@test.local", "members": ["owner@test.local"]}
    got = register(store.url, tmp_path / "one", ["falcon.internal"], 7400, PEM, open_browser=_browser, say=lambda m: None)
    assert got["company_id"] == "c_a"
    d["companies"]["c_b"] = {"name": "B", "owner": "x@test.local", "members": ["x@test.local", "owner@test.local"]}
    with pytest.raises(InstallError, match="2 companies"):
        register(store.url, tmp_path / "two", ["falcon.internal"], 7400, PEM, open_browser=_browser, say=lambda m: None)
    assert register(store.url, tmp_path / "two", ["falcon.internal"], 7400, PEM, company_id="c_b", open_browser=_browser,
                    say=lambda m: None)["company_id"] == "c_b"


def test_without_the_store_nothing_is_registered(tmp_path):
    from installers.store_register import register

    with pytest.raises(InstallError, match="cannot be reached"):
        register("http://127.0.0.1:9", tmp_path, ["falcon.internal"], 7400, PEM, open_browser=lambda u: None, say=lambda m: None)
    with pytest.raises(InstallError, match="store's address"):
        register("", tmp_path, ["falcon.internal"], 7400, PEM, say=lambda m: None)
    assert not (tmp_path / "store.json").exists()
