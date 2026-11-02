"""Private items on this machine: Windows itself refuses anyone not named (engine/resource/private.py; the user, 2 Nov 2026: "established
mechanisms").

    private.apply {mark_id, path, kind, readers: [Windows names], owner, allow_system} -> private.applied {mark_id, ok, granted, missing, error?}
    private.lift  {mark_id, path}                                                        -> the permissions it had before are put back
    and, while there is anything private here: Windows' audit of failed opens is read, and each refusal is said (private.refused)

How, with Windows' own tools only (icacls, the Security log, auditpol, PowerShell's Set-Acl for the audit rule):
  1. the item's permissions as they are now are saved once (`icacls <item> /save`), to be put back exactly when it stops being private;
  2. its permissions become: the people named (and the owner) may open and change it; the system account may too when the owner allows it,
     and otherwise keeps only the right to read and change the permissions themselves, so Falcon can always undo it; nobody else may;
  3. failed opens of it are audited (a failure audit rule on the item, and "File System" failure auditing switched on), so Windows writes
     who was refused into its Security log (event 4656), which `RefusalReader` reads.
A person whose Windows name does not exist on this machine is reported as missing and left out; if nobody named can be found, nothing is
changed (an item nobody can open is worse than one that is not private yet).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

AUDIT_FAILURE = 0x10000000000000                  # the Security log's "Audit Failure" keyword


def windows() -> bool:
    return os.name == "nt"


def signed_in_user() -> str | None:
    """The person signed in at this machine, as Windows names them (the service itself runs as the system account)."""
    try:
        import psutil

        people = [u for u in psutil.users() if u.name]
        if people:
            return min(people, key=lambda u: u.started or 0).name
    except (ImportError, OSError):
        pass
    return None


def _run(argv: list[str]) -> tuple[int, str]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    done = subprocess.run(argv, capture_output=True, text=True, creationflags=flags, check=False)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


class Privacy:
    def __init__(self, state_dir: Path, *, audit: bool = True) -> None:
        self.state_dir = Path(state_dir)
        self.audit = audit                           # (tests) leave the machine's audit policy and the item's audit rule alone
        self.paths: dict[int, str] = self._load()    # mark id -> path, while private here

    def _index(self) -> Path:
        return self.state_dir / "private.json"

    def _load(self) -> dict[int, str]:
        try:
            return {int(k): str(v) for k, v in json.loads(self._index().read_text(encoding="utf-8")).items()}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._index().write_text(json.dumps({str(k): v for k, v in self.paths.items()}), encoding="utf-8")

    def _acl_file(self, mark_id: int) -> Path:
        return self.state_dir / f"private-{mark_id}.acl"

    def apply(self, order: dict[str, Any]) -> dict[str, Any]:
        mark_id, path = int(order["mark_id"]), str(order["path"])
        result: dict[str, Any] = {"mark_id": mark_id, "ok": False, "granted": [], "missing": []}
        if not windows():
            result["error"] = "Private is Windows' own permissions: this machine is not Windows"
            return result
        item = Path(path)
        if not item.exists():
            result["error"] = "it is not there any more"
            return result
        folder = item.is_dir()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        saved = self._acl_file(mark_id)
        if not saved.exists():
            code, out = _run(["icacls", str(item), "/save", str(saved), "/Q"])
            if code != 0:
                result["error"] = f"its permissions could not be saved first: {out.strip()[:200]}"
                return result
        names = list(dict.fromkeys([n for n in [order.get("owner"), *(order.get("readers") or [])] if n]))
        rights = "(OI)(CI)M" if folder else "M"
        code, out = _run(["icacls", str(item), "/reset", "/Q"])
        code2, out2 = _run(["icacls", str(item), "/inheritance:r", "/Q"])
        if code or code2:
            self._restore(mark_id, item)
            result["error"] = f"its permissions could not be changed: {(out or out2).strip()[:200]}"
            return result
        system = "SYSTEM:(OI)(CI)F" if folder else "SYSTEM:F"
        if not order.get("allow_system", True):
            system = "SYSTEM:(RC,WDAC)"                      # not to read it, only to put its permissions back
        _run(["icacls", str(item), "/grant:r", system, "/Q"])
        for name in names:
            code, out = _run(["icacls", str(item), "/grant:r", f"{name}:{rights}", "/Q"])
            (result["granted"] if code == 0 else result["missing"]).append(name)
        if not result["granted"]:
            self._restore(mark_id, item)
            result["error"] = "none of the people named is known on this machine: nothing was changed"
            return result
        if self.audit:
            self._audit_failures(item, folder)
        self.paths[mark_id] = str(item)
        self._save()
        result["ok"] = True
        return result

    def lift(self, mark_id: int, path: str) -> bool:
        ok = self._restore(mark_id, Path(path))
        self.paths.pop(mark_id, None)
        self._save()
        return ok

    def _restore(self, mark_id: int, item: Path) -> bool:
        saved = self._acl_file(mark_id)
        if not windows() or not saved.exists():
            return False
        code, out = _run(["icacls", str(item.parent), "/restore", str(saved), "/Q"])
        if code != 0:
            log.warning("private: the permissions of %s could not be put back: %s", item, out.strip()[:200])
            return False
        saved.unlink(missing_ok=True)
        return True

    @staticmethod
    def _audit_failures(item: Path, folder: bool) -> None:
        """Windows writes each refused open of the item into its Security log (event 4656): a failure audit rule on the item, and failure
        auditing of the file system switched on for the machine."""
        _run(["auditpol", "/set", "/subcategory:{0CCE921D-69AE-11D9-BED3-505054503030}", "/failure:enable"])     # "File System"
        inherit = "'ContainerInherit,ObjectInherit'" if folder else "'None'"
        script = ("$p = $args[0]; $a = Get-Acl -LiteralPath $p -Audit; "
                  f"$r = New-Object System.Security.AccessControl.FileSystemAuditRule('Everyone', 'ReadData,ExecuteFile', {inherit}, 'None', 'Failure'); "
                  "$a.AddAuditRule($r); Set-Acl -LiteralPath $p -AclObject $a")
        _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script, str(item)])


class RefusalReader:
    """Reads Windows' audit of failed opens (Security log, event 4656) for the items private here, from where it last read."""

    def __init__(self) -> None:
        self.last_record = 0

    def read(self, private_paths: list[str]) -> list[dict[str, Any]]:
        if not windows() or not private_paths:
            return []
        query = "*[System[(EventID=4656) and band(Keywords,4503599627370496)" + (f" and (EventRecordID > {self.last_record})" if self.last_record else "") + "]]"
        code, out = _run(["wevtutil", "qe", "Security", f"/q:{query}", "/f:xml", "/c:200", "/rd:false"])
        if code != 0:
            return []
        found, newest = parse_refusals(out, private_paths)
        if newest:
            self.last_record = max(self.last_record, newest)
        return found


