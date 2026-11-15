"""The Engine setup registers this Engine with the store (docs/SEATS-AND-SETUP.md section 4; docs/STORE-CONTRACT.md section 3).

    register(store_url, data_dir, names, port, certificate_pem, company_name=..., company_id=...) -> {engine_id, company_id, ...}

The person signs in in their browser (the owner, or a member the owner invited); their company is chosen (made, if the account has none
yet, with `company_name`); the Engine is registered with its names, port and certificate. What comes back is kept in the protected data
folder, beside the master secret:

    store.json       {store_url, engine_id, engine_token, company_id}: how the Engine asks the store for new seats (engine/store.py)
    company.falcon   the store-signed company file every Worker setup is given with it (where this Engine is, its certificate)

The grants the store already has for it are fetched by the Engine itself when it starts. Registered once: running it again keeps what is there.
Internet is required, with no exception.
"""

from __future__ import annotations

import json
import urllib.parse
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from installers.common import InstallError


def register(store: str, data: Path, names: list[str], port: int, certificate_pem: str, *, company_name: str | None = None,
             company_id: str | None = None, open_browser: Callable[[str], Any] = webbrowser.open, say: Callable[[str], Any] = print) -> dict[str, Any]:
    from common import signed
    from installers.windows.store_signin import SignInError, _http, sign_in

    found = data / "store.json"
    if found.exists():
        got = json.loads(found.read_text(encoding="utf-8"))
        return {**got, "kept": True}
    if not store:
        raise InstallError("the store's address is not known (--store): the Engine is registered with the store at install")
    if not names:
        raise InstallError("the Engine's names are needed to register it (--names)")
    try:
        say("Sign in to your company's Falcon account in the browser that opened (the owner, or a member the owner invited).")
        token = sign_in(store, open_browser=open_browser)
        base = store.rstrip("/")
        companies = list(_http("GET", f"{base}/api/me/companies", token=token).get("companies") or [])
        if company_id is None:
            if not companies:
                if not company_name:
                    raise InstallError("this account has no company yet: give its name (--company-name) and it is made")
                company_id = str(_http("POST", f"{base}/api/companies", {"name": company_name}, token=token)["company_id"])
            elif len(companies) == 1:
                company_id = str(companies[0]["company_id"])
            else:
                listed = ", ".join(f"{c['company_id']} ({c.get('name')})" for c in companies)
                raise InstallError(f"this account belongs to {len(companies)} companies; say which (--company-id): {listed}")
        got = _http("POST", f"{base}/api/companies/{urllib.parse.quote(company_id)}/engines",
                    {"names": names, "port": port, "certificate": certificate_pem.strip()}, token=token)
    except SignInError as exc:
        raise InstallError(str(exc)) from exc
    try:
        company = signed.check(got.get("company"), "company")
    except signed.SignatureError as exc:
        raise InstallError(f"what the store sent cannot be trusted: {exc}") from exc
    if company.get("engine_id") != got.get("engine_id") or not got.get("engine_token"):
        raise InstallError("the store's answer does not name this Engine")
    data.mkdir(parents=True, exist_ok=True)
    (data / "company.falcon").write_text(json.dumps(got["company"]), encoding="utf-8")
    ident = {"store_url": store, "engine_id": str(got["engine_id"]), "engine_token": str(got["engine_token"]), "company_id": company_id}
    found.write_text(json.dumps(ident, indent=2), encoding="utf-8")
    say(f"Registered this Engine with the store as {ident['engine_id']} ({company.get('company_name') or company_id}).")
    return {**ident, "kept": False}
