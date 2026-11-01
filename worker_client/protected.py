"""What the Worker never ends and never lists as something to end (ENGINE-GAPS #9): Windows' own processes, what runs as the machine's
service accounts, and the Worker itself (its service, its supervised parts, and whatever it started).

Used by the process snapshot (`inventory.processes`, so a console never offers them) and by the `kill_process` built-in, which refuses
them even when asked directly by name or pid.
"""

from __future__ import annotations

from typing import Any

# Windows' own processes: ending any of these takes the session or the machine down.
SYSTEM_NAMES = frozenset({
    "system", "system idle process", "idle", "registry", "memory compression", "secure system", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "lsaiso.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe",
    "sihost.exe", "ctfmon.exe", "taskhostw.exe", "runtimebroker.exe", "spoolsv.exe", "audiodg.exe", "conhost.exe",
    "msmpeng.exe", "nissrv.exe", "securityhealthservice.exe", "explorer.exe", "userinit.exe", "logonui.exe", "wudfhost.exe",
})
# What the machine itself runs: the service accounts, never a person.
SYSTEM_USERS = frozenset({"system", "local service", "network service", "localsystem"})
# The Worker runs under one of these (a venv's python, or the frozen executable once packaged).
_OWN_PREFIXES = ("python", "falcon")


def falcon_pids() -> set[int]:
    """This process, the processes above it, and everything below the outermost Worker process above it: the Worker's service, its
    indexer and tracker, and the scripts it runs."""
    try:
        import psutil
    except ImportError:
        return set()
    try:
        me = psutil.Process()
        chain = [me, *me.parents()]
    except (psutil.Error, OSError):
        return set()
    pids = {p.pid for p in chain}
    root = None
    for p in chain:
        try:
            if p.name().lower().startswith(_OWN_PREFIXES):
                root = p
        except (psutil.Error, OSError):
            continue
    if root is not None:
        try:
            pids |= {c.pid for c in root.children(recursive=True)}
        except (psutil.Error, OSError):
            pass
    return pids


def is_protected(pid: int, name: str | None, username: str | None, own: set[int]) -> bool:
    if pid in (0, 4) or pid in own:
        return True
    if (name or "").lower() in SYSTEM_NAMES:
        return True
    user = (username or "").split("\\")[-1].lower()
    return user in SYSTEM_USERS


def why(info: dict[str, Any], own: set[int]) -> str:
    if info.get("pid") in own:
        return "it is part of Falcon"
    if (info.get("name") or "").lower() in SYSTEM_NAMES:
        return "Windows needs it"
    return "it runs as the machine itself"
