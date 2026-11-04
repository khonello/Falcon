"""A case told in words (ENGINE-GAPS #15, the user's decision 3 Nov 2026: way (a), then a pass to make it read naturally).

The account is written by the Engine, not by the model. Every fact in it (who was signed in, the machine, each time, file, folder, drive,
program, count and how long it lasted, and the rules' own reasons) is filled in from the case. Each one is a part the console marks, the
way the task box marks people and files. Around the facts are plain joining words.

Then, when `SMOOTHING` is on (it is off: see below) and the model is here, it may smooth one paragraph at a time so it reads less like a form. It never sees the facts. It sees each one
as a marker that says what kind of fact it is ([person1], [file2], [time3]...) and is told to keep every marker once and to add nothing.
Its paragraph is used only when a check finds every marker still there once, each still with the facts of its own sentence and the
sentences in their order (inside a sentence, facts of different kinds may change places: `_same_facts`), and finds no new number, no new name (a capitalised word), no change in
how many times it says "not", no word of blame or of intent ("on purpose", "to hide", "stole", "probably"), and a length close to the
original. A paragraph that fails is kept as the Engine wrote it. The markers are filled in only after the check, so a fact can never be
changed by the model. Only the joining words between them can.

The smoothed paragraphs are kept with the case (`detective_cases.telling`), with markers in place of facts and a fingerprint of the
account they were made from. People are filled in per viewer, from that viewer's own display names, so one smoothing serves everyone. When
the case grows, the fingerprint no longer matches: the Engine's own account is shown and the model is asked again in the background.

    compose(case, findings, sessions, hostname) -> Telling     the account, built from the case alone
    smooth(llm, telling) -> list[str | None]                    the model's paragraphs that passed the check (None: keep the Engine's)
    checked(skeleton, rewrite) -> bool                          the check
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from common.detective import Sig, folder_of, megabytes, name_of

MAX_STEPS = 8                       # what happened, run by run; beyond this "and N more steps"
MAX_REASONS = 4
MAX_INNOCENT = 3
SMOOTH_TOKENS = 320

NOTE = "Detective's reading of the evidence, not proof."

# Off (4 Nov 2026): measured on 8 paragraphs, the 1.7B handed all 8 back unchanged, and with a worked example (below) improved 2, spoiled 2 and
# still copied the events paragraph, at about 13 s each, with Task proposals queued behind it. The Engine's own account is what is shown.
# tests/test_llm_real.py has the bar a model must clear before this is switched on.
SMOOTHING = False

INSTRUCTION = (
    "Turn the stiff notes below into natural English, the way a colleague would tell it. Join sentences with words like then, after that, and, a little later. "
    "Words in square brackets such as [time1] or [file2] are placeholders: copy each one exactly, each one once, and keep them with the same event. "
    "Tell the events in the same order. Add no facts and no reasons.\n\n"
    "Example notes: At [time1], [file2] was opened. At [time3], [file4] was deleted.\n"
    "Example answer: [file2] was opened at [time1], and then [file4] was deleted a little later, at [time3].\n\n"
    "Now do the same for these notes. Reply with only the new text.")

# Words that judge or guess at a reason: the account says what happened, never why or who is to blame. Refused in a rewrite unless the
# Engine's own paragraph already had them.
BLAME = ("deliberately", "deliberate", "intentionally", "intentional", "on purpose", "purposely", "purposefully", "clearly", "obviously",
         "stole", "steal", "stealing", "theft", "thief", "guilty", "malicious", "criminal", "suspicious", "suspect", "suspected", "illegal",
         "probably", "likely", "presumably", "apparently", "must have", "seems", "seemed", "in order to", "so that", "because", "trying to",
         "tried to", "wanted to", "attempt", "attempted", "to hide", "to cover", "cover up", "covered up", "secretly", "sneak", "sneaked",
         "snuck", "wrongdoing", "breach", "leak", "leaked")
NEGATIONS = re.compile(r"\b(not|no|never|nothing|nobody|none|without|neither|nor)\b|n't\b", re.IGNORECASE)
MARKER = re.compile(r"\[([a-z]+)(\d+)\]")          # [person1], [file2]: what kind of fact, and which one
SHAPE = "2"                                        # how the markers look; part of the fingerprint, so a smoothing in an older shape is made again


@dataclass
class Fact:
    kind: str                       # person machine time duration file folder drive program count amount reason intent tag
    text: str                       # how it reads (a person's is filled in per viewer)
    value: Any = None               # what it stands for: an account id, an ISO time, a path

    def key(self) -> list[Any]:
        return [self.kind, self.text if self.kind != "person" else "", self.value]


@dataclass
class Telling:
    paragraphs: list[list[str | Fact]] = field(default_factory=list)

    def skeletons(self) -> list[str]:
        """Each paragraph with its facts as markers [person1], [file2]... (its kind, and a number from 1 within the paragraph): what the model sees."""
        out = []
        for para in self.paragraphs:
            n, said = 0, []
            for p in para:
                if isinstance(p, Fact):
                    n += 1
                    said.append(f"[{p.kind}{n}]")
                else:
                    said.append(p)
            out.append("".join(said))
        return out

    def facts(self, i: int) -> list[Fact]:
        return [p for p in self.paragraphs[i] if isinstance(p, Fact)]

    def fingerprint(self) -> str:
        what = [[p if isinstance(p, str) else p.key() for p in para] for para in self.paragraphs]
        return hashlib.sha256(json.dumps([SHAPE, what], default=str).encode("utf-8")).hexdigest()[:32]

    def view(self, names: dict[int, str | None], smoothed: list[str | None] | None = None) -> dict[str, Any]:
        """The account as the console gets it: paragraphs of parts ({text} or {text, kind, value}), each from the model's smoothing when that
        passed the check, else the Engine's own; people filled in from the viewer's own names."""
        paras: list[list[dict[str, Any]]] = []
        used = False
        for i, para in enumerate(self.paragraphs):
            facts = [self._shown(f, names) for f in self.facts(i)]
            rewrite = smoothed[i] if smoothed and i < len(smoothed) else None
            if rewrite:
                used = True
                parts: list[dict[str, Any]] = []
                at = 0
                for m in MARKER.finditer(rewrite):
                    if m.start() > at:
                        parts.append({"text": rewrite[at:m.start()]})
                    parts.append(facts[int(m.group(2)) - 1])
                    at = m.end()
                if at < len(rewrite):
                    parts.append({"text": rewrite[at:]})
            else:
                parts = []
                k = 0
                for p in para:
                    if isinstance(p, Fact):
                        parts.append(facts[k])
                        k += 1
                    else:
                        parts.append({"text": p})
            paras.append(parts)
        text = "\n\n".join("".join(p["text"] for p in para) for para in paras)
        return {"paragraphs": paras, "text": text, "smoothed": used, "note": NOTE}

    @staticmethod
    def _shown(f: Fact, names: dict[int, str | None]) -> dict[str, Any]:
        text = f.text
        if f.kind == "person":
            text = names.get(f.value) or f"account {f.value}"
        return {"text": text, "kind": f.kind, "value": f.value}


# --- the account, from the case alone ------------------------------------------------------------------------------------------------------

def _clock(ts: float, with_day: bool) -> Fact:
    t = time.localtime(ts)
    shown = time.strftime("%H:%M", t)
    if with_day:
        shown += " on " + time.strftime("%a ", t) + str(t.tm_mday) + time.strftime(" %b", t)
    return Fact("time", shown, time.strftime("%Y-%m-%dT%H:%M:%S", t))


def lasted(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return "under a minute"
    if s < 3600:
        m = round(s / 60)
        return f"{m} minute{'s' if m != 1 else ''}"
    if s < 2 * 86400:
        h, m = divmod(round(s / 60), 60)
        return f"{h} hour{'s' if h != 1 else ''}" + (f" {m} minute{'s' if m != 1 else ''}" if m else "")
    d = round(s / 86400)
    return f"{d} days"


def _file(path: str) -> Fact:
    return Fact("file", name_of(path) or path, path)


def _folder(path: str) -> Fact:
    f = folder_of(path)
    return Fact("folder", f or "another place", f or None)


def _step(e: Sig) -> list[str | Fact]:
    """One thing that happened, in a passive sentence (who did it is said once, above, from the sessions)."""
    v = e.verb
    out: list[str | Fact]
    if v == "created":
        out = [_file(e.path), " was created"]
    elif v == "modified":
        out = [_file(e.path), " was changed"]
    elif v == "renamed":
        out = [_file(e.old), " was renamed to ", _file(e.path)]
    elif v == "moved":
        out = [_file(e.path), " was moved to ", _folder(e.path)]
    elif v == "copied":
        out = [_file(e.path), " was copied to ", _folder(e.path)]
    elif v == "deleted":
        out = [_file(e.path), " was deleted"]
    elif v == "opened":
        out = [_file(e.path), " was opened"]
    elif v == "hid":
        out = [_file(e.path), " was hidden"]
    elif v == "unhid":
        out = [_file(e.path), " was made visible again"]
    elif v == "permissions":
        out = ["who may open ", _file(e.path), " was changed"]
    elif v == "attached":
        label = str(e.info.get("label") or "")
        out = ["a drive was plugged in (", Fact("drive", f"{label}, {e.device}" if label else (e.device or "a drive"), e.device or None), ")"]
    elif v == "detached":
        out = ["the drive ", Fact("drive", e.device or "a drive", e.device or None), " was removed"]
    elif v == "uploaded":
        out = [Fact("program", e.program or "a program", e.program or None), " sent ", Fact("amount", megabytes(e.info.get("bytes")), e.info.get("bytes")),
               " out over the network"]
    elif v == "launched":
        out = [Fact("program", e.program or "a program", e.program or None), " was started"]
    elif v == "exited":
        out = [Fact("program", e.program or "a program", e.program or None), " was closed"]
    elif v == "captured":
        kind = e.info.get("kind")
        out = ["a picture of the whole screen was taken" if kind == "screen" else "a picture was put on the clipboard" if kind == "region" else "the screen was captured"]
        if e.program:
            out += [" with ", Fact("program", e.program, e.program)]
    elif v == "cleared":
        what = str(e.info.get("what") or "a history")
        out = [Fact("reason", what, None), " was cleared"]
    elif v == "silent":
        out = ["the machine stopped reporting while still switched on"]
    else:
        out = [_file(e.path) if e.path else Fact("reason", e.name or v, None), f" ({v})"]
    if "restricted" in e.tags and e.path:
        out += [", ", Fact("tag", "a restricted file", "restricted")]
    return out


def _runs(sigs: list[Sig]) -> list[list[Sig]]:
    """Runs of the same step in one folder, close together, read as one (the same grouping as Case.story)."""
    runs: list[list[Sig]] = []
    for e in sigs:
        last = runs[-1][-1] if runs else None
        if (last is not None and e.verb == last.verb and e.verb in ("copied", "opened", "deleted", "created", "moved")
                and folder_of(e.path) == folder_of(last.path) and e.at - last.at <= 90):
            runs[-1].append(e)
        else:
            runs.append([e])
    return runs


def _upper(first: str | Fact) -> str | Fact:
    return first[:1].upper() + first[1:] if isinstance(first, str) else first


def _joined(items: list[list[str | Fact]], word: str = "and") -> list[str | Fact]:
    out: list[str | Fact] = []
    for i, item in enumerate(items):
        if i:
            out.append(", " if i < len(items) - 1 else f" {word} ")
        out += item
    return out


def compose(case: dict[str, Any], findings: list[dict[str, Any]], sessions: list[dict[str, Any]], hostname: str | None) -> Telling:
    """The account of one case from what the Engine keeps: the case row, its findings (with their evidence), who was signed in when it began
    (`SessionsRepo.signed_in_at`), and the machine's name."""
    from common.detective import sig_from_dict

    seen: set[Sig] = set()
    sigs = sorted((e for f in findings for e in (sig_from_dict(x) for x in (f.get("evidence") or [])) if not (e in seen or seen.add(e))),
                  key=lambda e: e.at)
    first = case["first_at"].timestamp() if case.get("first_at") else (sigs[0].at if sigs else time.time())
    last = case["last_at"].timestamp() if case.get("last_at") else (sigs[-1].at if sigs else first)
    days = last - first >= 18 * 3600
    machine = Fact("machine", hostname or f"machine {case.get('pc_id')}", case.get("pc_id"))
    t = Telling()

    # who, where, when, how long
    who: list[str | Fact]
    own = [s for s in sessions if s.get("occupied_via") == "native"]
    entered = [s for s in sessions if s.get("occupied_via") != "native"]
    if own:
        who = _joined([[Fact("person", "", s["occupant_account_id"])] for s in own]) + [" was signed in on " if len(own) == 1 else " were signed in on ", machine]
    else:
        who = ["Nobody was signed in on ", machine, " in their own name"]
    p1: list[str | Fact] = [*who, " when this began, at ", _clock(first, True), "."]
    if entered:
        p1 += [" ", *_joined([[Fact("person", "", s["occupant_account_id"])] for s in entered]), " had entered it from the console."]
    p1 += [" It went on for ", Fact("duration", lasted(last - first), int(last - first)), ", until ", _clock(last, days), "."] if last - first >= 60 \
        else [" It was over within ", Fact("duration", "a minute", int(last - first)), "."]
    t.paragraphs.append(p1)

    # what happened, in order
    runs = _runs(sigs)
    p2: list[str | Fact] = []
    for run in runs[:MAX_STEPS]:
        if p2:
            p2.append(" ")
        p2 += ["At ", _clock(run[0].at, days), ", "]
        if len(run) > 2:
            verb = run[0].verb
            p2 += [Fact("count", str(len(run)), len(run)), f" files were {verb} ", "to " if verb in ("copied", "moved") else "in ", _folder(run[0].path)]
            if any("restricted" in e.tags for e in run):
                p2 += [", ", Fact("tag", "some of them restricted", "restricted")]
        else:
            for k, e in enumerate(run):
                if k:
                    p2.append(" and ")
                p2 += _step(e)
        p2.append(".")
    if len(runs) > MAX_STEPS:
        more = sum(len(r) for r in runs[MAX_STEPS:])
        p2 += [" After that came ", Fact("count", str(more), more), f" more step{'s' if more != 1 else ''}."]
    if p2:
        t.paragraphs.append(p2)

    # why it is worth a look: the rules' own reasons, word for word
    top = sorted((f for f in findings if not str(f.get("graph") or "").startswith("coverage_") and f.get("summary")), key=lambda f: float(f.get("weight") or 0),
                 reverse=True)[:MAX_REASONS]
    reasons = list(dict.fromkeys(str(f["summary"]) for f in sorted(top, key=lambda f: f["at"])))
    p3: list[str | Fact] = ["Detective reads this as ", Fact("intent", str(case.get("intent") or "unusual activity"), case.get("intent")), "."]
    if reasons:
        p3 += [" What makes it worth a look: ", *_joined([[Fact("reason", r, None)] for r in reasons]), "."]
    if case.get("not_yet"):
        p3 += [" ", Fact("reason", str(case["not_yet"]), "not_yet")]
    t.paragraphs.append(p3)

    # what would make it innocent
    innocent = list(dict.fromkeys(str(f["innocent"]) for f in findings if f.get("innocent")))[:MAX_INNOCENT]
    if innocent:
        t.paragraphs.append(["It could be harmless: ", *_joined([[Fact("reason", x, None)] for x in innocent], "or"), "."])
    for para in t.paragraphs:
        para[0] = _upper(para[0])
    return t


