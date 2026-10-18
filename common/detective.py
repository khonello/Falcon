"""Detective: what a person seems to be trying to do, read from several small things happening together.

Not "this event, so do that". The system watches what happens to files, programs and drives on a machine and asks what a person would be doing for
it to look that way. The vocabulary is human:

    BEHAVIOURS   concealment (making something hard to find or recognise), collection (gathering things in one place), exfiltration (getting it off the
                 machine), capture (taking the information without the file), erasure (removing the evidence), evasion (slipping the watch),
                 sabotage (destroying, not taking), reach (looking where one has no business)
    MINI-GRAPHS  each behaviour owns a few small patterns. A pattern has a SPARK (the one event that starts it) and looks back and forward over a time
                 window for the supporting steps; it is only evaluated when its spark appears, so it is cheap.
    FINDING      what one mini-graph concluded: a behaviour, a weight, the evidence, and what would make it innocent.
    CASE         findings about the same person/machine/files collected under one hypothesis, an INTENT ("taking data out", "covering up", ...), with the
                 STAGE it has reached ("collected and hidden, not yet taken out") and what usually comes next. The verdict is the case's, never one graph's.

How it speaks: it states a pattern and shows its evidence, never an accusation and never a cause. Context lowers or raises weight (a task for that file, a
flow that wrote it, an allowance, a drive that is always used); the time of day is context, never a trigger; Falcon's own work is ignored entirely.

Provenance (`Sig.by`) says who made a change when that is known: "hand" (input happened just before, in the program doing it), "started" (a program the
person started), "alone" (a program on its own), "falcon" (a flow or an action), "unknown" (not yet observed). It is a weight, never a verdict.

Stdlib only: it runs on a Worker or in the Engine, and is tested with scripted scenarios (scripts/detective_scenarios.py).
"""

from __future__ import annotations

import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from common.anchors import ANCHORS, INCLUDES, coverage

BEHAVIOURS = ("concealment", "collection", "exfiltration", "capture", "erasure", "evasion", "sabotage", "reach")
BEHAVIOUR_WORDS = {"concealment": "Concealment", "collection": "Collection", "exfiltration": "Taking out", "capture": "Capture", "erasure": "Erasure",
                   "evasion": "Evasion", "sabotage": "Sabotage", "reach": "Reach"}

# the order a taking-out usually runs in, so a case can say how far along it is and what usually follows
ARC_STAGES = (("Reaching", ("reach",)), ("Gathering", ("collection",)), ("Hiding", ("concealment",)), ("Taking out", ("exfiltration", "capture")),
              ("Covering up", ("erasure", "evasion")))

NOTED, CASE, URGENT = 0.35, 0.60, 0.85       # weights: kept quietly; shown as a case; shown first and to the Super User as well

WINDOW = 15 * 60                              # how far back/forward a mini-graph looks for its supporting steps
SESSION = 2 * 3600                            # findings on one machine this close together are one sitting
PATIENT = 7 * 86400                           # ... and a later step of the same arc on the same machine can still join an earlier case
KEEP = 6 * 3600                               # how much recent activity a machine's memory holds

DOC_EXT = {"doc", "docx", "xls", "xlsx", "csv", "pdf", "ppt", "pptx", "txt", "rtf", "odt", "ods", "md", "json"}
SYSTEMISH_EXT = {"dll", "sys", "exe", "tmp", "dat", "bin", "scr", "js", "vbs", "bat", "cab", "ini", "db", "bak"}
ARCHIVE_EXT = {"zip", "7z", "rar", "tar", "gz", "tgz", "bz2", "xz", "cab"}
MEDIA_EXT = {"jpg", "jpeg", "png", "gif", "bmp", "heic", "webp", "svg", "mp3", "m4a", "wav", "flac", "ogg", "mp4", "mkv", "mov", "avi", "webm"}
_DOUBLE = re.compile(r"\.(docx?|xlsx?|pdf|pptx?|csv|txt)\.(exe|scr|dll|js|vbs|bat|tmp|dat|sys)$", re.IGNORECASE)
_SYSTEM_DIRS = ("\\windows\\", "\\program files", "\\programdata\\", "\\appdata\\", "\\temp\\", "\\$recycle.bin\\", "\\system volume information\\",
                "/windows/", "/programdata/", "/tmp/", "/var/", "/proc/", "/etc/")

# programs whose job is to take a picture or a recording of the screen: a person using one while working on restricted files is taking the information without the file
CAPTURE_TOOLS = ("snippingtool.exe", "screenclippinghost.exe", "snip.exe", "sharex.exe", "lightshot.exe", "greenshot.exe", "snagit32.exe", "snagiteditor.exe",
                 "screenpresso.exe", "bandicam.exe", "camtasia.exe", "obs64.exe", "picpick.exe", "flameshot.exe")

# programs that move data around for a living: they lower a taking-out finding (a backup is not a theft) unless something else says otherwise
USUAL_MOVERS = ("git.exe", "msbuild", "nuget", "npm", "docker", "curl.exe", "slack", "robocopy", "backup", "veeam", "acronis", "syncthing", "onedrive", "dropbox", "rsync", "7zg", "windowssearch", "googledrivefs", "backblaze", "crashplan",
                "teams", "zoom")


HIT_KEEP = 30 * 86400                         # how long what fell in an area stays on the board: a patient person covers it slowly
THREAD = 30 * 60                              # stages this close together are one piece of work even with no file in common
ENC_EXT = {"gpg", "pgp", "enc", "aes", "crypt", "kdbx", "vault", "hc"}                  # (ransom endings like .locked are the sabotage graph's)
BACKUP_EXT = {"bak", "bkf", "vhd", "vhdx", "wbcat", "vss", "tib", "bkp", "rbf"}
IMAGE_EXT = {"jpg", "jpeg", "png", "bmp", "gif", "webp", "mp4", "mkv", "avi", "mov", "webm"}
VALUABLE_EXT = DOC_EXT | ARCHIVE_EXT | {"db", "mdb", "accdb", "sql", "pst", "ost", "kdbx", "vsd", "dwg", "psd"}
# words in a name or a place that say a thing matters, whether or not anyone marked it
WORTH_WORDS = frozenset({"contract", "audit", "ledger", "payroll", "salary", "invoice", "legal", "board", "tax", "passport", "confidential", "secret", "personnel",
                         "customer", "client", "master", "budget", "merger", "acquisition", "password", "credential", "finance", "compliance", "hr", "director", "ceo"})


def names_something_that_matters(path: str) -> bool:
    """A whole word of the name or the place says it matters (not a stretch of letters inside another word, and not the person's own profile folder's name)."""
    parts = [p for p in re.split(r"[\\/]+", path.lower()) if p]
    if "users" in parts:
        i = parts.index("users")
        parts = parts[:i] + parts[i + 2:]                              # (the folder named after a person is not a place that matters)
    for part in parts:
        for token in re.split(r"[^a-z]+", part):
            if token in WORTH_WORDS or (len(token) > 3 and token.endswith("s") and token[:-1] in WORTH_WORDS) or (token.endswith("ies") and token[:-3] + "y" in WORTH_WORDS):
                return True
    return False
BEHAVIOUR_LABEL = {"exfiltration": "Taking out", "collection": "Gathering", "concealment": "Hiding", "erasure": "Covering up", "capture": "Capturing",
                   "evasion": "Slipping the watch", "sabotage": "Wrecking", "reach": "Looking where they should not"}
# the anchor each existing mini-graph is a reading of, so a case can show the board whatever made the finding
GRAPH_ANCHOR: dict[str, tuple[str, str]] = {
    "gathering": ("exfiltration", "Gather"), "archived": ("exfiltration", "Compress"), "to_drive": ("exfiltration", "Transfer"),
    "drive_after_staging": ("exfiltration", "Transfer"), "uploaded": ("exfiltration", "Transfer"), "hidden": ("concealment", "Disguise"),
    "disguised": ("concealment", "Disguise"), "buried": ("concealment", "Relocate"), "removed_after_taking": ("erasure", "Remove"),
    "mass_removal": ("erasure", "Remove"), "history_cleared": ("erasure", "Clear the trail"), "capture_tool": ("capture", "Capture"),
    "clipboard_picture": ("capture", "Capture"), "flow_bypass": ("exfiltration", "Transfer"), "went_silent": ("evasion", "Switch off"), "bulk_destroyed": ("sabotage", "Destroy"),
    "bulk_rewritten": ("sabotage", "Destroy"), "scrambled_names": ("sabotage", "Destroy"), "outside_role": ("reach", "Beyond role"),
}


