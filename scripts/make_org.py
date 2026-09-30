"""Provision a department, an Admin and a Worker on a running Engine, and write their settings.

A fresh install has one account: the Super User that `python -m engine setup` bootstrapped. There is
no Admin and no Worker, so there is nothing to run at those levels and the console looks thin -- the
Super User's shell is eight areas by design (docs/UI.md rule 25).

This makes the other two, once, so each can be started with one command:

    environ-operator\\Scripts\\python.exe scripts\\make_org.py             # uses the saved Super User
    environ-operator\\Scripts\\python.exe scripts\\make_org.py --department Logistics

It writes `data/admin.json` (an Operator Client settings file, so the Admin console does not overwrite
the Super User's) and prints the Worker's command. Client keys are printed ONCE by the Engine at
provisioning and never again -- that is the design, not an oversight -- so they are written into
those files as they arrive.

Run it again and it makes another set: hostnames are numbered from what is already registered.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from operator_client.core import EngineConnection, LocalConfig


async def make(args: argparse.Namespace) -> int:
    su = LocalConfig.load()
    if not su.client_id:
        print("No saved Super User on this machine. Run `python -m engine setup` first.",
              file=sys.stderr)
        return 2

    conn = EngineConnection(su.engine_host, su.engine_port, client_id=su.client_id,
                            tls=su.tls, ca_cert=su.ca_cert, derived_key=su.client_key)
    try:
        ident = await conn.connect()
    except Exception as exc:                                    # noqa: BLE001 -- any failure is the same story
        print(f"Could not reach the Engine at {su.engine_host}:{su.engine_port} -- {exc}",
              file=sys.stderr)
        print("Start it first: `environ-engine\\Scripts\\python.exe -m engine`", file=sys.stderr)
        return 1
    if ident.role != "super_user":
        print(f"These settings are a {ident.role}; only the Super User can make a department.",
              file=sys.stderr)
        return 2

    tree = await conn.call("hierarchy.tree")
    existing = {d["name"]: d for d in tree.get("departments", [])}
    if args.department in existing:
        department_id = existing[args.department]["department_id"]
        print(f"Department {args.department!r} is already there (id {department_id}).")
    else:
        dept = await conn.call("hierarchy.department_create", {"name": args.department})
        department_id = dept["department"]["id"] if "department" in dept else dept["department_id"]
        print(f"Made the department {args.department!r} (id {department_id}).")

    taken = {w["hostname"] for d in tree.get("departments", [])
             for w in (d.get("workers", []) + d.get("admins", []))}

    def free(prefix: str) -> str:
        n = 1
        while f"{prefix}-{n:02d}" in taken:
            n += 1
        name = f"{prefix}-{n:02d}"
        taken.add(name)
        return name

    admin_host, worker_host = free("ADM"), free("WS")
    admin = await conn.call("hierarchy.account_create",
                            {"role": "admin", "hostname": admin_host, "department_id": department_id})
    worker = await conn.call("hierarchy.account_create",
                             {"role": "worker", "hostname": worker_host, "department_id": department_id})
    await conn.close()

    # the Admin gets its own settings file: one machine, three levels, and they must not share one
    admin_cfg = ROOT / "data" / "admin.json"
    admin_cfg.parent.mkdir(parents=True, exist_ok=True)
    admin_cfg.write_text(json.dumps({
        "engine_host": su.engine_host, "engine_port": su.engine_port,
        "client_id": admin["client_id"], "client_key": admin["client_key"],
        "tls": su.tls, "ca_cert": su.ca_cert, "prefs": {}, "cache": {},
    }, indent=2), encoding="utf-8")

    ca = f" --ca {su.ca_cert}" if su.tls and su.ca_cert else (" --plaintext" if not su.tls else "")
    print()
    print(f"  Admin    account {admin['account_id']}  on {admin_host}")
    print(f"  Worker   account {worker['account_id']}  on {worker_host}")
    print()
    print("Run the Admin's console (its own settings file, so the Super User's stay put):")
    print("  environ-operator\\Scripts\\python.exe -m operator_client --gui --config data\\admin.json")
    print()
    print("Run the Worker on this machine:")
    print(f"  environ-worker\\Scripts\\python.exe -m worker_client --engine "
          f"{su.engine_host}:{su.engine_port}{ca} \\")
    print(f"      --client-id {worker['client_id']} --client-key {worker['client_key']} \\")
    print(f"      --watch {ROOT / 'data' / 'demo'} --ui")
    print()
    print("The Worker's key is printed here once. It is not stored anywhere else -- put the command")
    print("somewhere before you close this window, or derive the key again from the master secret.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--department", default="Operations", help="the department to make or reuse")
    return asyncio.run(make(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