# --- the model's pass, and the check -------------------------------------------------------------------------------------------------------

def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z' ]+", " ", MARKER.sub(" ", text).lower()) + " "


def _names(text: str) -> set[str]:
    """Capitalised words that are not the first word of a sentence: names, as far as plain text can tell."""
    out: set[str] = set()
    for sentence in re.split(r"(?<=[.!?:;])\s+|\n+", MARKER.sub(" x ", text)):
        words = re.findall(r"[A-Za-z][\w'-]*", sentence)
        out |= {w for w in words[1:] if w[0].isupper()}
    return out


def _same_facts(skeleton: str, rewrite: str) -> bool:
    """Every fact once, still with the others it was said with. Each sentence of the Engine's paragraph is one unit; in the rewrite the
    units come in their order (the story keeps the order it happened in), each unit's markers together (a time never moves to another
    event). Inside a unit, facts of different kinds may change places ("[count2] files went to [folder3] at [time1]"); two of the same
    kind keep theirs (two files never swap folders). Merging or splitting sentences is fine: only the markers' order is read."""
    got = MARKER.findall(rewrite)
    units = [u for u in (MARKER.findall(s) for s in re.split(r"(?<=[.!?])\s+", skeleton)) if u]
    if len(got) != sum(len(u) for u in units):
        return False
    at = 0
    for unit in units:
        part = got[at:at + len(unit)]
        at += len(unit)
        if sorted(part) != sorted(unit):
            return False                                          # a fact lost, repeated, its kind changed, or moved to another sentence's place
        if any([n for k, n in part if k == kind] != [n for k, n in unit if k == kind] for kind in {k for k, _ in unit}):
            return False                                          # two facts of one kind swapped
    return True


