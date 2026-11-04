"""A flow's steps, as a tree (the user, 3 Nov 2026): a category, a kind, an operation, and a few settings.

    Per file (each file in, one or none out)
      Choosing     which files go:            by_type, by_name, by_size
      Conversion   what is inside changes:    to_pdf, to_docx, to_image, zip_each
      Renaming     the name changes:          add_date, add_text, replace_text
    All files (many in, one out)
      Bundling     the files become one:      zip, pdf

Placing (sorting into folders by type or month) was dropped: it was not obvious what it does. A flow made with it before keeps running; its
placing steps do nothing now.

The kinds always run in one order along a destination's path, whatever order they were added in:
    Choosing -> Conversion -> Renaming -> Bundling
so a step never meets a file in a shape it did not expect, and a bundle holds the files as the steps before it left them. A path has at
most one Bundling. Bundling makes one file from the whole folder at each run, so it is only in a flow that
runs hourly or when Run is pressed, from one folder.

Where each runs: Choosing on the Engine (a file not taken is never read from its source; by size once its content has arrived), the
rest on the destination machine (worker_client/flowsync.py, worker_client/convert.py). A Conversion a file cannot have (no Office or
LibreOffice there for a Word file, a damaged image) never stops the flow: the file is copied as it is, or left out (`if_not`), and said.

    catalogue() -> the tree with every setting's choices and default (flow.steps, for New flow)
    parse(stage_in) -> (stage_type, config)        a step from flow.create / flow.edit, checked; also the older {"op": "Rename by date"} form
    normal(stage) -> {stage_type, config} | None   what a stored step means now (None: it does nothing: a branch, or a dropped placing step)
"""

from __future__ import annotations

import re
from typing import Any

from protocol import ErrorCode, ProtocolError

GROUPS: dict[str, tuple[str, ...]] = {
    "text": ("txt", "md", "csv", "log"),
    "images": ("jpg", "jpeg", "png", "bmp", "gif", "tif", "tiff"),
    "word": ("doc", "docx", "rtf", "odt"),
    "excel": ("xls", "xlsx", "ods"),
    "powerpoint": ("ppt", "pptx", "odp"),
    "pdf": ("pdf",),
}
RANK = {"choosing": 0, "conversion": 1, "renaming": 2, "bundling": 3}
KINDS = tuple(RANK)
STAGE_TYPES = ("branch", *KINDS)
NAME_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
IF_NOT = {"choices": ["copy", "leave_out"], "default": "copy", "label": "When a file cannot be converted",
          "words": {"copy": "Copy it as it is", "leave_out": "Leave it out"}}


def _from(groups: list[str], default: list[str]) -> dict[str, Any]:
    return {"many": groups, "default": default, "label": "Which files"}


CATALOGUE: list[dict[str, Any]] = [
    {"category": "per_file", "label": "Per file", "says": "Each file in, one file (or none) out", "kinds": [
        {"kind": "choosing", "label": "Choosing", "says": "Which files the flow takes", "ops": [
            {"op": "by_type", "label": "By file type", "settings": {
                "types": {"list": "extension", "label": "File types", "required": True},
                "keep": {"choices": ["take", "leave"], "default": "take", "label": "These files", "words": {"take": "Take only these", "leave": "Leave these out"}}}},
            {"op": "by_name", "label": "By name", "settings": {
                "match": {"choices": ["contains", "starts_with", "ends_with"], "default": "contains", "label": "The name"},
                "text": {"text": 80, "label": "Text", "required": True},
                "keep": {"choices": ["take", "leave"], "default": "take", "label": "These files", "words": {"take": "Take only these", "leave": "Leave these out"}}}},
            {"op": "by_size", "label": "By size", "settings": {
                "is": {"choices": ["under", "over"], "default": "under", "label": "Take files"},
                "mb": {"number": [0.001, 100000], "label": "Size in MB", "required": True}}}]},
        {"kind": "conversion", "label": "Conversion", "says": "What is inside the file changes", "ops": [
            {"op": "to_pdf", "label": "To PDF", "settings": {"from": _from(["text", "images", "word", "excel", "powerpoint"], ["text", "images", "word", "excel", "powerpoint"]),
                                                            "if_not": IF_NOT},
             "needs": "Word, Excel and PowerPoint files need Office or LibreOffice on the destination machine"},
            {"op": "to_docx", "label": "To DOCX", "settings": {"from": _from(["text", "pdf"], ["text", "pdf"]), "if_not": IF_NOT},
             "needs": "PDF files need Office or LibreOffice on the destination machine, and come out rough: a PDF's layout does not survive exactly"},
            {"op": "to_image", "label": "To another image type", "settings": {
                "to": {"choices": ["jpg", "png"], "default": "jpg", "label": "Make them"},
                "quality": {"number": [1, 100], "default": 85, "label": "JPG quality"},
                "if_not": IF_NOT}},
            {"op": "zip_each", "label": "Zip each file", "settings": {}}]},
        {"kind": "renaming", "label": "Renaming", "says": "The name changes, the content does not", "ops": [
            {"op": "add_date", "label": "Add a date", "settings": {
                "date": {"choices": ["changed", "copied"], "default": "changed", "label": "Which date",
                         "words": {"changed": "When it was last changed", "copied": "When it was copied"}},
                "where": {"choices": ["before", "after"], "default": "before", "label": "Where"},
                "format": {"choices": ["yyyy-mm-dd", "dd-mm-yyyy", "yyyymmdd"], "default": "yyyy-mm-dd", "label": "Format"}}},
            {"op": "add_text", "label": "Add text", "settings": {
                "text": {"text": 40, "label": "Text", "required": True, "name": True},
                "where": {"choices": ["before", "after"], "default": "before", "label": "Where"}}},
            {"op": "replace_text", "label": "Replace text in the name", "settings": {
                "find": {"text": 40, "label": "Find", "required": True, "name": True},
                "with": {"text": 40, "label": "Replace with", "default": "", "name": True}}}]}]},
    {"category": "all_files", "label": "All files", "says": "Many files in, one out, at each run", "kinds": [
        {"kind": "bundling", "label": "Bundling", "says": "The files become one", "ops": [
            {"op": "zip", "label": "Into one ZIP", "settings": {
                "name": {"text": 80, "label": "Its name", "name": True},
                "dated": {"flag": True, "default": True, "label": "Add the date to its name"},
                "folders": {"choices": ["keep", "flatten"], "default": "keep", "label": "Folders inside it"}}},
            {"op": "pdf", "label": "Into one PDF", "settings": {
                "name": {"text": 80, "label": "Its name", "name": True},
                "dated": {"flag": True, "default": True, "label": "Add the date to its name"}},
             "needs": "Only PDF files go in, in name order; put a To PDF step before it for the rest"}],
         "needs": "Only in a flow that runs every hour or when you press Run, from one folder"}]}
]

