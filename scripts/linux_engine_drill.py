"""Drill: the Linux Engine, for real, from the .deb (WSL or a test server; NEVER a server in use). Run as root:

    python3 scripts/linux_engine_drill.py dist/falcon-engine_<v>_<arch>.deb [--keep]

With a stand-in store (scripts/store_stub.py, its test key trusted for this run only), it:
  1. installs the package and runs `falcon-engine-install` as a person would: its own PostgreSQL, the store sign-in by a link and a code
     (opened here, as the stub allows), no first Admin;
  2. checks the private PostgreSQL: its own port (not 5432), localhost only, no socket file, its own user, pgdata 0700; the Engine's role
     in, the superuser and every other database refused; nothing on PATH; the distribution's own clusters untouched;
  3. checks the Engine: answering on 7400 over TLS; store.json and the company file beside the master secret, readable by it alone;
  4. an Admin's PC comes in with a store claim (as the Admin setup gives it), and signs in as an Admin;
  5. installs the package again (an upgrade): the data, the secret and the registration are kept, and it answers again;
  6. removes the package: both services go, the data stays; then (unless --keep) takes the drill's data away.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["FALCON_STORE_TEST_KEY"] = "1"

ok = True


def check(what: str, good: bool) -> None:
    global ok
    ok &= bool(good)
    print(f"  [{'ok' if good else 'FAIL'}] {what}", flush=True)


def sh(*argv: str, env: dict | None = None, check_rc: bool = True) -> str:
    p = subprocess.run(list(argv), capture_output=True, text=True, env=env, check=False)
    if check_rc and p.returncode != 0:
        raise SystemExit(f"{' '.join(argv[:4])} exited {p.returncode}:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return p.stdout + p.stderr


def clusters() -> str:
    return sh("pg_lsclusters", check_rc=False) if shutil.which("pg_lsclusters") else ""


def login(url: str) -> str:
    py = "/opt/falcon/venv/bin/python"
    code = ("import asyncio, asyncpg, sys\n"
            "async def m():\n c = await asyncpg.connect(sys.argv[1], timeout=10)\n print(await c.fetchval('select current_user'))\n await c.close()\n"
            "asyncio.run(m())")
    p = subprocess.run([py, "-c", code, url], capture_output=True, text=True, check=False)
    return p.stdout.strip() if p.returncode == 0 else "REFUSED: " + (p.stderr.strip().splitlines() or ["?"])[-1]


async def admin_claim(store_url: str, engine_id: str) -> bool:
    from common.connection import EngineConnection
    from common.machine import hardware_id, mac
    from installers.store_signin import _http, sign_in

    token = sign_in(store_url, open_browser=lambda u: urllib.request.urlopen(u, timeout=10).read())
    got = _http("POST", f"{store_url}/api/engines/{engine_id}/admin-claims", {"hostname": "IT-01", "hardware_id": hardware_id()}, token=token)
    cert = "/var/lib/falcon/engine.crt"
    m = EngineConnection("127.0.0.1", 7400, client_id="", tls=True, ca_cert=cert)
    await m.open()
    try:
        seated = await m.call("knock.hello", {"install_token": secrets.token_urlsafe(24), "hostname": "IT-01", "hardware_id": hardware_id(),
                                              "mac": mac(), "os": "Windows 11", "admin_claim": got["claim"]})
    finally:
        await m.close()
    check("an Admin's PC with a store claim is let in at once", seated.get("status") == "seated" and seated.get("role") == "admin")
    me = EngineConnection("127.0.0.1", 7400, client_id=seated["client_id"], tls=True, ca_cert=cert, derived_key=seated["client_key"], hostname="IT-01")
    ident = await me.connect()
    await me.close()
    return ident.role == "admin"


def answering(port: int, seconds: float = 60) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), 1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("deb", type=Path)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run as root")
    if Path("/opt/falcon").exists() or Path("/var/lib/falcon").exists():
        raise SystemExit("Falcon is already on this machine: this drill is for a clean test machine only")
    from scripts.store_stub import StoreStub

    before = clusters()
    store = StoreStub(port=8787, state=Path("/tmp/falcon-drill-store.json")).start()
    try:
        print("1. install", flush=True)
        sh("dpkg", "-i", str(a.deb))
        out = sh("falcon-engine-install", "--names", "falcon.internal,127.0.0.1", "--store", store.url, "--company-name", "Drill",
                 "--test-open-link", env={**os.environ, "FALCON_STORE_TEST_KEY": "1"})
        print("\n".join("   " + ln for ln in out.splitlines() if ln.startswith(("[", "Sign in")) or "registered" in ln)[:3000], flush=True)
        check("signed in by a link and a code (no browser on a server)", "enter the code" in out)
        check("no first Admin was made", not Path("/var/lib/falcon/first-admin.txt").exists() and "client_key:" not in out)

        print("2. its own PostgreSQL", flush=True)
        from installers.engine.pgsql import LinuxPostgres, find_bin

        pg = LinuxPostgres(bin=find_bin(Path("/opt/falcon/pgsql")))
        port = pg.port()
        check(f"its own port ({port}), not 5432", port and port != 5432)
        check("falcon-postgres is running", sh("systemctl", "is-active", "falcon-postgres", check_rc=False).strip() == "active")
        listen = [ln.split()[3] for ln in sh("ss", "-ltnH").splitlines() if ln.split()[3].endswith(f":{port}")]
        check(f"listens on this server only ({', '.join(listen)})", listen and all(x.startswith(("127.0.0.1:", "[::1]:")) for x in listen))
        check("no socket file", not list(Path("/var/run/postgresql").glob(f".s.PGSQL.{port}*")) and not list(Path("/tmp").glob(f".s.PGSQL.{port}*")))
        st = pg.pgdata.stat()
        check("pgdata: its own user, 0700", oct(st.st_mode & 0o777) == "0o700" and sh("stat", "-c", "%U", str(pg.pgdata)).strip() == "falcon-pg")
        env_lines = dict(ln.split("=", 1) for ln in Path("/etc/falcon/falcon.env").read_text().splitlines() if "=" in ln and not ln.startswith("#"))
        url = env_lines["FALCON_DATABASE_URL"]
        check("the Engine's role logs in", login(url) == "falcon")
        su = pg.password_file.read_text().strip()
        check("the superuser is refused", login(f"postgresql://postgres:{su}@127.0.0.1:{port}/postgres").startswith("REFUSED"))
        check("the Engine's role reaches no other database", login(url.rsplit("/", 1)[0] + "/postgres").startswith("REFUSED"))
        check("the superuser's password is root's alone", oct(pg.password_file.stat().st_mode & 0o777) == "0o600" and pg.password_file.stat().st_uid == 0)
        check("nothing on PATH", shutil.which("postgres") is None and "/opt/falcon" not in os.environ.get("PATH", ""))
        check("FALCON_PG_BIN names its own tools", env_lines.get("FALCON_PG_BIN", "").startswith("/opt/falcon/pgsql/"))
        check("the distribution's own clusters are untouched", clusters() == before)

        print("3. the Engine", flush=True)
        check("falcon-engine answers on 7400", answering(7400))
        ident = json.loads(Path("/var/lib/falcon/store.json").read_text())
        check("registered with the store (store.json, 0600, the falcon user's)", ident["engine_id"].startswith("e_")
              and oct(Path("/var/lib/falcon/store.json").stat().st_mode & 0o777) == "0o600"
              and sh("stat", "-c", "%U", "/var/lib/falcon/store.json").strip() == "falcon")
        check("the company file is there", Path("/var/lib/falcon/company.falcon").exists())

        print("4. an Admin's PC with its claim", flush=True)
        with Path("/etc/falcon/falcon.env").open("a") as f:
            f.write("FALCON_STORE_TEST_KEY=1\n")                                     # this drill's stand-in store only
        urllib.request.urlopen(urllib.request.Request(f"{store.url}/_test/grants", method="POST", headers={"Content-Type": "application/json"},
                                                      data=json.dumps({"engine_id": ident["engine_id"], "role": "admin", "seats": 2}).encode())).read()
        sh("systemctl", "restart", "falcon-engine")
        check("answers again after a restart", answering(7400))
        time.sleep(7)                                                                  # it asks the store for its seats as it starts
        check("it signs in as an Admin", asyncio.run(admin_claim(store.url, ident["engine_id"])))

        print("5. an upgrade", flush=True)
        secret = Path("/var/lib/falcon/master.secret").read_bytes()
        sh("dpkg", "-i", str(a.deb))
        check("answers after the upgrade", answering(7400))
        check("the secret, the registration and the database are kept", Path("/var/lib/falcon/master.secret").read_bytes() == secret
              and json.loads(Path("/var/lib/falcon/store.json").read_text())["engine_id"] == ident["engine_id"] and pg.port() == port)

        print("6. removal", flush=True)
        sh("dpkg", "-r", "falcon-engine")
        check("both services are gone", sh("systemctl", "is-active", "falcon-engine", check_rc=False).strip() != "active"
              and sh("systemctl", "is-active", "falcon-postgres", check_rc=False).strip() != "active")
        check("the data is kept", Path("/var/lib/falcon/master.secret").exists() and (pg.pgdata / "PG_VERSION").exists())
        check("the distribution's own clusters are still untouched", clusters() == before)
    finally:
        store.stop()
        if not a.keep:
            sh("dpkg", "--purge", "falcon-engine", check_rc=False)
            for d in ("/var/lib/falcon", "/etc/falcon", "/var/log/falcon", "/var/lib/falcon-postgres", "/opt/falcon"):
                shutil.rmtree(d, ignore_errors=True)
            for u in ("falcon", "falcon-pg"):
                sh("userdel", u, check_rc=False)
            Path("/tmp/falcon-drill-store.json").unlink(missing_ok=True)
    print("drill passed" if ok else "drill FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
