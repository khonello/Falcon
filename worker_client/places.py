"""Each person's real Desktop, Documents, Downloads and the rest, read from the registry and told to the Engine (`index.places`; common/places.py).

The service runs with nobody signed in to it, so asking the shell for "my Desktop" would give the service's own. Instead, for every profile Windows
lists (HKLM ... ProfileList), the folders are read from that person's own hive, HKEY_USERS\\<SID>\\...\\User Shell Folders, with %USERPROFILE% and the
like expanded with THAT profile's paths, never the service's. A Desktop or Documents moved into OneDrive is read as it is. A profile whose hive is not
loaded (nobody signed in) gets the usual layout under its profile folder, marked `guessed`. The machine's own places (Windows, Program Files,
ProgramData, the all-users Startup, the system Temp) come from HKLM.

Sent at every connect and again whenever what is read changes (checked every ten minutes: a folder redirected, a new person signing in).
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from common.connection import ConnectionError_, EngineError
from common.places import MAX_PLACES, clean

log = logging.getLogger(__name__)

CHECK_SECONDS = 600.0
PROFILE_LIST = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
USER_SHELL = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
MACHINE_SHELL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
# value names in a person's User Shell Folders -> the place
USER_VALUES = {"Desktop": "desktop", "Personal": "documents", "{374DE290-123F-4565-9164-39C4925E467B}": "downloads", "My Pictures": "pictures",
               "My Video": "videos", "My Music": "music", "AppData": "appdata_roaming", "Local AppData": "appdata_local", "Startup": "startup"}
# what a profile nobody is signed in to usually has, under its folder
DEFAULTS = {"desktop": r"Desktop", "documents": r"Documents", "downloads": r"Downloads", "pictures": r"Pictures", "videos": r"Videos", "music": r"Music",
            "appdata_roaming": r"AppData\Roaming", "appdata_local": r"AppData\Local", "temp": r"AppData\Local\Temp",
            "startup": r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"}
PEOPLE = ("S-1-5-21-", "S-1-12-1-")         # a local or domain account; an Entra (Azure AD) account. Not the service accounts (S-1-5-18/19/20)


class Registry(Protocol):
    """What is read. `root` is "HKLM" or "HKU"; a missing key reads as nothing. Faked in the tests."""

    def values(self, root: str, key: str) -> dict[str, str]: ...

    def subkeys(self, root: str, key: str) -> list[str]: ...


class WinRegistry:
    def __init__(self) -> None:
        import winreg  # Windows only, and only when this is used

        self._w = winreg
        self._roots = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKU": winreg.HKEY_USERS}

    def values(self, root: str, key: str) -> dict[str, str]:
        w, out = self._w, {}
        try:
            with w.OpenKey(self._roots[root], key) as k:
                i = 0
                while True:
                    try:
                        name, value, _kind = w.EnumValue(k, i)
                    except OSError:
                        break
                    if isinstance(value, str):
                        out[name] = value
                    i += 1
        except OSError:
            pass
        return out

    def subkeys(self, root: str, key: str) -> list[str]:
        w, out = self._w, []
        try:
            with w.OpenKey(self._roots[root], key) as k:
                i = 0
                while True:
                    try:
                        out.append(w.EnumKey(k, i))
                    except OSError:
                        break
                    i += 1
        except OSError:
            pass
        return out


_VAR = re.compile(r"%([^%]+)%")


def expand(value: str, env: dict[str, str]) -> str:
    """%NAME% replaced from `env` (any case); a name it does not know is left as it is, so the place is not taken for somewhere else."""
    low = {k.lower(): v for k, v in env.items()}
    return _VAR.sub(lambda m: low.get(m.group(1).lower(), m.group(0)), value)


def _join(base: str, rest: str) -> str:
    return base.rstrip("\\/") + "\\" + rest


def _take(found: dict[str, str], env: dict[str, str], kind: str, value: str) -> None:
    path = expand(value, env) if value else ""
    if path and "%" not in path:                          # a name that could not be expanded: the usual place stands in, marked guessed
        found[kind] = path


def read(reg: Registry) -> list[dict[str, Any]]:
    """Every place of this machine and of each person on it."""
    out: list[dict[str, Any]] = []
    nt = reg.values("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
    cv = reg.values("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion")
    plist = reg.values("HKLM", PROFILE_LIST)
    system_root = nt.get("SystemRoot") or r"C:\Windows"
    machine_env = {"SystemRoot": system_root, "windir": system_root, "SystemDrive": system_root[:2]}
    program_data = expand(plist.get("ProgramData") or r"%SystemDrive%\ProgramData", machine_env)
    machine_env["ProgramData"] = machine_env["ALLUSERSPROFILE"] = program_data

    def add(kind: str, path: str, user: str = "", guessed: bool = False) -> None:
        if path and "%" not in path:
            out.append({"kind": kind, "path": path, "user": user, "guessed": guessed})

    add("windows", system_root)
    for name in ("ProgramFilesDir", "ProgramFilesDir (x86)"):
        add("program_files", expand(cv.get(name, ""), machine_env))
    add("programdata", program_data)
    common = reg.values("HKLM", MACHINE_SHELL)
    add("startup", expand(common.get("Common Startup") or _join(program_data, r"Microsoft\Windows\Start Menu\Programs\StartUp"), machine_env))
    session_env = reg.values("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
    add("temp", expand(session_env.get("TEMP") or _join(system_root, "Temp"), machine_env))

    loaded = {k.lower() for k in reg.subkeys("HKU", "")}
    for sid in reg.subkeys("HKLM", PROFILE_LIST):
        if not sid.startswith(PEOPLE) or sid.lower().endswith("_classes"):
            continue
        home = expand(reg.values("HKLM", PROFILE_LIST + "\\" + sid).get("ProfileImagePath", ""), machine_env)
        if not home:
            continue
        user = home.rstrip("\\/").replace("/", "\\").rsplit("\\", 1)[-1]
        env = {**machine_env, "USERPROFILE": home, "HOMEDRIVE": home[:2], "HOMEPATH": home[2:],
               "APPDATA": _join(home, r"AppData\Roaming"), "LOCALAPPDATA": _join(home, r"AppData\Local")}
        if sid.lower() not in loaded:
            for kind, rel in DEFAULTS.items():
                add(kind, _join(home, rel), user, guessed=True)
            continue
        shell = reg.values("HKU", sid + "\\" + USER_SHELL)
        found: dict[str, str] = {}
        for name in ("AppData", "Local AppData"):         # first: the Startup folder and Temp are written with %APPDATA% / %LOCALAPPDATA%
            _take(found, env, USER_VALUES[name], shell.get(name, ""))
        env["APPDATA"] = found.get("appdata_roaming", env["APPDATA"])
        env["LOCALAPPDATA"] = found.get("appdata_local", env["LOCALAPPDATA"])
        for name, kind in USER_VALUES.items():
            if name not in ("AppData", "Local AppData"):
                _take(found, env, kind, shell.get(name, ""))
        person_env = reg.values("HKU", sid + "\\Environment")
        _take(found, env, "temp", person_env.get("TEMP", ""))
        _take(found, env, "onedrive", person_env.get("OneDrive") or reg.values("HKU", sid + r"\Software\Microsoft\OneDrive").get("UserFolder", ""))
        for kind, rel in DEFAULTS.items():                # what the hive did not say is where Windows would put it
            if kind in found:
                add(kind, found[kind], user)
            else:
                add(kind, expand(_join(env["LOCALAPPDATA"], "Temp"), env) if kind == "temp" else _join(home, rel), user, guessed=True)
        if "onedrive" in found:
            add("onedrive", found["onedrive"], user)
    return clean(out)[:MAX_PLACES]


class PlacesReporter:
    """Reads the places when connected and tells the Engine what changed. `call` is the service's request to the Engine."""

    def __init__(self, call: Callable[[str, dict[str, Any]], Awaitable[Any]], reg: Registry | None = None) -> None:
        self._call = call
        self._reg = reg
        self.sent: list[dict[str, Any]] | None = None
        self._loop: asyncio.Task[None] | None = None

    def _registry(self) -> Registry | None:
        if self._reg is None and sys.platform == "win32":
            self._reg = WinRegistry()
        return self._reg

    async def send(self, *, force: bool = False) -> bool:
        reg = self._registry()
        if reg is None:
            return False                                 # not Windows: there is nothing of Windows' to tell
        places = await asyncio.to_thread(read, reg)
        if not places or (places == self.sent and not force):
            return False
        try:
            await self._call("index.places", {"places": places})
        except (ConnectionError_, EngineError, OSError, asyncio.TimeoutError) as exc:      # the Engine was away or is older: told again at the next connect
            log.info("places not told to the Engine: %s", exc)
            return False
        self.sent = places
        return True

    async def connected(self) -> None:
        """At every connect: tell them (a restarted Engine has forgotten), then keep watching for changes."""
        await self.send(force=True)
        if self._loop is None or self._loop.done():
            self._loop = asyncio.create_task(self._watch())

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(CHECK_SECONDS)
            try:
                await self.send()
            except Exception:
                log.exception("reading the places failed")

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
