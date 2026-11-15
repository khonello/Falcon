"""What tells one machine from another (stdlib only): used by a knocking PC (worker_client/knock.py) and by the Admin setup's claim
(installers/store_signin.py), which must name the PC the same way."""

from __future__ import annotations

import os
import uuid


def mac() -> str:
    n = uuid.getnode()
    return ":".join(f"{(n >> s) & 0xFF:02x}" for s in range(40, -1, -8))


def hardware_id() -> str:
    """Windows' own MachineGuid (or /etc/machine-id), with the network card: what tells this machine from another that took its name."""
    ident = ""
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                                winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)) as key:
                ident = str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except OSError:
            ident = ""
    else:
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                with open(path, encoding="ascii") as f:
                    ident = f.read().strip()
                break
            except OSError:
                continue
    return f"{ident or 'unknown'}/{mac()}"