OPS: dict[tuple[str, str], dict[str, Any]] = {(k["kind"], o["op"]): o for c in CATALOGUE for k in c["kinds"] for o in k["ops"]}

# The older names a console or a stored flow may still use (the five steps before the tree), and what each means now.
LEGACY: dict[str, tuple[str, str] | None] = {
    "Rename by date": ("renaming", "add_date"), "Convert to PDF": ("conversion", "to_pdf"), "Compress to ZIP": ("conversion", "zip_each"),
    "Sort by file type": None, "Sort by month": None,
}


def catalogue() -> list[dict[str, Any]]:
    return CATALOGUE


def _bad(why: str) -> ProtocolError:
    return ProtocolError(ErrorCode.INVALID, why)


def settings_for(kind: str, op: str, given: Any) -> dict[str, Any]:
    """The settings of one step, each checked against the catalogue and defaulted; unknown ones refused."""
    spec = OPS[(kind, op)]["settings"]
    given = given if isinstance(given, dict) else {}
    unknown = set(given) - set(spec)
    if unknown:
        raise _bad(f"{OPS[(kind, op)]['label']} has no setting {min(unknown)!r}")
    out: dict[str, Any] = {}
    for key, s in spec.items():
        value = given.get(key, s.get("default"))
        if value is None:
            if s.get("required"):
                raise _bad(f"{OPS[(kind, op)]['label']}: {s['label']} is needed")
            continue
        if "choices" in s:
            if value not in s["choices"]:
                raise _bad(f"{s['label']}: one of {', '.join(s['choices'])}")
        elif "many" in s:
            if not isinstance(value, list) or not value or any(v not in s["many"] for v in value):
                raise _bad(f"{s['label']}: some of {', '.join(s['many'])}")
            value = [v for v in s["many"] if v in value]
        elif "list" in s:
            if not isinstance(value, list) or not 1 <= len(value) <= 20:
                raise _bad(f"{s['label']}: 1 to 20 file types")
            value = sorted({str(v).strip().lower().lstrip(".") for v in value})
            if any(not re.fullmatch(r"[a-z0-9]{1,10}", v) for v in value):
                raise _bad(f"{s['label']}: file types are letters and digits, like pdf or xlsx")
        elif "text" in s:
            value = " ".join(str(value).split()) if s.get("name") is None else str(value)
            if len(value) > s["text"] or (s.get("required") and not value.strip()):
                raise _bad(f"{s['label']}: 1 to {s['text']} characters")
            if s.get("name") and NAME_BAD.search(value):
                raise _bad(f"{s['label']}: a file name cannot hold \\ / : * ? \" < > |")
        elif "number" in s:
            try:
                value = float(value)
            except (TypeError, ValueError) as exc:
                raise _bad(f"{s['label']}: a number") from exc
            lo, hi = s["number"]
            if not lo <= value <= hi:
                raise _bad(f"{s['label']}: {lo:g} to {hi:g}")
        elif "flag" in s:
            value = bool(value)
        out[key] = value
    return out


