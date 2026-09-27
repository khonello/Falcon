"""`python -m engine setup` -- make a fresh clone (or a freshly installed machine) ready to run, with no shell variables.

Every step is checked first and skipped when already done, so it is safe to run again:

  1. `.env`       written from .env.example if missing (the test database line switched on), then loaded
  2. certificate  data/engine.crt + .key for localhost, 127.0.0.1, this machine's name and any --names
  3. databases    the working and test databases, created if missing -- only when an admin login is given
                  (--admin-url postgresql://postgres:<password>@localhost:5432/postgres); otherwise the exact SQL
                  is printed and setup stops there
  4. schema       migrations applied to the working database
  5. secret       the master secret created (data/master.secret -- back it up)
  6. Super User   bootstrapped once on an empty database; its client id + key printed ONCE, and written into this
                  machine's Operator Client settings so it connects without typing anything
  7. local model  checked; --download-model fetches it (~640 MB) from Hugging Face

PostgreSQL itself and the three virtual environments are installed beforehand (the user's rule).
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from common import dotenv

ROOT = dotenv.REPO_ROOT
MODEL_URL = "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf"


def say(step: str, text: str) -> None:
    print(f"  {step:<12} {text}")


# --- 1. .env ------------------------------------------------------------------------------------------

def ensure_env() -> Path:
    env = ROOT / ".env"
    if env.exists():
        say(".env", f"kept ({env})")
    else:
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        env.write_text(text, encoding="utf-8")
        say(".env", f"written from .env.example ({env})")
    dotenv.load(env)
    return env


# --- 2. certificate -------------------------------------------------------------------------------------

def ensure_certificate(settings: Any, extra_names: list[str]) -> None:
    cert, key = settings.tls_cert, settings.tls_key
    if settings.dev_plaintext:
        say("certificate", "not needed (FALCON_DEV_PLAINTEXT is on)")
        return
    if cert is None or key is None:
        say("certificate", "FALCON_TLS_CERT / FALCON_TLS_KEY are not set in .env -- skipped")
        return
    cert, key = ROOT / cert if not cert.is_absolute() else cert, ROOT / key if not key.is_absolute() else key
    if cert.exists() and key.exists():
        say("certificate", f"kept ({cert})")
        return
    from engine.tls import generate_self_signed

    names = ["localhost", "127.0.0.1", socket.gethostname(), *extra_names]
    made_cert, _ = generate_self_signed(",".join(dict.fromkeys(n for n in names if n)), cert.parent)
    say("certificate", f"made for {', '.join(dict.fromkeys(names))} -> {made_cert} (ship it with every client)")


# --- 3. databases ------------------------------------------------------------------------------------------

def _parts(url: str) -> tuple[str, str, str]:
    u = urllib.parse.urlparse(url)
    return urllib.parse.unquote(u.username or ""), urllib.parse.unquote(u.password or ""), u.path.lstrip("/")


async def _reachable(url: str) -> str | None:
    """None when the database answers, else why not."""
    import asyncpg

    try:
        conn = await asyncpg.connect(url, timeout=10)
    except Exception as exc:                        # noqa: BLE001 -- any failure is reported, not raised
        return f"{type(exc).__name__}: {exc}"
    await conn.close()
    return None


async def ensure_databases(admin_url: str | None) -> bool:
    import os

    import asyncpg

    urls = [u for u in (os.environ.get("FALCON_DATABASE_URL"), os.environ.get("FALCON_TEST_DATABASE_URL")) if u]
    if not urls:
        say("databases", "FALCON_DATABASE_URL is not set in .env -- skipped")
        return False
    missing = {u: why for u in urls if (why := await _reachable(u))}
    if not missing:
        say("databases", ", ".join(_parts(u)[2] for u in urls) + " reachable")
        return True
    if not admin_url:
        say("databases", "not reachable yet: " + "; ".join(f"{_parts(u)[2]} ({w.split(':')[0]})" for u, w in missing.items()))
        user, password, _ = _parts(urls[0])
        print("\n  Give setup an admin login to create them:  python -m engine setup --admin-url "
              "postgresql://postgres:<password>@localhost:5432/postgres")
        print("  or run this SQL as a PostgreSQL superuser, then run setup again:\n")
        print(f"    CREATE ROLE {user} LOGIN PASSWORD '{password}';   -- skip if the role exists")
        for u in urls:
            print(f"    CREATE DATABASE {_parts(u)[2]} OWNER {user};")
        print()
        return False
    conn = await asyncpg.connect(admin_url, timeout=10)
    try:
        for u in missing:
            user, password, name = _parts(u)
            if not await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", user):
                await conn.execute(f'CREATE ROLE "{user}" LOGIN PASSWORD $pw${password}$pw$')
                say("databases", f"role {user} created")
            if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
                await conn.execute(f'CREATE DATABASE "{name}" OWNER "{user}"')
                say("databases", f"database {name} created")
    finally:
        await conn.close()
    still = [u for u in urls if await _reachable(u)]
    if still:
        say("databases", "still not reachable: " + ", ".join(_parts(u)[2] for u in still) + " (check the password in .env)")
        return False
    say("databases", "ready")
    return True


# --- 4-6. schema, secret, Super User -----------------------------------------------------------------------------

async def ensure_schema_and_super_user(settings: Any, hostname: str, write_operator: bool, engine_host: str) -> None:
    from engine.__main__ import provision_super_user
    from engine.database import Database
    from engine.master_secret import load_or_create

    db = Database(settings.database_url)
    await db.connect()
    try:
        await db.migrate()
        say("schema", "migrations applied")
        secret = settings.master_secret or load_or_create(ROOT / settings.secret_path
                                                          if not settings.secret_path.is_absolute() else settings.secret_path)
        say("secret", "master secret ready (data/master.secret -- back it up; every key derives from it)")
        existing = [a for a in await db.accounts.list_all() if a["role"] == "super_user" and a["status"] == "active"]
        if existing:
            say("Super User", f"already exists (account {existing[0]['id']}) -- nothing issued")
            return
        account_id, client_id, key = await provision_super_user(db, secret, hostname)
    finally:
        await db.close()
    say("Super User", f"account {account_id} on {hostname}")
    print(f"\n    client_id:  {client_id}\n    client_key: {key}\n")
    print("    Shown once. Keep them for the Super User's Operator Client install.\n")
    if write_operator:
        _write_operator_config(settings, engine_host, client_id, key)


def _write_operator_config(settings: Any, engine_host: str, client_id: str, key: str) -> None:
    try:
        from operator_client.core.config import LocalConfig
    except ImportError:
        say("operator", "the Operator Client is not installed here -- enter the id and key on its connect screen")
        return
    cfg = LocalConfig.load()
    cfg.engine_host, cfg.engine_port = engine_host, settings.port
    cfg.client_id, cfg.client_key = client_id, key
    cfg.tls = not settings.dev_plaintext
    if settings.tls_cert is not None:
        cert = settings.tls_cert if settings.tls_cert.is_absolute() else ROOT / settings.tls_cert
        cfg.ca_cert = str(cert)
    cfg.save()
    say("operator", f"this machine's Operator Client will connect as the Super User ({cfg.path})")


# --- 7. the local model --------------------------------------------------------------------------------------------

def ensure_model(settings: Any, download: bool) -> None:
    if settings.llm_backend != "llamacpp" or not settings.llm_model_path:
        say("model", f"served by {settings.llm_backend} at {settings.llm_endpoint}")
        return
    path = Path(settings.llm_model_path)
    path = path if path.is_absolute() else ROOT / path
    if path.exists():
        say("model", f"present ({path})")
        return
    if not download:
        say("model", f"missing: {path} -- run setup with --download-model, or fetch {MODEL_URL}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    say("model", f"downloading {MODEL_URL}")
    with urllib.request.urlopen(MODEL_URL, timeout=60) as r, part.open("wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r    {done * 100 // total:3d} %  {done >> 20} / {total >> 20} MB", end="", flush=True)
    print()
    part.replace(path)
    say("model", f"downloaded ({path})")


# --- the command ------------------------------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m engine setup", description=__doc__.split("\n\n")[0])
    ap.add_argument("--hostname", default=socket.gethostname(), help="the Super User's workstation name (default: this machine)")
    ap.add_argument("--names", default="", help="more names/IPs the clients will use to reach the Engine, comma-separated")
    ap.add_argument("--admin-url", default=None, help="a PostgreSQL superuser URL, to create the role and databases")
    ap.add_argument("--engine-host", default="127.0.0.1", help="where this machine's Operator Client reaches the Engine")
    ap.add_argument("--no-operator-config", action="store_true", help="do not write this machine's Operator Client settings")
    ap.add_argument("--download-model", action="store_true", help="fetch the local LLM model if it is missing")
    args = ap.parse_args(argv)

    print("Falcon setup\n")
    ensure_env()
    from engine.config import Settings

    settings = Settings.from_env()
    ensure_certificate(settings, [n.strip() for n in args.names.split(",") if n.strip()])
    ok = asyncio.run(ensure_databases(args.admin_url))
    if ok and settings.database_url:
        asyncio.run(ensure_schema_and_super_user(settings, args.hostname, not args.no_operator_config, args.engine_host))
    ensure_model(settings, args.download_model)
    print("\nDone." if ok else "\nNot finished: the databases above come first.")
    if ok:
        print("  Start the Engine:        python -m engine")
        print("  Start the Operator GUI:  python -m operator_client --gui")
        print("  Run the tests:           python -m pytest")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
