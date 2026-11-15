"""A loose picture of the whole machine, for Detective alone (docs/design/proposals-core-features.md, item 3; the user, 15 Nov 2026).

Not `worker_client/snapshot.py`, which is what the index was last told about the files. This one is taken two minutes after connecting and every six hours, and
sent to the Engine (`detective.snapshot`), which compares it with the last one. No page shows it: only a finding it leads to, as evidence in a case.
Everything is read from Windows itself, stdlib only (the registry, two network-management calls, file sizes; drives through psutil, already here):

    drives       each fixed drive's size and free space
    places       the size and file count of each person's own places, Temp, the Recycle Bin and Windows Update's downloads (walked only while
                 the machine is idle, within a budget; `partial` when cut short)
    admins       who is in the local Administrators group (by its SID, so its name in any language)
    accounts     the local accounts
    startup      what starts by itself at sign-in: the Run / RunOnce keys of the machine and of each person signed in, and the Startup folders
    services     services that start by themselves (Win32 services, not drivers)
    tasks        scheduled tasks (Windows' own, under \\Microsoft, left out)
    programs     programs installed, for the machine and for each person
    shares       folders shared on the network
    defender     real-time protection on or off; firewall on or off for each profile
    logs         the size of the Security, System and Application event logs

A section that cannot be read is left out, never sent empty: the Engine compares only what both pictures have, so a part that failed to read is
never taken for "every administrator was removed". Falcon's own service, programs and tasks are left out of what is compared.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

from common.connection import ConnectionError_, EngineError
from worker_client import idle
from worker_client.places import PEOPLE, PROFILE_LIST, Registry, WinRegistry
from worker_client.places import read as read_places

log = logging.getLogger(__name__)

EVERY_SECONDS = 6 * 3600.0
FIRST_AFTER = 120.0
WALK_FILES = 300_000                 # the most files the place walk counts, all places together
WALK_SECONDS = 30.0                  # ... and the longest it takes
IDLE_FOR = 60.0                      # the walk runs only after this much idle, and stops the moment someone is back
CAP = 2000                           # the most items a list section holds
SIZED = ("desktop", "documents", "downloads", "pictures", "videos", "music", "onedrive", "temp")
RUN_KEYS = (r"Software\Microsoft\Windows\CurrentVersion\Run", r"Software\Microsoft\Windows\CurrentVersion\RunOnce")
UNINSTALL = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
OURS = ("falcon",)                   # what Falcon itself installs and starts: never a change worth reading


def _ours(text: str) -> bool:
    t = text.lower()
    return any(o in t for o in OURS)


def _section(name: str, fn: Callable[[], Any]) -> tuple[str, Any] | None:
    try:
        value = fn()
    except Exception:                                       # one part that cannot be read must not lose the rest
        log.info("snapshot: %s could not be read", name, exc_info=True)
        return None
    return None if value is None else (name, value)


# --- the registry parts ----------------------------------------------------------------------------------------------

def _people(reg: Registry) -> list[str]:
    loaded = {k.lower() for k in reg.subkeys("HKU", "")}
    return [sid for sid in reg.subkeys("HKLM", PROFILE_LIST) if sid.startswith(PEOPLE) and sid.lower() in loaded]


def _user_of(reg: Registry, sid: str) -> str:
    home = str(reg.values("HKLM", PROFILE_LIST + "\\" + sid).get("ProfileImagePath") or "")
    return home.rstrip("\\/").replace("/", "\\").rsplit("\\", 1)[-1] or sid


def startup_entries(reg: Registry, places: list[dict[str, Any]], listdir: Callable[[str], list[str]] = os.listdir) -> list[str]:
    out: list[str] = []
    hives = [("HKLM", "SOFTWARE\\"), ("HKLM", "SOFTWARE\\WOW6432Node\\")] + [("HKU", sid + "\\Software\\") for sid in _people(reg)]
    for root, prefix in hives:
        who = "the machine" if root == "HKLM" else _user_of(reg, prefix.split("\\", 1)[0])
        for key in RUN_KEYS:
            for name, command in reg.values(root, prefix + key[len("Software\\"):]).items():
                if isinstance(command, str) and not _ours(name + command):
                    out.append(f"{who}: {key.rsplit(chr(92), 1)[-1]}: {name} = {command[:300]}")
    for p in places:
        if p["kind"] == "startup" and not p.get("guessed"):
            try:
                names = listdir(p["path"])
            except OSError:
                continue
            out += [f"{p['user'] or 'the machine'}: Startup folder: {n}" for n in names if n.lower() != "desktop.ini" and not _ours(n)]
    return sorted(set(out))[:CAP]


def services(reg: Registry) -> list[str]:
    base = r"SYSTEM\CurrentControlSet\Services"
    out = []
    for name in reg.subkeys("HKLM", base):
        v = reg.values("HKLM", base + "\\" + name)
        kind, start = v.get("Type"), v.get("Start")
        if isinstance(kind, int) and kind & 0x30 and start == 2 and not _ours(name + str(v.get("ImagePath", ""))):     # a Win32 service that starts by itself
            out.append(f"{name} = {str(v.get('ImagePath', ''))[:300]}")
    return sorted(out)[:CAP]


def programs(reg: Registry) -> list[str]:
    keys = [("HKLM", "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"), ("HKLM", "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall")]
    keys += [("HKU", sid + "\\" + UNINSTALL) for sid in _people(reg)]
    out = set()
    for root, key in keys:
        for sub in reg.subkeys(root, key):
            v = reg.values(root, key + "\\" + sub)
            name = v.get("DisplayName")
            if isinstance(name, str) and name.strip() and not v.get("SystemComponent") and not _ours(name):
                out.add(f"{name.strip()[:200]} {str(v.get('DisplayVersion') or '').strip()[:40]}".strip())
    return sorted(out)[:CAP]


def shares(reg: Registry) -> list[str]:
    v = reg.values("HKLM", r"SYSTEM\CurrentControlSet\Services\LanmanServer\Shares")
    out = []
    for name, value in v.items():
        path = next((x[5:] for x in value if isinstance(x, str) and x.startswith("Path=")), "") if isinstance(value, list) else ""
        out.append(f"{name} = {path}")
    return sorted(out)[:CAP]


def defender(reg: Registry) -> dict[str, bool]:
    rt = reg.values("HKLM", r"SOFTWARE\Microsoft\Windows Defender\Real-Time Protection")
    pol = reg.values("HKLM", r"SOFTWARE\Policies\Microsoft\Windows Defender")
    pol_rt = reg.values("HKLM", r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection")
    out = {"realtime_off": bool(rt.get("DisableRealtimeMonitoring") or pol.get("DisableAntiSpyware") or pol_rt.get("DisableRealtimeMonitoring"))}
    fw = r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy"
    for profile in ("DomainProfile", "StandardProfile", "PublicProfile"):
        value = reg.values("HKLM", fw + "\\" + profile).get("EnableFirewall")
        if isinstance(value, int):
            out[f"firewall_off_{profile[:-7].lower()}"] = value == 0
    return out


def tasks(root: str, cap: int = CAP) -> list[str]:
    out: list[str] = []
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        if rel.split(os.sep)[0].lower() == "microsoft":
            dirs[:] = []
            continue
        out += [os.path.join(rel, f) if rel != "." else f for f in files if not _ours(f)]
        if len(out) >= cap:
            break
    return sorted(out)[:cap]


def log_sizes(system_root: str) -> dict[str, int]:
    folder = os.path.join(system_root, "System32", "winevt", "Logs")
    out = {}
    for name in ("Security", "System", "Application"):
        try:
            out[name] = os.stat(os.path.join(folder, name + ".evtx")).st_size
        except OSError:
            pass
    return out


# --- the network-management parts (Windows only) ---------------------------------------------------------------------

def _net_names(fn_name: str, *args: Any) -> list[str] | None:
    import ctypes
    from ctypes import wintypes

    netapi = ctypes.WinDLL("netapi32")
    buf, read, total = ctypes.c_void_p(), wintypes.DWORD(), wintypes.DWORD()
    rc = getattr(netapi, fn_name)(None, *args, ctypes.byref(buf), wintypes.DWORD(0xFFFFFFFF), ctypes.byref(read), ctypes.byref(total), None)
    if rc != 0:
        return None
    try:
        arr = ctypes.cast(buf, ctypes.POINTER(ctypes.c_wchar_p))       # level 0 / level 3: the first field is the name
        return sorted(str(arr[i]) for i in range(read.value))
    finally:
        netapi.NetApiBufferFree(buf)


def admins() -> list[str] | None:
    """Members of the local Administrators group, found by its SID (S-1-5-32-544), so its name in any language."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32")
    sid = ctypes.c_void_p()
    if not advapi.ConvertStringSidToSidW("S-1-5-32-544", ctypes.byref(sid)):
        return None
    try:
        name, dom = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
        n1, n2, use = wintypes.DWORD(256), wintypes.DWORD(256), wintypes.DWORD()
        if not advapi.LookupAccountSidW(None, sid, name, ctypes.byref(n1), dom, ctypes.byref(n2), ctypes.byref(use)):
            return None
    finally:
        ctypes.windll.kernel32.LocalFree(sid)
    return _net_names("NetLocalGroupGetMembers", name.value, wintypes.DWORD(3))