def ext_of(path: str) -> str:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def name_of(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def folder_of(path: str) -> str:
    p = path.replace("\\", "/")
    return p.rsplit("/", 1)[0] if "/" in p else ""


def is_system_folder(path: str) -> bool:
    low = "\\" + path.lower().replace("/", "\\") if not path.lower().startswith(("c:", "d:")) else path.lower().replace("/", "\\")
    return any(d.replace("/", "\\") in low for d in _SYSTEM_DIRS)


def megabytes(n: Any) -> str:
    try:
        mb = float(n) / 1_000_000
    except (TypeError, ValueError):
        return "a lot of data"
    return f"{mb / 1000:.1f} GB" if mb >= 1000 else f"{mb:.0f} MB"


def kind_factor(path: str, tags: frozenset[str] = frozenset()) -> float:
    """How much a file of this kind can matter before anything else is known about it. Documents, data and archives (which can hold anything) count fully; photographs,
    music, programs and temporary files count for little (a person's own photographs on a drive are not what this is for) unless something marks them as mattering."""
    if "restricted" in tags:
        return 1.0
    ext = ext_of(path)
    if ext in VALUABLE_EXT:
        return 1.0
    if not ext:
        return 0.6
    return 0.35


def _same_profile(a: str, b: str) -> bool:
    """Both places are inside the same person's profile folder (under a Users folder)."""
    def user(p: str) -> str:
        parts = p.lower().replace("/", "\\").split("\\")
        return parts[2] if len(parts) > 3 and parts[1] == "users" else ""
    ua, ub = user(a), user(b)
    return bool(ua) and ua == ub


def is_archive(path: str) -> bool:
    return ext_of(path) in ARCHIVE_EXT


def disguised(old: str, new: str) -> bool:
    """A name changed so that the thing looks like something it is not: a document made to look like a system file, or given a second extension."""
    if not old or not new:
        return False
    before, after = ext_of(old), ext_of(new)
    if before in DOC_EXT and (after in SYSTEMISH_EXT or after in MEDIA_EXT or after in ARCHIVE_EXT):
        return True                                                # a document that now looks like a system file, a picture, a song or an archive
    return bool(_DOUBLE.search(name_of(new)) and not _DOUBLE.search(name_of(old)))


@dataclass(frozen=True)
class Sig:
    """One thing that happened, as the detector reads it. `verb` is one of: created modified renamed moved copied deleted opened hid unhid permissions
    attached detached launched exited captured uploaded cleared silent. `thing` follows the file (its content hash or identity); `device` is a drive's own name."""
    at: float
    pc: int
    verb: str
    path: str = ""
    old: str = ""
    thing: str = ""
    program: str = ""
    by: str = "unknown"
    device: str = ""
    tags: frozenset[str] = frozenset()
    info: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def name(self) -> str:
        return name_of(self.path) or self.device or self.program

    def phrase(self) -> str:
        said = self._phrase()
        title = str(self.info.get("title") or "")
        return f"{said} (in \"{title}\")" if title and self.verb not in ("attached", "detached", "launched", "exited", "cleared", "silent", "captured") else said

    def _phrase(self) -> str:
        n = self.name
        return {"created": f"created {n}", "modified": f"changed {n}", "renamed": f"renamed {name_of(self.old)} to {n}", "moved": f"moved {n} to {folder_of(self.path) or 'another place'}",
                "copied": f"copied {n} to {folder_of(self.path) or 'another place'}", "deleted": f"deleted {n}", "opened": f"opened {n}", "hid": f"hid {n}",
                "unhid": f"made {n} visible", "permissions": f"changed who may open {n}", "attached": f"plugged in a drive ({self.info.get('label') + ', ' if self.info.get('label') else ''}{self.device})",
                "detached": f"removed a drive ({self.device})", "uploaded": f"sent {megabytes(self.info.get('bytes'))} out over the network ({self.program or 'a program'})", "launched": f"started {self.program}", "exited": f"closed {self.program}",
                "captured": ("took a picture of the whole screen" if self.info.get("kind") == "screen" else "put a picture on the clipboard" if self.info.get("kind") == "region"
                             else f"captured the screen ({self.program or 'a tool'})") + (f" ({self.program})" if self.info.get("kind") and self.program else ""), "cleared": f"cleared {self.info.get('what') or 'a history'}",
                "silent": "stopped reporting while still switched on"}.get(self.verb, f"{self.verb} {n}")


def sig_to_dict(x: Sig) -> dict[str, Any]:
    return {"at": x.at, "pc": x.pc, "verb": x.verb, "path": x.path, "old": x.old, "thing": x.thing, "program": x.program, "by": x.by, "device": x.device,
            "tags": sorted(x.tags), "info": x.info, "text": x.phrase()}


def sig_from_dict(d: dict[str, Any]) -> Sig:
    return Sig(float(d["at"]), int(d["pc"]), str(d["verb"]), str(d.get("path") or ""), str(d.get("old") or ""), str(d.get("thing") or ""), str(d.get("program") or ""),
               str(d.get("by") or "unknown"), str(d.get("device") or ""), frozenset(d.get("tags") or ()), dict(d.get("info") or {}))


@dataclass
class Finding:
    behaviour: str
    graph: str
    at: float
    pc: int
    weight: float
    things: frozenset[str]
    summary: str
    evidence: list[Sig]
    innocent: str                                  # what would make this harmless
    why: list[str] = field(default_factory=list)   # what raised or lowered the weight, in words

    @property
    def reads_as(self) -> str:
        """The behaviour this finding counts as when a case works out how far an arc has got. Coverage of taking-out areas with nothing in the area where it
        leaves is still gathering: it must not say "taken out" before anything has gone."""
        if self.graph.startswith("coverage_") and self.weight < NOTED:
            return ""                                  # light coverage is on the board but names no intent
        if self.graph == "coverage_exfiltration":
            areas = {a for x in self.why if x.startswith("areas covered: ") for a in x[len("areas covered: "):].split(", ")}
            if "Transfer" not in areas:
                return "collection" if areas & {"Gather", "Compress"} else ""      # only reshaping, nothing gathered or packed: not yet a taking-out
        return self.behaviour


@dataclass(frozen=True)
class Hit:
    """One event falling in one area (anchor) of one intent, with the weight of that event on its own."""
    behaviour: str
    anchor: str
    at: float
    weight: float
    things: frozenset[str]
    sig: Sig


@dataclass
class Case:
    pc: int
    findings: list[Finding] = field(default_factory=list)
    id: int | None = None
    first_at: float = 0.0
    last_at: float = 0.0

    @property
    def behaviours(self) -> set[str]:
        return {f.reads_as for f in self.findings} - {""}

    @property
    def things(self) -> set[str]:
        out: set[str] = set()
        for f in self.findings:
            out |= f.things
        return out

    @property
    def weight(self) -> float:
        """Several independent hints are stronger together than any one: 1 - the chance every one of them is nothing, plus a little for each further kind of behaviour."""
        # The same reading made again and again (the tenth file copied to the same drive) is a count, and a count only amplifies: a graph speaks at its heaviest,
        # with a little added for each further time it spoke, never a new vote each time.
        by_graph: dict[str, list[float]] = {}
        for f in self.findings:
            if not f.graph.startswith("coverage_"):
                by_graph.setdefault(f.graph, []).append(min(0.95, f.weight))
        rest = 1.0
        for ws in by_graph.values():
            top = max(ws)
            rest *= 1.0 - (top + (1.0 - top) * (0.08 if top >= 0.5 else 0.03) * min(len(ws) - 1, 6))      # a count amplifies a heavy reading, and barely a light one
        # Coverage (what falls in an intent's areas on one piece of work) is a reading of the very same events the other findings are readings of, so it does not stack with
        # them: it is a floor under the case, and what makes a case when no single graph fires.
        core = max(1.0 - rest, max((f.weight for f in self.findings if f.graph.startswith("coverage_")), default=0.0))
        firm = {f.reads_as for f in self.findings if f.weight >= 0.30} - {""}          # a second kind of behaviour adds weight only when it is firm in itself
        return min(0.99, core + 0.06 * max(0, len(firm) - 1))

    @property
    def level(self) -> str:
        w = self.weight
        return "urgent" if w >= URGENT else "case" if w >= CASE else "noted" if w >= NOTED else "quiet"

    @property
    def intent(self) -> str:
        b = self.behaviours
        if "sabotage" in b:
            return "Wrecking things"
        if "exfiltration" in b or ("collection" in b and ("concealment" in b or "capture" in b)):
            return "Taking data out"
        if "capture" in b and "reach" in b:
            return "Spying"
        if b <= {"erasure", "evasion"} and b:
            return "Covering up" if "erasure" in b else "Slipping the watch"
        if "concealment" in b and "erasure" in b:
            return "Covering up"
        if "capture" in b:
            return "Copying what is on screen"
        if "collection" in b:
            return "Gathering"
        if "reach" in b:
            return "Looking where they should not"
        return "Hiding something" if "concealment" in b else "Unusual activity"

    @property
    def stage(self) -> tuple[int, str, str | None]:
        """(how many of the five stages of a taking-out have shown, the latest one's name, what usually comes next)."""
        seen = [i for i, (_, bs) in enumerate(ARC_STAGES) if self.behaviours & set(bs)]
        if not seen:
            return 0, "", None
        top = max(seen)
        nxt = ARC_STAGES[top + 1][0] if top + 1 < len(ARC_STAGES) else None
        return len(seen), ARC_STAGES[top][0], nxt

    def not_yet(self) -> str | None:
        """The step that has not happened, said plainly, when everything up to it has."""
        b = self.behaviours
        if self.intent != "Taking data out":
            return None
        if not b & {"exfiltration", "capture"}:
            return "It has not left the machine yet."
        if "erasure" not in b:
            return "Nothing has been erased yet."
        return None

    def board(self) -> list[dict[str, Any]]:
        """The areas of each intent this case touches, and which have something in them: [{behaviour, label, covered, of, areas: [{name, says, seen, covered}]}].
        Areas are coverage, not steps: no order, none required."""
        covered: dict[str, set[str]] = {}
        for f in self.findings:
            if f.graph.startswith("coverage_"):
                for line in f.why:
                    if line.startswith("areas covered: "):
                        for x in line[len("areas covered: "):].split(", "):
                            b, _, a = x.partition("/") if "/" in x else (f.behaviour, "", x)
                            covered.setdefault(b, set()).add(a.strip().lower())
                covered.setdefault(f.behaviour, set())
            elif f.graph in GRAPH_ANCHOR:
                b, a = GRAPH_ANCHOR[f.graph]
                covered.setdefault(b, set()).add(a.lower())
        out = []
        for b in BEHAVIOURS:
            if b not in covered:
                continue
            areas = [{"name": a.name, "says": a.says, "seen": a.seen, "covered": a.name.lower() in covered[b]} for a in ANCHORS.get(b, ())]
            out.append({"behaviour": b, "label": BEHAVIOUR_LABEL[b], "covered": sum(1 for x in areas if x["covered"]), "of": sum(1 for x in areas if x["seen"]), "areas": areas})
        return sorted(out, key=lambda x: (-x["covered"], x["behaviour"]))

    def story(self) -> list[str]:
        """The evidence in the order it happened, one line each."""
        seen: set[Sig] = set()
        sigs: list[Sig] = []
        for f in self.findings:
            for e in f.evidence:
                if e not in seen:
                    seen.add(e)
                    sigs.append(e)
        sigs.sort(key=lambda e: e.at)
        days = (self.last_at - self.first_at) >= 18 * 3600
        fmt = "%a %H:%M" if days else "%H:%M"
        lines: list[str] = []
        i = 0
        while i < len(sigs):
            j = i
            while (j + 1 < len(sigs) and sigs[j + 1].verb == sigs[i].verb and folder_of(sigs[j + 1].path) == folder_of(sigs[i].path)
                   and sigs[i].verb in ("copied", "opened", "deleted", "created", "moved") and sigs[j + 1].at - sigs[j].at <= 90):
                j += 1
            run = sigs[i:j + 1]
            when = time.strftime(fmt, time.localtime(run[0].at))
            if len(run) > 2:
                lines.append(f"{when}  {run[0].verb} {len(run)} files {'to' if run[0].verb in ('copied', 'moved') else 'in'} {folder_of(run[0].path) or 'another place'}")
            else:
                for e in run:
                    lines.append(f"{when}  {e.phrase()}")
            i = j + 1
        return lines

    def graph(self) -> dict[str, Any]:
        seen: set[Sig] = set()
        sigs = [e for f in self.findings for e in f.evidence if not (e in seen or seen.add(e))]
        return graph_of(sigs)

    def headline(self) -> str:
        top = sorted(self.findings, key=lambda f: f.weight, reverse=True)[:4]
        said = f"{self.intent}. " + ("; ".join(dict.fromkeys(f.summary for f in sorted(top, key=lambda f: f.at))) + ".")
        extra = self.not_yet()
        return said + (f" {extra}" if extra else "")


def graph_of(sigs: list[Sig]) -> dict[str, Any]:
    """The picture of a case: what was touched, where it went, in columns (where it came from, where it was staged, packed, taken out, the traces).
    Runs of the same step in one folder become one node ("14 files in Staging"), so a burst reads as one thing. Computed here, so a console only draws it."""
    ordered = sorted(sigs, key=lambda e: e.at)
    devices = [e.device or e.path for e in ordered if e.verb == "attached"]

    def on_device(path: str) -> str:
        low = path.lower().replace("/", "\\")
        return next((d for d in devices if low.startswith(d.lower().replace("/", "\\").rstrip("\\") + "\\")), "")

    # bundles: consecutive same step into the same folder
    runs: list[list[Sig]] = []
    for e in ordered:
        if (runs and e.verb in ("copied", "created", "moved", "opened", "deleted") and runs[-1][-1].verb == e.verb and folder_of(runs[-1][-1].path) == folder_of(e.path)
                and e.at - runs[-1][-1].at <= 90):
            runs[-1].append(e)
        else:
            runs.append([e])
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def node(key: str, label: str, col: int, kind: str, at: float, count: int = 1) -> dict[str, Any]:
        n = nodes.setdefault(key, {"id": key, "label": label, "col": col, "kind": kind, "count": count, "badges": [], "at": at})
        n["count"] = max(n["count"], count)
        return n

    def badge(n: dict[str, Any], what: str) -> None:
        if what not in n["badges"]:
            n["badges"].append(what)

    def place(path: str, count: int, at: float, run: list[Sig]) -> dict[str, Any]:
        dev = on_device(path)
        if dev:
            return node("dev:" + dev, f"Drive {dev.rstrip(chr(92))}", 3, "drive", at)
        if count > 2:
            return node("dir:" + folder_of(path).lower(), f"{count} files in {name_of(folder_of(path)) or folder_of(path)}", 1 if run[0].verb != "opened" else 0, "staging", at, count)
        if is_archive(path):
            return node("f:" + path.lower(), name_of(path), 2, "archive", at)
        return node("f:" + path.lower(), name_of(path), 1 if is_system_folder(path) else 0, "system" if is_system_folder(path) else "file", at)

    last_bundle: dict[str, Any] | None = None
    for run in runs:
        e, n = run[0], len(run)
        if e.verb == "attached":
            node("dev:" + (e.device or e.path), f"Drive {(e.device or e.path).rstrip(chr(92))}", 3, "drive", e.at)
        elif e.verb == "cleared":
            node("trace:" + str(e.info.get("what") or "history"), f"cleared {e.info.get('what') or 'a history'}", 4, "trace", e.at)
        elif e.verb == "launched":
            node("trace:launched:" + e.program.lower(), f"started {e.program}" + (f" ({n} times)" if n > 1 else ""), 4, "trace", e.at, n)
        elif e.verb == "uploaded":
            node("net:" + e.program.lower(), f"{megabytes(e.info.get('bytes'))} sent out by {e.program or 'a program'}", 3, "drive", e.at)
        elif e.verb == "captured":
            node("trace:captured", "a picture of the screen was taken" + (f" ({n} times)" if n > 1 else ""), 4, "trace", e.at, n)
        elif e.verb == "silent":
            node("trace:silent", "stopped reporting", 4, "trace", e.at)
        elif e.verb in ("hid", "unhid"):
            badge(place(e.path, 1, e.at, run), "hidden" if e.verb == "hid" else "visible")
        elif e.verb == "deleted":
            for x in run:
                badge(place(x.path, 1, x.at, [x]) if n <= 2 else place(x.path, n, x.at, run), "deleted")
                if n > 2:
                    break
        elif e.verb in ("copied", "moved", "renamed"):
            to = place(e.path, n, e.at, run)
            if e.old:
                src_count = n
                src = node("dir:" + folder_of(e.old).lower(), f"{n} files in {name_of(folder_of(e.old))}", 0, "staging", e.at, n) if src_count > 2 else \
                    node("f:" + e.old.lower(), name_of(e.old), 0, "file", e.at)
                edges.append({"from": src["id"], "to": to["id"], "verb": e.verb, "at": e.at})
            if n > 2:
                last_bundle = to
        elif e.verb == "created":
            to = place(e.path, n, e.at, run)
            if is_archive(e.path) and last_bundle is not None and e.at - last_bundle["at"] <= 600:
                edges.append({"from": last_bundle["id"], "to": to["id"], "verb": "packed", "at": e.at})
            if n > 2:
                last_bundle = to
        elif e.verb == "opened":
            place(e.path, n, e.at, run)
    for n in nodes.values():
        n["badges"] = list(n["badges"])
    return {"nodes": sorted(nodes.values(), key=lambda x: (x["col"], x["at"])), "edges": edges}


@dataclass
class Update:
    case: Case
    created: bool
    raised: bool                # crossed into "case" or "urgent" with this finding (the moment to tell people)
    was: str
    now: str
    weight: float = 0.0         # the case as it stood at that moment (the case itself keeps growing)
    intent: str = ""
    stage: tuple[int, str, str | None] = (0, "", None)
    not_yet: str | None = None
    finding: Finding | None = None


@dataclass(frozen=True)
class Rule:
    """Something a reviewer said is fine, written down so it applies again: "this kind of finding, on this machine, with this program / in this folder / on
    this drive". It only LOWERS a matching finding (the finding is still recorded, with the rule named in its reasons) -- it never hides anything."""
    id: int
    pc: int
    graph: str
    kind: str                      # program | folder | drive
    value: str
    made_at: str = ""

    def matches(self, f: Finding) -> bool:
        if f.graph != self.graph or not f.evidence:
            return False
        v = self.value.lower().replace("/", "\\")
        if self.kind == "program":
            return any(e.program.lower() == v for e in f.evidence if e.program)
        if self.kind == "drive":
            return any(((e.device or e.path).lower() == v) if e.verb == "attached" else _device_in(e.path, v) for e in f.evidence)
        paths = [x.path.lower().replace("/", "\\") for x in f.evidence if x.path]
        return bool(paths) and all(x == v or x.startswith(v.rstrip("\\") + "\\") for x in paths)


def _device_in(path: str, device: str) -> bool:
    return bool(device) and path.lower().replace("/", "\\").startswith(device.rstrip("\\") + "\\")


def rule_options(findings: list[Finding]) -> list[dict[str, str]]:
    """What a reviewer could say is fine about these findings: the programs, folders and drives they involve (so the Engine can write the rule down)."""
    out: list[dict[str, str]] = []
    for f in findings:
        programs = sorted({e.program for e in f.evidence if e.program})
        out += [{"graph": f.graph, "kind": "program", "value": x} for x in programs]
        folders = {folder_of(e.path) for e in f.evidence if e.path and e.verb not in ("attached", "detached")}
        if len(folders) == 1 and (only := next(iter(folders))):
            out.append({"graph": f.graph, "kind": "folder", "value": only})
        devices = sorted({e.device for e in f.evidence if e.verb == "attached" and e.device})
        out += [{"graph": f.graph, "kind": "drive", "value": x} for x in devices]
    seen: set[tuple[str, str, str]] = set()
    return [o for o in out if not ((k := (o["graph"], o["kind"], o["value"])) in seen or seen.add(k))]


class Context:
    """What the detector may ask the rest of the system (the Engine supplies it; tests supply a dict). Every method has a safe answer for 'unknown'."""

    def __init__(self, *, task_things: Callable[[int], set[str]] | None = None, flow_paths: Callable[[int, str], bool] | None = None,
                 allowed: Callable[[int, str, str], bool] | None = None, known_device: Callable[[int, str], int] | None = None,
                 rules: Callable[[int], list[Rule]] | None = None) -> None:
        self._task, self._flow, self._allowed, self._known, self._rules = task_things, flow_paths, allowed, known_device, rules

    def ruled(self, pc: int, f: Finding) -> str:
        """Why a reviewer already said this is fine (or "")."""
        for r in (self._rules(pc) if self._rules else []):
            if r.pc == pc and r.matches(f):
                return f"you ruled {r.kind} {r.value} fine for this" + (f" on {r.made_at}" if r.made_at else "")
        return ""

    def has_task(self, pc: int, thing: str) -> bool:
        return bool(self._task and thing in self._task(pc))

    def written_by_flow(self, pc: int, path: str) -> bool:
        return bool(self._flow and self._flow(pc, path))

    def allowed(self, pc: int, thing: str, where: str) -> bool:
        return bool(self._allowed and self._allowed(pc, thing, where))

    def device_uses(self, pc: int, device: str) -> int:
        return self._known(pc, device) if self._known else 0


class Memory:
    """What one machine has been seen doing lately, and its drives."""

    def __init__(self) -> None:
        self.recent: deque[Sig] = deque()
        self.devices: dict[str, float] = {}                   # drive -> when it was plugged in (still attached)
        self.lineage: dict[str, set[str]] = {}                # an archive's thing -> the things that went into it
        self.hidden: set[str] = set()
        self.at_path: dict[str, str] = {}                     # where a thing was last seen -> which thing (a delete carries no hash of its own)
        self.hits: list[Hit] = []                             # the board: the stages reached lately, kept for days

    def add(self, s: Sig) -> None:
        if s.thing and s.path:
            self.at_path[s.path.lower().replace("/", "\\")] = s.thing
            if len(self.at_path) > 20000:
                for k in list(self.at_path)[:5000]:
                    self.at_path.pop(k, None)
        self.recent.append(s)
        while self.recent and self.recent[0].at < s.at - KEEP:
            self.recent.popleft()

    def since(self, at: float, *verbs: str) -> list[Sig]:
        return [x for x in self.recent if x.at >= at and (not verbs or x.verb in verbs)]

    def add_hits(self, hits: list[Hit], now: float) -> None:
        self.hits.extend(hits)
        if self.hits and (len(self.hits) > 4000 or self.hits[0].at < now - HIT_KEEP):
            self.hits = [h for h in self.hits if h.at >= now - HIT_KEEP][-4000:]


def _on_external(m: Memory, path: str) -> str:
    low = path.lower().replace("/", "\\")
    for dev in m.devices:
        d = dev.lower().replace("/", "\\").rstrip("\\")
        if d and low.startswith(d + "\\"):
            return dev
    return ""


class Detective:
    """Feed it what happens; it says when a case is raised or grows. One instance holds every machine's memory and every open case."""

    def __init__(self, ctx: Context | None = None, clock: Callable[[], float] = time.time) -> None:
        self.ctx = ctx or Context()
        self.clock = clock
        self.mem: dict[int, Memory] = {}
        self.cases: list[Case] = []
        self._covered: dict[tuple[int, str, int], float] = {}       # (machine, intent, when the piece of work began) -> the coverage already said

    # --- feeding -----------------------------------------------------------------------------------------------

    def feed(self, s: Sig) -> list[Update]:
        if s.by == "falcon":
            return []                                        # Falcon's own flows and actions are not behaviour
        m = self.mem.setdefault(s.pc, Memory())
        if not s.thing:
            known = m.at_path.get(s.path.lower().replace("/", "\\")) or (m.at_path.get(s.old.lower().replace("/", "\\")) if s.old else "")
            if known:
                s = replace(s, thing=known)
        if s.verb == "attached":
            m.devices[s.device or s.path] = s.at
        elif s.verb == "detached":
            m.devices.pop(s.device or s.path, None)
        m.add(s)
        new = self._hits(m, s)
        m.add_hits(new, s.at)
        out: list[Update] = []
        for f in self._graphs(m, s) + self._coverage(m, s, new):
            f.weight = self._contextual(f, s)
            if any(x.startswith("you ruled ") for x in f.why):
                f.weight = max(f.weight, 0.12)                    # a rule lowers a finding, it never makes it vanish: it stays on the record with the rule named
            if f.weight < 0.12:
                continue
            out.append(self._attach(f))
        return out

    def remember(self, s: Sig) -> None:
        """Put something in a machine's memory without judging it (what was already known before this run, so a restart does not forget the last hours)."""
        m = self.mem.setdefault(s.pc, Memory())
        if s.verb == "attached":
            m.devices[s.device or s.path] = s.at
        elif s.verb == "detached":
            m.devices.pop(s.device or s.path, None)
        m.add(s)
        m.add_hits(self._hits(m, s), s.at)

    # --- anchors: which stage of which intent an event is -----------------------------------------------------------

    @staticmethod
    def _worth(s: Sig) -> tuple[float, list[str]]:
        """How much the thing itself matters, apart from what was done to it: one deletion of the right file outweighs ten of the wrong ones."""
        w, why = 0.0, []
        if "restricted" in s.tags:
            w += 0.05 if "own_scope" in s.tags else 0.12
            why.append("a restricted file" + (" of their own department's" if "own_scope" in s.tags else ""))
        if names_something_that_matters(s.path) or (s.old and names_something_that_matters(s.old)):
            w += 0.08
            why.append("its name or place says it matters")
        if s.path.startswith("\\\\"):
            w += 0.06
            why.append("on a share other people use")
        if "only_copy" in s.tags:
            # nearly every file is the only copy the index knows of, so it counts for little alone and for a lot beside anything else that says it matters
            w += 0.20 if w > 0 else 0.04
            why.append("the only copy the index knows of")
        return w, why

    def _sources_of(self, m: Memory, s: Sig) -> list[Sig]:
        lo = s.at - 5 * 60
        return [x for x in m.since(lo, "opened", "copied", "created", "modified") if x is not s and not is_archive(x.path) and x.path != s.path
                and ("restricted" in x.tags or x.verb in ("opened", "copied")) and (not s.program or not x.program or x.program == s.program)]

    def _hits(self, m: Memory, s: Sig) -> list[Hit]:
        """The area(s) of each intent this event belongs to. An event may belong to several intents (what means little in one can mean a lot in another)."""
        out: list[Hit] = []
        v = s.verb
        thing = s.thing or s.path
        base = frozenset({thing}) if thing else frozenset()
        worth, _ = self._worth(s)
        kf = kind_factor(s.path, s.tags if "own_scope" not in s.tags else frozenset())
        ext, old_ext = ext_of(s.path), ext_of(s.old) if s.old else ""
        dev = _on_external(m, s.path) if s.path else ""
        low = s.path.lower().replace("/", "\\")

        def add(b: str, a: str, w: float, extra: frozenset[str] = frozenset()) -> None:
            out.append(Hit(b, a, s.at, round(w, 3), base | extra, s))

        recent_exfil = frozenset().union(*(h.things for h in m.hits if h.behaviour == "exfiltration" and h.anchor in ("Gather", "Compress", "Transform") and s.at - h.at <= THREAD)) \
            if m.hits else frozenset()
        if v in ("copied", "moved", "created") and dev:
            lineage = m.lineage.get(thing, set())
            add("exfiltration", "Transfer", 0.30 * kf + (0.08 if is_archive(s.path) else 0.0) + worth, frozenset(lineage))
            if any(h.behaviour == "capture" and h.anchor == "Keep" and h.things & (base | frozenset(lineage)) for h in m.hits):
                add("capture", "Pass on", 0.30 + worth)
        elif v in ("copied", "moved") and s.path.startswith("\\\\"):
            add("exfiltration", "Transfer", 0.26 * kf + worth)             # a share elsewhere on the network: inside, but off this machine
        elif v in ("copied", "moved") and not is_system_folder(s.path) and not is_system_folder(s.old or "") and ext not in SYSTEMISH_EXT \
                and folder_of(s.path).lower() != folder_of(s.old or "").lower():
            mine = 0.01 if _same_profile(s.path, s.old) and not worth else 0.03         # filing a download into one's own documents is housekeeping, not gathering
            add("exfiltration", "Gather", mine + worth)
            add("collection", "Access", mine + worth)
            same = {x.thing or x.path for x in m.since(s.at - 10 * 60, "copied", "moved") if folder_of(x.path).lower() == folder_of(s.path).lower()}
            if len(same) >= 3:
                add("collection", "Assemble", 0.10 + worth)
        if v in ("created", "copied") and is_archive(s.path) and not dev:
            sources = self._sources_of(m, s)
            things = {x.thing or x.path for x in sources}
            here = folder_of(s.path).lower()
            things |= {t for h in m.hits if h.behaviour == "exfiltration" and h.anchor == "Gather" and folder_of(h.sig.path).lower() == here for t in h.things}
            if things:
                m.lineage[thing] = things
            # a person zipping their own working files is ordinary: it counts for little until the files are ones that matter (or what the zip is later used for does)
            add("exfiltration", "Compress", 0.08 + worth + min(0.10, 0.02 * len(things)) + (0.10 if any("restricted" in x.tags for x in sources) else 0.0), frozenset(things))
            add("collection", "Consolidate", 0.06 + worth, frozenset(things))
        if v in ("renamed", "moved") and s.old and old_ext != ext:
            if (old_ext in DOC_EXT or old_ext in ARCHIVE_EXT) and ext not in DOC_EXT:
                add("exfiltration", "Transform", 0.14 + worth)
            if disguised(s.old, s.path):
                add("concealment", "Disguise", 0.22 + worth)
            if ext in ENC_EXT:
                add("concealment", "Protect", 0.20 + worth)
        if v == "hid":
            add("concealment", "Disguise", 0.18 + worth)
            add("exfiltration", "Transform", 0.08 + worth)
        if v == "created" and ext in ENC_EXT:
            add("exfiltration", "Transform", 0.20 + worth)
            add("concealment", "Protect", 0.20 + worth)
        elif v == "created" and ext and not is_archive(s.path):
            stem = name_of(s.path).rsplit(".", 1)[0].lower()
            if any(name_of(x.path).rsplit(".", 1)[0].lower() == stem and ext_of(x.path) != ext and ext_of(x.path) in DOC_EXT
                   for x in m.since(s.at - 10 * 60, "created", "copied", "modified", "opened") if x is not s):
                add("exfiltration", "Transform", 0.12 + worth)                       # the same document in another format
        if v == "moved" and is_system_folder(s.path) and ext in DOC_EXT | ARCHIVE_EXT and not (s.old and is_system_folder(s.old)):
            add("concealment", "Relocate", 0.15 + worth)
        if v == "uploaded":
            add("exfiltration", "Transfer", 0.25 + worth, recent_exfil)
            if any(h.behaviour == "capture" and h.anchor == "Keep" and s.at - h.at <= THREAD for h in m.hits):
                add("capture", "Pass on", 0.30)
        if v == "deleted":
            own = any(x.verb in ("created", "copied", "moved") and (x.path == s.path or (thing and x.thing == thing)) for x in m.recent if x is not s and x.at < s.at)
            if ext in VALUABLE_EXT:
                add("erasure", "Remove", 0.06 + worth)
                if not own:                                   # taking back what one made a moment ago is tidying, not destroying
                    add("sabotage", "Destroy", 0.10 + worth)
                    if worth >= 0.12:
                        add("sabotage", "Reach", 0.06 + worth)
            if ext in BACKUP_EXT or "backup" in low or "shadow" in low:
                add("sabotage", "Disable safety nets", 0.30)
        if v == "modified" and worth >= 0.12:
            add("erasure", "Alter", 0.08 + worth)
            add("sabotage", "Reach", 0.06 + worth)
        if v == "permissions":
            add("sabotage", "Destroy", 0.22 + worth)                    # who may open it was changed: a lock-out
        if v == "cleared":
            add("erasure", "Clear the trail", 0.40)
        if v in ("launched", "captured") and (v == "captured" or any(t in s.program.lower() for t in CAPTURE_TOOLS)):
            add("capture", "Capture", 0.18)
            working = [x for x in m.since(s.at - 10 * 60) if "restricted" in x.tags and x.verb not in ("attached", "detached", "captured")]
            if working:
                out.append(Hit("capture", "Open the source", s.at, 0.10, frozenset(x.thing or x.path for x in working), working[-1]))
        if v == "created" and ext in IMAGE_EXT and any(h.behaviour == "capture" and h.anchor == "Capture" and 0 <= s.at - h.at <= 120 for h in m.hits):
            add("capture", "Keep", 0.12)
        if v == "silent":
            add("evasion", "Switch off", 0.10)                             # alone it is a laptop lid; beside anything else it is not (see _went_silent)
        if v == "opened":
            add("collection", "Access", 0.03 + worth)
            if "outside_role" in s.tags:
                outside = [h for h in m.hits if h.behaviour == "reach" and h.anchor in ("Find", "Beyond role")]
                if outside:
                    add("reach", "Beyond role", 0.10 + worth)
                else:
                    add("reach", "Find", 0.15 + worth)                  # the first thing outside one's work that is opened is the most telling: it is the one that was chosen
                if len({folder_of(h.sig.path).lower() for h in outside} | {folder_of(s.path).lower()}) >= 3:
                    add("reach", "Widen", 0.15)
                day = time.strftime("%Y%m%d", time.localtime(s.at))
                if any(time.strftime("%Y%m%d", time.localtime(h.at)) != day for h in outside):
                    add("reach", "Return", 0.20)
        return out

    def _coverage(self, m: Memory, s: Sig, new: list[Hit]) -> list[Finding]:
        """What the events on the board add up to, intent by intent. A piece of work is the events that share a file or happen within half an hour of each other. Each
        intent weighs what falls in its own areas and, at a discount, in the areas of the intents it contains. Nothing needs to be complete: one heavy event is enough."""
        out: list[Finding] = []
        touched = {h.behaviour for h in new}
        targets = [b for b in ANCHORS if b in touched or any(c in touched for c in INCLUDES.get(b, ()))]
        for behaviour in targets:
            family = {behaviour, *INCLUDES.get(behaviour, ())}
            mine = [h for h in m.hits if h.behaviour in family]
            parent = list(range(len(mine)))

            def find(i: int, parent: list[int] = parent) -> int:
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i

            shared: set[int] = set()
            for i, a in enumerate(mine):
                for j in range(i):
                    b = mine[j]
                    by_thing = bool(a.things & b.things)
                    if by_thing or abs(a.at - b.at) <= THREAD:
                        parent[find(i)] = find(j)
                        if by_thing:
                            shared.update((i, j))
            fresh = {id(h) for h in new}
            for root in {find(i) for i, h in enumerate(mine) if id(h) in fresh}:
                idx = [i for i in range(len(mine)) if find(i) == root]
                comp = [mine[i] for i in idx]
                own: dict[str, list[float]] = {}
                kids: dict[str, list[float]] = {}
                mine_sigs = {h.sig for h in comp if h.behaviour == behaviour}
                for h in comp:
                    if h.behaviour == behaviour:
                        own.setdefault(h.anchor, []).append(h.weight)
                    elif h.sig not in mine_sigs:              # the same event already counted in the intent's own areas is not evidence twice
                        kids.setdefault(f"{h.behaviour}/{h.anchor}", []).append(h.weight)
                linked = any(i in shared for i in idx)
                w, covered = coverage(behaviour, own, kids, linked or len(comp) == 1)
                if w < 0.12 or not any(h.behaviour == behaviour for h in comp):
                    continue                               # (a parent is only said when something in its own areas is there: the children speak for themselves)
                key = (s.pc, behaviour, round(min(h.at for h in comp)))
                if w <= self._covered.get(key, 0.0) + 0.03:
                    continue                               # nothing new worth saying
                self._covered[key] = w
                things = frozenset().union(*(h.things for h in comp))
                sigs = sorted({h.sig for h in comp}, key=lambda x: x.at)[-14:]
                names = [c.split("/")[-1] if "/" not in c else c for c in covered]
                out.append(Finding(behaviour, "coverage_" + behaviour, s.at, s.pc, w, things,
                                   f"{BEHAVIOUR_LABEL[behaviour]}: {', '.join(c.replace('/', ' · ') for c in covered)}", sigs,
                                   "one piece of ordinary work that happens to touch these areas",
                                   ["areas covered: " + ", ".join(names)] + ([] if linked or len(comp) == 1 else ["the events share no file, only the time"])))
        return out

    # --- the mini-graphs ----------------------------------------------------------------------------------------

    def _graphs(self, m: Memory, s: Sig) -> list[Finding]:
        found: list[Finding | None] = []
        if s.verb == "hid":
            found.append(self._hidden(m, s))
        if s.verb in ("renamed", "moved"):
            found.append(self._disguised(m, s))
            found.append(self._buried(m, s))
        if s.verb in ("created", "copied", "moved") and "flow_bypass" in s.tags:
            found.append(self._bypass(m, s))
        if s.verb in ("created", "copied", "modified"):
            found.append(self._archived(m, s))
            found.append(self._gathering(m, s))
            found.append(self._to_drive(m, s))
        if s.verb == "attached":
            found.append(self._drive_after_staging(m, s))
        if s.verb == "deleted":
            found.append(self._removed_after_taking(m, s))
            found.append(self._mass_removal(m, s))
        if s.verb == "cleared":
            found.append(self._history_cleared(m, s))
        if s.verb in ("launched", "captured"):
            found.append(self._capture_tool(m, s))
        if s.verb == "uploaded":
            found.append(self._uploaded(m, s))
        if s.verb == "silent":
            found.append(self._went_silent(m, s))
        if s.verb in ("renamed", "modified", "deleted"):
            found.append(self._wrecking(m, s))
        if s.verb == "opened":
            found.append(self._outside_role(m, s))
        return [f for f in found if f is not None]

    def _restricted(self, *sigs: Sig) -> bool:
        """Restricted material that is not simply this person's own department's work (that is what their job is made of)."""
        return any("restricted" in x.tags and "own_scope" not in x.tags for x in sigs)

    def _hidden(self, m: Memory, s: Sig) -> Finding:
        w, why = 0.30, ["a file was made hidden"]
        if is_system_folder(s.path):
            w += 0.20
            why.append("in a system folder")
        if self._restricted(s):
            w += 0.20
            why.append("a restricted file")
        if ext_of(s.path) in DOC_EXT:
            w += 0.08
        m.hidden.add(s.thing or s.path)
        return Finding("concealment", "hidden", s.at, s.pc, w, frozenset({s.thing or s.path}), f"{s.name} was hidden", [s],
                       "someone hiding a personal or in-progress file", why)

    def _disguised(self, m: Memory, s: Sig) -> Finding | None:
        old = s.old or ""
        if s.verb == "renamed" and disguised(old, s.path):
            w, why = 0.45, [f"{name_of(old)} was given the look of {name_of(s.path)}"]
            if is_system_folder(s.path):
                w += 0.12
                why.append("in a system folder")
            if self._restricted(s):
                w += 0.15
                why.append("a restricted file")
            return Finding("concealment", "disguised", s.at, s.pc, w, frozenset({s.thing or s.path}),
                           f"{name_of(old)} was renamed to look like a different kind of file ({name_of(s.path)})", [s],
                           "a file saved in a format or name an application insists on", why)
        if s.verb == "moved" and s.old and disguised(s.old, s.path):
            return Finding("concealment", "disguised", s.at, s.pc, 0.45, frozenset({s.thing or s.path}),
                           f"{name_of(s.old)} was renamed to look like a different kind of file ({s.name}) while moving", [s], "an application's own save", ["renamed while moving"])
        return None

    def _buried(self, m: Memory, s: Sig) -> Finding | None:
        if s.verb != "moved" or ext_of(s.path) not in DOC_EXT | ARCHIVE_EXT or not is_system_folder(s.path) or (s.old and is_system_folder(s.old)):
            return None
        w, why = 0.30, [f"{s.name} was moved into a system folder"]
        if self._restricted(s):
            w += 0.20
            why.append("a restricted file")
        return Finding("concealment", "buried", s.at, s.pc, w, frozenset({s.thing or s.path}), f"{s.name} was moved somewhere nobody looks ({folder_of(s.path)})", [s],
                       "an application keeping its own data there", why)

    def _archived(self, m: Memory, s: Sig) -> Finding | None:
        if s.verb != "created" or not is_archive(s.path):
            return None
        sources = self._sources_of(m, s)
        things = {x.thing or x.path for x in sources}
        if len(things) < 3:
            return None
        m.lineage[s.thing or s.path] = things
        w, why = 0.42, [f"{len(things)} files were packed together"]
        if self._restricted(*sources):
            w += 0.22
            why.append("restricted files among them")
        return Finding("collection", "archived", s.at, s.pc, w, frozenset(things | {s.thing or s.path}),
                       f"{len(things)} files were packed into {s.name}", sources[-200:] + [s], "a person sending a few files together or a backup", why)

    def _gathering(self, m: Memory, s: Sig) -> Finding | None:
        lo = s.at - 10 * 60
        near = [x for x in m.since(lo, "opened", "copied") if "restricted" in x.tags and "own_scope" not in x.tags]
        things = {x.thing or x.path for x in near}
        if len(things) < 8 or s.verb not in ("copied", "opened"):
            return None
        if any(f.graph == "gathering" and s.at - f.at < 10 * 60 for c in self.cases if c.pc == s.pc for f in c.findings):
            return None
        return Finding("collection", "gathering", s.at, s.pc, 0.40 + min(0.20, 0.02 * (len(things) - 8)), frozenset(things),
                       f"{len(things)} restricted files were gathered in ten minutes", near[-200:], "a review or an audit that needs all of them", [f"{len(things)} restricted files in ten minutes"])

    def _to_drive(self, m: Memory, s: Sig) -> Finding | None:
        dev = _on_external(m, s.path)
        if not dev or s.verb not in ("copied", "created"):
            return None
        lineage = m.lineage.get(s.thing or s.path, set())
        lineage_restricted = self._restricted(s) or any(("restricted" in x.tags and "own_scope" not in x.tags) for x in m.since(s.at - 3600) if (x.thing or x.path) in lineage)
        w, why = (0.45 if lineage_restricted else 0.30) * kind_factor(s.path, s.tags if lineage_restricted else frozenset()), [f"{s.name} was put on a removable drive"]
        if is_archive(s.path):
            w += 0.10
            why.append("an archive")
        if self._restricted(s) or any(("restricted" in x.tags) for x in m.since(s.at - 3600) if (x.thing or x.path) in lineage):
            w += 0.18
            why.append("restricted content")
        return Finding("exfiltration", "to_drive", s.at, s.pc, w, frozenset({s.thing or s.path} | lineage), f"{s.name} was copied to a removable drive ({dev})", [s],
                       "a drive this person always uses for their own files", why)

    def _bypass(self, m: Memory, s: Sig) -> Finding | None:
        """What a flow delivers here, put here by hand instead: the sanctioned way to move it is the flow (checked, consented, audited), so doing it by hand is a way round."""
        w, why = 0.36, [f"{s.name} is what a flow delivers to this folder, put here by hand instead"]
        if self._restricted(s):
            w += 0.20
            why.append("a restricted file")
        return Finding("exfiltration", "flow_bypass", s.at, s.pc, w, frozenset({s.thing or s.path}), f"{s.name} was copied here by hand, not by the flow that delivers it", [s],
                       "a person fetching something the flow was slow to bring", why)

    def _drive_after_staging(self, m: Memory, s: Sig) -> Finding | None:
        lo = s.at - WINDOW
        staged = [f for c in self.cases if c.pc == s.pc for f in c.findings if not f.graph.startswith("coverage_") and f.behaviour in ("collection", "concealment") and f.at >= lo]
        if not staged:
            return None
        return Finding("exfiltration", "drive_after_staging", s.at, s.pc, 0.34, frozenset().union(*(f.things for f in staged)),
                       f"a drive was plugged in just after files were gathered or hidden ({s.device})", [s], "a coincidence", ["a drive appeared right after staging"])

    def _removed_after_taking(self, m: Memory, s: Sig) -> Finding | None:
        lo = s.at - 30 * 60
        thing = s.thing or s.path
        gone = {thing}
        for arc, srcs in m.lineage.items():
            if thing == arc or thing in srcs:
                gone |= srcs | {arc}
        taken = [x for x in m.since(lo, "copied", "created", "moved") if _on_external(m, x.path) and (x.thing or x.path) in gone]
        if not taken:
            return None
        w, why = 0.52, [f"{s.name} was deleted after it was copied to a drive"]
        if is_archive(s.path):
            why.append("the archive that carried it")
        if self._restricted(s):
            w += 0.12
        return Finding("erasure", "removed_after_taking", s.at, s.pc, w, frozenset(gone), f"{s.name} was deleted after being copied off the machine", taken[-1:] + [s],
                       "tidying up after a legitimate transfer", why)

    def _mass_removal(self, m: Memory, s: Sig) -> Finding | None:
        lo = s.at - 120
        dels = [x for x in m.since(lo, "deleted") if ext_of(x.path) in DOC_EXT]
        hand = sum(1 for x in dels if x.by == "hand") * 2 > len(dels)
        if len(dels) < (25 if hand else 15):
            return None
        first = min(x.at for x in dels)
        if any(f.graph == "mass_removal" and abs(f.at - first) < 120 for c in self.cases if c.pc == s.pc for f in c.findings):
            return None
        # The same burst can be read as sabotage (damage) or as erasure (covering what was done). It is erasure when it follows staging or taking
        # on this machine; by hand and with nothing before it, it stays a little weight rather than nothing.
        staged = [f for c in self.cases if c.pc == s.pc for f in c.findings if not f.graph.startswith("coverage_") and f.behaviour in ("collection", "exfiltration", "concealment") and s.at - f.at <= WINDOW]
        if hand and not staged:
            return None                  # by hand with nothing before it this is read as damage (sabotage), not as covering anything up
        w, why = (0.20 if hand else 0.40), [f"{len(dels)} deletions in two minutes"]
        if staged:
            w += 0.28
            why.append("right after files were gathered, hidden or taken out")
        return Finding("erasure", "mass_removal", s.at, s.pc, w, frozenset({x.thing or x.path for x in dels}),
                       f"{len(dels)} documents were deleted in two minutes" + (" by hand" if hand else ", not by hand"), dels[-200:],
                       "a clean-up script or an application removing its own files" if not hand else "a person tidying up old files", why)

    def _history_cleared(self, m: Memory, s: Sig) -> Finding:
        what = str(s.info.get("what") or "").lower()
        record = any(k in what for k in ("security", "system")) and "log" in what          # the machine's own record of who did what; an application log is housekeeping
        is_log = record
        return Finding("erasure", "history_cleared", s.at, s.pc, 0.55 if record else 0.25 if "log" in what else 0.40, frozenset(), f"{s.info.get('what') or 'a history'} was cleared", [s],
                       "an administrator clearing a log on purpose" if is_log else "routine housekeeping", ["the machine's own record of what happened was cleared" if is_log else "a history was cleared"])

    def _capture_tool(self, m: Memory, s: Sig) -> Finding | None:
        """The screen photographed: a tool started (the Snipping Tool, ShareX ...) or a picture put on the clipboard (PrintScreen, Win+Shift+S) -- one reading, two ways in."""
        pictured = s.verb == "captured"
        if pictured:
            if any(x.verb == "launched" and any(t in x.program.lower() for t in CAPTURE_TOOLS) for x in m.since(s.at - 120)):
                return None                                      # the tool that took it was already read when it started
        elif not any(t in s.program.lower() for t in CAPTURE_TOOLS):
            return None
        lo = s.at - 10 * 60
        working = [x for x in m.since(lo) if "restricted" in x.tags and x.verb not in ("attached", "detached", "captured")]
        again = [x for x in m.since(s.at - 30 * 60, "launched", "captured") if x is not s and (x.verb == "captured" or any(t in x.program.lower() for t in CAPTURE_TOOLS))]
        what = ("a picture of the whole screen" if s.info.get("kind") == "screen" else "a picture") + " was put on the clipboard" if pictured else f"{s.program} was started"
        w, why = 0.10 if not pictured else 0.08, [what]
        if working:
            w += 0.40 if any("own_scope" not in x.tags for x in working) else 0.12
            why.append("restricted files were being worked on just before")
        if again:
            w += (0.10 if working else 0.03) * min(3, len(again))               # again and again, over material that matters, is a habit worth saying
            why.append("it has been started again and again")
        if pictured:
            tail = f" ({s.program})" if s.program else ""
            summary = (what[0].upper() + what[1:] + tail + (" while restricted files were open" if working else ""))
        else:
            summary = f"{s.program} was started while restricted files were open" if working else f"{s.program} was started"
        return Finding("capture", "clipboard_picture" if pictured else "capture_tool", s.at, s.pc, w, frozenset({x.thing or x.path for x in working}), summary, working[-6:] + [s],
                       "someone capturing their own work, or documenting a problem for support", why)

    def _uploaded(self, m: Memory, s: Sig) -> Finding | None:
        """A program sent a great deal out over the network. Alone it is mostly a video call, a sync client or an update; after files were gathered, packed or hidden it is the way out."""
        import math

        size = float(s.info.get("bytes") or 0)
        if size <= 0:
            return None
        w, why = 0.18 + min(0.22, 0.05 * math.log2(size / 25_000_000 + 1)), [f"{megabytes(size)} sent out in {int(s.info.get('seconds') or 60)} seconds"]
        lo = s.at - 30 * 60
        near = [x for x in m.since(lo) if x.verb in ("created", "copied", "opened", "moved", "hid") and (("restricted" in x.tags and "own_scope" not in x.tags)
                                                                                                        or (is_archive(x.path) and m.lineage.get(x.thing or x.path)))]
        matters = any("restricted" in x.tags and "own_scope" not in x.tags for x in near)
        staged = [f for c in self.cases if c.pc == s.pc for f in c.findings if not f.graph.startswith("coverage_") and f.behaviour in ("collection", "concealment") and s.at - f.at <= WINDOW]
        if near:
            w += 0.28 if matters else 0.08
            why.append("just after restricted files were worked on" if matters else "just after files were packed")
        if staged:
            w += 0.18
            why.append("right after files were gathered or hidden")
        if int(s.info.get("destinations") or 1) == 1:
            w += 0.04
            why.append("all to one place")
        return Finding("exfiltration", "uploaded", s.at, s.pc, w, frozenset({x.thing or x.path for x in near if (x.thing or x.path)}),
                       f"{s.program or 'a program'} sent {megabytes(size)} out over the network", near[-6:] + [s],
                       "a video call, a sync or backup client, an update, or a person sending something they are meant to", why)

    def _went_silent(self, m: Memory, s: Sig) -> Finding | None:
        """A machine that stops reporting while still switched on, right after something worth a look happened on it: the watch is being slipped."""
        recent = [c for c in self.cases if c.pc == s.pc and s.at - c.last_at <= 60 * 60 and c.weight >= NOTED]
        if not recent:
            return None
        top = max(recent, key=lambda c: c.weight)
        w = 0.30 + (0.20 if top.level in ("case", "urgent") else 0.0)
        return Finding("evasion", "went_silent", s.at, s.pc, w, frozenset(top.things), "the machine stopped reporting while a case was open on it", [s],
                       "a laptop closed, a power cut or a network fault", [f"a case ({top.intent.lower()}) was open on it"])

    def _wrecking(self, m: Memory, s: Sig) -> Finding | None:
        """Files being destroyed or scrambled in bulk by a program, not a person: many documents deleted, renamed to one odd ending, or rewritten in two minutes."""
        if ext_of(s.path) not in DOC_EXT and s.verb != "renamed":
            return None
        lo = s.at - 120
        burst = [x for x in m.since(lo, s.verb) if x.by != "falcon"]
        by_hand = bool(burst) and sum(1 for x in burst if x.by == "hand") * 2 > len(burst)
        if s.verb == "renamed":
            ends = {}
            for x in burst:
                if ext_of(x.old) in DOC_EXT and ext_of(x.path) not in DOC_EXT:
                    ends.setdefault(ext_of(x.path), []).append(x)
            if not ends:
                return None
            ending, same = max(ends.items(), key=lambda kv: len(kv[1]))
            if len(same) < 10:
                return None
            graph, summary = "scrambled_names", f"{len(same)} documents were renamed to end in .{ending} in two minutes, not by hand"
            hits = same
        else:
            hits = [x for x in burst if ext_of(x.path) in DOC_EXT]
            if len(hits) < 40:
                return None
            graph = "bulk_destroyed" if s.verb == "deleted" else "bulk_rewritten"
            summary = f"{len(hits)} documents were {'deleted' if s.verb == 'deleted' else 'rewritten'} in two minutes, not by hand"
        if any(f.graph == graph and s.at - f.at < 120 and (len(f.things) + 19 >= len(hits) or (by_hand and len(f.things) * 2 > len(hits))) for c in self.cases if c.pc == s.pc for f in c.findings):
            return None                                           # one finding per burst, said again only when it has grown a great deal
        # A program doing it is the loud case. A person's own hands doing it is not innocent by default either: it starts lower and is raised by what was
        # destroyed (restricted files, work outside their role, many places at once) -- the same sixty deletions mean little in one folder of old drafts
        # and a great deal across the restricted share.
        if by_hand:
            w, why = 0.28, [f"{len(hits)} files in two minutes by hand"]
            summary = summary.replace(", not by hand", " by hand")
        else:
            w, why = 0.65 + min(0.25, 0.01 * (len(hits) - 10)), [f"{len(hits)} files in two minutes by a program"]
        restricted = sum(1 for x in hits if "restricted" in x.tags)
        if restricted * 4 >= len(hits):
            w += 0.22 if by_hand else 0.08
            why.append(f"{restricted} of them restricted")
        outside = sum(1 for x in hits if "outside_role" in x.tags)
        if outside * 2 >= len(hits):
            w += 0.15 if by_hand else 0.05
            why.append("mostly files outside this person's work")
        shared = sum(1 for x in hits if x.path.startswith("\\\\"))
        if shared * 2 >= len(hits):
            w += 0.30 if by_hand else 0.08
            why.append("on a share other people use")
        places = len({folder_of(x.path) for x in hits})
        if places >= 4:
            w += 0.08 if by_hand else 0.0
            why.append(f"across {places} folders")
        if by_hand and len(hits) >= 150:
            w += 0.08
            why.append("a very large number")
        return Finding("sabotage", graph, s.at, s.pc, w, frozenset({x.thing or x.path for x in hits}), summary, hits[-200:],
                       "a deliberate clean-up, a migration tool or a conversion", why)

    def _outside_role(self, m: Memory, s: Sig) -> Finding | None:
        lo = s.at - 20 * 60
        outside = [x for x in m.since(lo, "opened") if "outside_role" in x.tags]
        folders = {folder_of(x.path) for x in outside}
        if len(outside) < 15 or len(folders) < 3 or "outside_role" not in s.tags:
            return None
        first = min(x.at for x in outside)
        if any(f.graph == "outside_role" and abs(f.at - first) < 20 * 60 for c in self.cases if c.pc == s.pc for f in c.findings):
            return None
        return Finding("reach", "outside_role", s.at, s.pc, 0.36 + min(0.2, 0.01 * (len(outside) - 15)), frozenset({x.thing or x.path for x in outside}),
                       f"{len(outside)} files were opened across {len(folders)} folders that are not part of this person's work", outside[-200:],
                       "covering for a colleague, or looking for one particular file", [f"{len(outside)} files in {len(folders)} places outside their work"])

    # --- context ------------------------------------------------------------------------------------------------

    def _contextual(self, f: Finding, s: Sig) -> float:
        w = f.weight
        proportional = f.graph.startswith("coverage_")

        def lift(w: float, d: float) -> float:
            """Context raises a finding. On a sum of many readings it raises in proportion, so a trivial sum stays trivial."""
            return w * (1.0 + d * 2.5) if proportional else w + d

        def cut(w: float, d: float) -> float:
            """Context lowers a finding. Coverage already adds many readings of the same work, so there it lowers in proportion (a task for the file takes most of it away
            whatever it came to) instead of by a fixed amount that a large sum would shrug off."""
            return w * (1.0 - min(0.9, d * 1.6)) if proportional else w - d

        if f.behaviour in ("concealment", "collection", "exfiltration", "erasure") and s.by in ("alone", "started"):
            w = lift(w, 0.08 if s.by == "alone" else 0.05)                       # done by a program rather than by hand: a little more telling, never a verdict
            f.why.append("done by a program on its own" if s.by == "alone" else "done by a program the person started")
        for thing in f.things:
            if self.ctx.has_task(s.pc, thing):
                w = cut(w, 0.45)
                f.why.append("a task covers this file")
                break
        if any(self.ctx.written_by_flow(s.pc, e.path) for e in f.evidence if e.path):
            w = cut(w, 0.40)
            f.why.append("a flow wrote it")
        mem = self.mem[s.pc]
        if any("allowed" in e.tags for e in f.evidence):
            w = cut(w, 0.45)
            f.why.append("recorded as allowed")
        if any("task_expected" in e.tags for e in f.evidence):
            w = cut(w, 0.45)
            f.why.append("a task asks for exactly this")
        if (said := self.ctx.ruled(s.pc, f)):
            w = cut(w, 0.45)
            f.why.append(said)
        dev = next((d for e in f.evidence for d in ((e.device,) if e.verb == "attached" else (_on_external(mem, e.path),)) if d), "")
        if dev and any(self.ctx.allowed(s.pc, t, dev) for t in f.things):
            w = cut(w, 0.45)
            f.why.append("recorded as allowed there")
        if dev:
            uses = self.ctx.device_uses(s.pc, dev)
            if uses >= 3:
                w = cut(w, 0.35)
                f.why.append(f"a drive this machine has used {uses} times")
            elif uses == 0 and f.behaviour == "exfiltration" and not any("a task covers" in x for x in f.why):
                w = lift(w, 0.10)
                f.why.append("a drive this machine has not seen before")
        mover = next((e.program for e in f.evidence if e.program and any(p in e.program.lower() for p in USUAL_MOVERS)), "")
        if mover:
            w = cut(w, 0.35)
            f.why.append(f"{mover} is a program that moves files for a living")
        hour = time.localtime(s.at).tm_hour
        if (hour >= 22 or hour < 6) and f.weight >= 0.3:
            w = lift(w, 0.04)                                           # context only: it can never start a finding
        return max(0.0, min(0.95, w))

    # --- cases --------------------------------------------------------------------------------------------------

    def _attach(self, f: Finding) -> Update:
        best, how = None, 0
        for c in self.cases:
            if c.pc != f.pc:
                continue
            link = 3 if (c.things & f.things) else 2 if f.at - c.last_at <= SESSION else 1 if (f.at - c.last_at <= PATIENT and self._continues(c, f)) else 0
            if link > how:
                best, how = c, link
        created = best is None
        if best is None:
            best = Case(pc=f.pc, first_at=f.at)
            self.cases.append(best)
        was = "quiet" if created else best.level
        intent_was = "" if created else best.intent
        best.findings.append(f)
        best.last_at = max(best.last_at, f.at)
        now = best.level
        order = ("quiet", "noted", "case", "urgent")
        crossed = order.index(now) > order.index(was) and now in ("case", "urgent")
        # a case already raised that turns into something graver (hiding becomes taking data out) is worth telling people again
        graver = bool(intent_was) and now in ("case", "urgent") and best.intent != intent_was and best.intent in ("Taking data out", "Wrecking things")
        return Update(best, created, crossed or graver, was, now, best.weight, best.intent, best.stage, best.not_yet(), f)

    @staticmethod
    def _continues(c: Case, f: Finding) -> bool:
        """A later step of the same arc: it follows what the case has already shown (hiding, then taking out, then covering up)."""
        order = {b: i for i, (_, bs) in enumerate(ARC_STAGES) for b in bs}
        have = max((order.get(b, -1) for b in c.behaviours), default=-1)
        return order.get(f.behaviour, -2) >= have >= 0

    def note(self, f: Finding) -> Update:
        """Take a finding made elsewhere (the model's label on a rename) into the same cases, weighed as it comes."""
        return self._attach(f)

    def open_cases(self, *, pc: int | None = None, level: str | None = None) -> list[Case]:
        out = [c for c in self.cases if (pc is None or c.pc == pc) and (level is None or c.level == level)]
        return sorted(out, key=lambda c: c.weight, reverse=True)