def parse(stage_in: dict[str, Any], i: int) -> tuple[str, dict[str, Any] | None]:
    """A step from flow.create / flow.edit -> (stage_type, config). New form: {"step": {kind, op, settings?}}. Older forms: {"stage_type":
    "branch"}, and {"config": {"op": "Rename by date"}} (the five steps before the tree)."""
    step = stage_in.get("step")
    if step is None:
        stype = stage_in.get("stage_type")
        config = stage_in.get("config") if isinstance(stage_in.get("config"), dict) else {}
        if stype == "branch":
            return "branch", config or None
        name = config.get("op")
        if stype in KINDS and (config.get("kind"), name) in OPS:      # a step as it is stored, sent back whole (an edit made from a flow as it stands)
            step = config
        elif name in LEGACY:
            meant = LEGACY[name]
            if meant is None:
                raise _bad(f"step {i}: {name} was dropped (placing steps are no longer offered)")
            step = {"kind": meant[0], "op": meant[1]}
        elif stype in ("categorization",):
            raise _bad(f"step {i}: placing steps were dropped")
        elif stype == "transformation" and (meant_now := normal({"stage_type": stype, "config": config})) is not None:
            return meant_now["stage_type"], meant_now["config"]
        else:
            raise _bad(f"step {i}: name a step as {{kind, op, settings}} (flow.steps lists them)")
    if not isinstance(step, dict):
        raise _bad(f"step {i}: a step is {{kind, op, settings}}")
    kind, op = step.get("kind"), step.get("op")
    if (kind, op) not in OPS:
        raise _bad(f"step {i}: {kind}.{op} is not a step (flow.steps lists them)")
    return str(kind), {"kind": kind, "op": op, "label": OPS[(kind, op)]["label"], "settings": settings_for(str(kind), str(op), step.get("settings"))}


def normal(stage: dict[str, Any]) -> dict[str, Any] | None:
    """What a stored step means now, as the Worker reads it: {"stage_type": kind, "config": {kind, op, label, settings}}. A step stored before
    the tree is read in its new name with the settings it had; a placing step, and a branch, mean nothing to a file (None)."""
    stype, config = stage.get("stage_type"), dict(stage.get("config") or {})
    if stype in KINDS and (config.get("kind"), config.get("op")) in OPS:
        return {"stage_type": stype, "config": config}
    if stype == "transformation":
        if config.get("op") == "Rename by date" or config.get("rename") == "date":
            kind, op, settings = "renaming", "add_date", {}
        elif config.get("op") == "Compress to ZIP" or config.get("pack") == "zip":
            kind, op, settings = "conversion", "zip_each", {}
        elif config.get("op") == "Convert to PDF" or str(config.get("to", "")).lower().lstrip(".") == "pdf":
            kind, op, settings = "conversion", "to_pdf", {}
        else:
            return None                                           # (the early text-to-text conversions: a copy as it is)
        return {"stage_type": kind, "config": {"kind": kind, "op": op, "label": OPS[(kind, op)]["label"], "settings": settings_for(kind, op, settings)}}
    return None


def check_path(chain: list[dict[str, Any]]) -> None:
    """The steps on one destination's path: in the kinds' order, at most one Bundling."""
    kinds = [s["stage_type"] for s in chain]
    if kinds != sorted(kinds, key=RANK.__getitem__):
        raise _bad("steps run in this order: Choosing, Conversion, Renaming, Bundling; put them in that order")
    if kinds.count("bundling") > 1:
        raise _bad("a destination's path has at most one Bundling step")


def bundles(chains: list[list[dict[str, Any]]]) -> bool:
    return any(s["stage_type"] == "bundling" for c in chains for s in c)


# --- Choosing, on the Engine -----------------------------------------------------------------------------------------------------------

def ext_of(name: str) -> str:
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def chosen(chain: list[dict[str, Any]], relative_path: str, size: int | None = None) -> bool:
    """Does this file go down this path? Every Choosing step on it must take it. By size is decided only once the size is known (None: not yet)."""
    name = relative_path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    for st in chain:
        if st["stage_type"] != "choosing":
            continue
        cfg, s = st["config"], st["config"]["settings"]
        if cfg["op"] == "by_type":
            hit = ext_of(name) in s["types"]
        elif cfg["op"] == "by_name":
            text = s["text"].lower()
            hit = {"contains": text in name, "starts_with": name.startswith(text), "ends_with": name.rsplit(".", 1)[0].endswith(text) or name.endswith(text)}[s["match"]]
        else:
            if size is None:
                continue
            limit = s["mb"] * 1_000_000
            hit = size < limit if s["is"] == "under" else size > limit
            if not hit:
                return False
            continue
        if hit != (s["keep"] == "take"):
            return False
    return True


def bundle_name(config: dict[str, Any], flow_name: str | None, today: str) -> str:
    """The bundle's file name: its name (the flow's, when none was given), the date when asked, and .zip or .pdf."""
    s = config["settings"]
    base = (s.get("name") or flow_name or "bundle").strip() or "bundle"
    base = NAME_BAD.sub("-", base)
    if s.get("dated", True):
        base = f"{base} {today}"
    return f"{base}.{'pdf' if config['op'] == 'pdf' else 'zip'}"