def accounts() -> list[str] | None:
    from ctypes import wintypes

    return _net_names("NetUserEnum", wintypes.DWORD(0), wintypes.DWORD(2))       # level 0, normal accounts


# --- sizes ------------------------------------------------------------------------------------------------------------

def _under_any(path: str, roots: list[str]) -> bool:
    p = os.path.normcase(os.path.normpath(path))
    return any(p == r or p.startswith(r.rstrip("\\/") + os.sep) for r in (os.path.normcase(os.path.normpath(x)) for x in roots))


def _from_index(state_path: str, folder: str) -> tuple[int, int] | None:
    """(bytes, files) under a folder, from what the watcher recorded (worker_client/snapshot.py): no walk. None when it has not made its first look."""
    import sqlite3

    from worker_client.snapshot import key

    try:
        db = sqlite3.connect(f"file:{state_path}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return None
    try:
        row = db.execute("SELECT value FROM meta WHERE name = 'baseline'").fetchone()
        if not (row and row[0]):
            return None
        prefix = key(folder).rstrip("/") + "/"
        size, count = db.execute("SELECT coalesce(sum(size), 0), count(*) FROM files WHERE substr(k, 1, ?) = ?", (len(prefix), prefix)).fetchone()
        return int(size), int(count)
    except sqlite3.Error:
        return None
    finally:
        db.close()


def place_sizes(places: list[dict[str, Any]], drive_mounts: list[str], system_root: str, busy: Callable[[], bool],
                watch_roots: list[str] | None = None, state_path: str | None = None) -> list[dict[str, Any]]:
    """Bytes and files under each place. A place inside the watched folders is summed from what the watcher already recorded (instant); the rest
    (Temp, the Recycle Bin, Windows Update's downloads, a place outside the watched folders) is walked within a budget, smallest kinds first, and
    stopped (marked partial) the moment someone is back."""
    targets = [("recycle_bin", "", d.rstrip("\\") + "\\$Recycle.Bin") for d in drive_mounts]
    targets.append(("windows_update", "", os.path.join(system_root, "SoftwareDistribution", "Download")))
    targets += [(p["kind"], p["user"], p["path"]) for p in sorted(places, key=lambda p: p["kind"] != "temp") if p["kind"] in SIZED and not p.get("guessed")]
    seen: set[str] = set()
    out, files_left, until = [], WALK_FILES, time.monotonic() + WALK_SECONDS
    walked_out = False
    for kind, user, path in targets:
        key = os.path.normcase(path)
        if key in seen or not os.path.isdir(path):
            continue
        seen.add(key)
        if state_path and watch_roots and _under_any(path, watch_roots):
            known = _from_index(state_path, path)
            if known is not None:
                out.append({"kind": kind, "user": user, "path": path, "bytes": known[0], "files": known[1], "partial": False, "from": "index"})
                continue
        if walked_out:
            continue                                       # the walk's budget is spent: what is left is only what the index can say
        size = count = 0
        partial = False
        stack = [path]
        while stack:
            if files_left <= 0 or time.monotonic() > until or (count % 500 == 0 and busy()):
                partial = True
                break
            try:
                with os.scandir(stack.pop()) as it:
                    for e in it:
                        try:
                            if e.is_dir(follow_symlinks=False):
                                stack.append(e.path)
                            elif e.is_file(follow_symlinks=False):
                                size += e.stat(follow_symlinks=False).st_size
                                count += 1
                                files_left -= 1
                        except OSError:
                            continue
            except OSError:
                continue
        out.append({"kind": kind, "user": user, "path": path, "bytes": size, "files": count, "partial": partial, "from": "walk"})
        walked_out = walked_out or partial
    return out


def drives() -> list[dict[str, Any]]:
    import psutil

    out = []
    for part in psutil.disk_partitions(all=False):
        if sys.platform == "win32" and "fixed" not in (part.opts or ""):
            continue                                       # a removable drive is the drive watch's; a CD has nothing to say
        try:
            u = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        out.append({"mount": part.mountpoint, "total": u.total, "free": u.free})
    return out


# --- the whole picture -------------------------------------------------------------------------------------------------

def take(reg: Registry | None = None, busy: Callable[[], bool] | None = None, watch_roots: list[str] | None = None,
         state_path: str | None = None) -> dict[str, Any]:
    reg = reg or WinRegistry()
    busy = busy or (lambda: not idle.is_idle(IDLE_FOR))
    system_root = str(reg.values("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion").get("SystemRoot") or r"C:\Windows")
    places = read_places(reg)
    parts = [
        _section("drives", drives),
        _section("admins", admins),
        _section("accounts", accounts),
        _section("startup", lambda: startup_entries(reg, places)),
        _section("services", lambda: services(reg)),
        _section("tasks", lambda: tasks(os.path.join(system_root, "System32", "Tasks"))),
        _section("programs", lambda: programs(reg)),
        _section("shares", lambda: shares(reg)),
        _section("defender", lambda: defender(reg)),
        _section("logs", lambda: log_sizes(system_root)),
    ]
    got = dict(p for p in parts if p is not None)
    if not busy():                                          # the walk only when nobody is at the machine
        sizes = _section("places", lambda: place_sizes(places, [d["mount"] for d in got.get("drives", [])], system_root, busy, watch_roots, state_path))
        if sizes is not None:
            got[sizes[0]] = sizes[1]
    return got


class Snapshots:
    """Takes the picture at every connect and every six hours, and sends it. `call` is the service's request to the Engine."""

    def __init__(self, call: Callable[[str, dict[str, Any]], Awaitable[Any]], taker: Callable[[], dict[str, Any]] | None = None) -> None:
        self._call = call
        self._take = taker
        self._loop: asyncio.Task[None] | None = None
        self.sent = 0

    async def send(self) -> bool:
        taker = self._take or (take if sys.platform == "win32" else None)
        if taker is None:
            return False
        picture = await asyncio.to_thread(taker)
        if not picture:
            return False
        try:
            await self._call("detective.snapshot", {"at": time.time(), "snapshot": picture})
        except (ConnectionError_, EngineError, OSError, asyncio.TimeoutError) as exc:     # the Engine was away or is older: the next one is sent later
            log.info("snapshot not sent: %s", exc)
            return False
        self.sent += 1
        return True

    async def connected(self) -> None:
        """Two minutes after the first connect (a machine that has just started settles first), then every six hours. A reconnect sends nothing
        new: the Engine keeps the last picture in its database, so there is nothing for it to forget."""
        if self._loop is None or self._loop.done():
            self._loop = asyncio.create_task(self._every())

    async def _every(self) -> None:
        wait = FIRST_AFTER
        while True:
            await asyncio.sleep(wait)
            wait = EVERY_SECONDS
            try:
                await self.send()
            except Exception:
                log.exception("the snapshot failed")

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