def checked(skeleton: str, rewrite: str) -> bool:
    """Is the model's paragraph the same account in other joining words? See the module's docstring for what is checked."""
    if not rewrite or "\n\n" in rewrite.strip() or not _same_facts(skeleton, rewrite):
        return False
    if re.search(r"\d", MARKER.sub("", rewrite)) or re.search(r"[\[\]{}<>*#]", MARKER.sub("", rewrite)):
        return False                                              # a number the case did not give, or markup
    if _names(rewrite) - _names(skeleton) - {"I"}:
        return False
    if len(NEGATIONS.findall(rewrite)) != len(NEGATIONS.findall(skeleton)):
        return False                                              # "has not left" must not become "has left"
    was, now = _words(skeleton), _words(rewrite)
    if any(f" {w} " in now and f" {w} " not in was for w in BLAME):
        return False
    plain = len(MARKER.sub("", skeleton))
    return 0.5 * plain - 20 <= len(MARKER.sub("", rewrite)) <= 1.6 * plain + 60


async def smooth(llm: Any, telling: Telling) -> list[str | None]:
    """Each paragraph the model rewrote and the check passed; None where it did not (or the model is away)."""
    out: list[str | None] = []
    for skeleton in telling.skeletons():
        said = None
        if getattr(llm, "available", False) and hasattr(llm, "rewrite"):
            said = await llm.rewrite(INSTRUCTION, skeleton, max_tokens=SMOOTH_TOKENS)
        said = " ".join(said.split()) if said else None
        out.append(said if said and said != skeleton and checked(skeleton, said) else None)
    return out