def parse_refusals(xml_text: str, private_paths: list[str]) -> tuple[list[dict[str, Any]], int]:
    """The failed opens in a Security log query whose object is one of the private items (or under a private folder): [{path, who, process, at}]
    and the newest record id read."""
    under = [p.replace("/", "\\").rstrip("\\").lower() for p in private_paths]
    out: list[dict[str, Any]] = []
    newest = 0
    for chunk in re.findall(r"<Event[\s>].*?</Event>", xml_text, flags=re.DOTALL):
        try:
            ev = ET.fromstring(re.sub(r'\sxmlns="[^"]+"', "", chunk, count=1))
        except ET.ParseError:
            continue
        record = int(ev.findtext("System/EventRecordID") or 0)
        newest = max(newest, record)
        data = {d.get("Name"): (d.text or "") for d in ev.findall("EventData/Data")}
        obj = data.get("ObjectName", "")
        low = obj.replace("/", "\\").lower()
        if not any(low == p or low.startswith(p + "\\") for p in under):
            continue
        who = data.get("SubjectUserName", "")
        domain = data.get("SubjectDomainName", "")
        created = ev.find("System/TimeCreated")
        out.append({"path": obj, "who": f"{domain}\\{who}" if domain and who else who, "process": data.get("ProcessName") or None,
                    "at": created.get("SystemTime") if created is not None else None})
    return out, newest
