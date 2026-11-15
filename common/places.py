"""Windows' own places: Desktop, Documents, Downloads and the rest, for each person on a machine (docs/design/proposals-core-features.md, item 2).

A path alone does not say what a place is: a Desktop can live in OneDrive, a profile on another drive, Documents be called "Dokumente". The Worker reads
each profile's real folders from the registry (`worker_client/places.py`) and sends them; the Engine keeps them per machine (`engine/places.py`) and gives
every file event its place before Detective reads it. Where nothing was sent, `guess` reads the usual layout out of the path, and says it guessed.

    Place(kind, user, guessed)    kind is one of KINDS; user is the profile's folder name ("" for a place of the machine's)

Stdlib only: bundled by every package.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

# A person's own places: where their work lives. Moving a file between two of these, inside one profile, is filing.
PERSONAL = ("desktop", "documents", "downloads", "pictures", "videos", "music", "onedrive")
# Places nobody looks in: a document put here is out of sight.
OUT_OF_SIGHT = ("appdata_roaming", "appdata_local", "temp", "recycle_bin", "windows", "program_files", "programdata")
# Places whose files run by themselves at sign-in.
RUNS_AT_SIGN_IN = ("startup",)
KINDS = PERSONAL + OUT_OF_SIGHT + RUNS_AT_SIGN_IN

WORDS = {"desktop": "Desktop", "documents": "Documents", "downloads": "Downloads", "pictures": "Pictures", "videos": "Videos", "music": "Music",
         "onedrive": "OneDrive", "appdata_roaming": "AppData (Roaming)", "appdata_local": "AppData (Local)", "temp": "Temp", "recycle_bin": "the Recycle Bin",
         "windows": "Windows", "program_files": "Program Files", "programdata": "ProgramData", "startup": "Startup"}

MAX_PLACES = 400                               # what one machine may send (a machine with many profiles: ~15 each)


@dataclass(frozen=True)
class Place:
    kind: str
    user: str = ""
    guessed: bool = False

    @property
    def personal(self) -> bool:
        return self.kind in PERSONAL

    @property
    def out_of_sight(self) -> bool:
        return self.kind in OUT_OF_SIGHT

    def words(self) -> str:
        where = WORDS.get(self.kind, self.kind)
        return f"{self.user}'s {where}" if self.user and self.kind in PERSONAL + RUNS_AT_SIGN_IN else where


def norm(path: str) -> str:
    """One spelling of a Windows path: backslashes, lower case, no trailing separator."""
    p = str(path or "").replace("/", "\\").lower()
    while len(p) > 3 and p.endswith("\\"):
        p = p[:-1]
    return p


def _under(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder + "\\")


class Places:
    """The places of one machine, as its Worker said. `of(path)` is the deepest place the path is in (AppData\\Local\\Temp is Temp, not AppData)."""

    def __init__(self, entries: Iterable[dict[str, Any]] = ()) -> None:
        self._by: list[tuple[str, Place]] = []
        self._said: dict[str, str] = {}                  # the folder as the Worker wrote it, for showing
        for e in entries:
            said = str(e.get("path") or "")
            kind, path = str(e.get("kind") or ""), norm(said)
            if kind in KINDS and len(path) >= 3:
                self._by.append((path, Place(kind, str(e.get("user") or ""), bool(e.get("guessed")))))
                self._said[path] = said
        self._by.sort(key=lambda x: -len(x[0]))         # deepest first

    def __len__(self) -> int:
        return len(self._by)

    def of(self, path: str) -> Place | None:
        p = norm(path)
        if not p:
            return None
        for folder, place in self._by:
            if _under(p, folder):
                return place
        return guess(path)

    def entries(self) -> list[dict[str, Any]]:
        return [{"kind": pl.kind, "path": self._said.get(folder, folder), "user": pl.user, "guessed": pl.guessed}
                for folder, pl in sorted(self._by, key=lambda x: (x[1].user, x[0]))]


# The usual layout, for a machine that has not said (an older Worker), a path from before, or a profile nobody is signed in to.
_PROFILE_DIRS = {"desktop": "desktop", "documents": "documents", "downloads": "downloads", "pictures": "pictures", "videos": "videos", "music": "music",
                 "onedrive": "onedrive"}


def guess(path: str) -> Place | None:
    """What the path itself says, by the usual layout. Marked `guessed`."""
    p = norm(path)
    if not p:
        return None
    parts = p.split("\\")
    if len(parts) >= 2 and parts[1] == "$recycle.bin":
        return Place("recycle_bin", "", True)
    if len(parts) >= 4 and parts[1] == "users":
        user, top = parts[2], parts[3]
        if user in ("public", "default", "all users"):
            user = ""
        rest = parts[4:]
        if top == "appdata" and rest:
            if rest[0] == "local" and len(rest) > 1 and rest[1] == "temp":
                return Place("temp", user, True)
            if rest[0] == "roaming" and rest[1:5] == ["microsoft", "windows", "start menu", "programs"] and len(rest) > 5 and rest[5] == "startup":
                return Place("startup", user, True)
            return Place("appdata_local" if rest[0] in ("local", "locallow") else "appdata_roaming", user, True)
        if top.startswith("onedrive"):                  # "OneDrive", "OneDrive - Company"
            if rest and rest[0] in ("desktop", "documents", "pictures"):
                return Place(rest[0], user, True)
            return Place("onedrive", user, True)
        if top in _PROFILE_DIRS:
            return Place(_PROFILE_DIRS[top], user, True)
        return None
    if len(parts) >= 2:
        top = parts[1]
        if top == "windows":
            return Place("temp" if len(parts) > 2 and parts[2] == "temp" else "windows", "", True)
        if top in ("program files", "program files (x86)"):
            return Place("program_files", "", True)
        if top == "programdata":
            if parts[2:7] == ["microsoft", "windows", "start menu", "programs", "startup"]:
                return Place("startup", "", True)
            return Place("programdata", "", True)
        if top in ("temp", "tmp"):
            return Place("temp", "", True)
    return None


def clean(entries: Any) -> list[dict[str, Any]]:
    """What a Worker sent, kept to what is understood and bounded."""
    out: list[dict[str, Any]] = []
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict):
            continue
        kind, path = str(e.get("kind") or ""), str(e.get("path") or "")[:400]
        if kind in KINDS and len(path) >= 3:
            out.append({"kind": kind, "path": path, "user": str(e.get("user") or "")[:120], "guessed": bool(e.get("guessed"))})
        if len(out) >= MAX_PLACES:
            break
    return out
