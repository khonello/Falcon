"""Anchors: the areas an intent covers, whatever the channel (stdlib only).

An intent is not a tool or a route; it is something a person is trying to get done, and everything they might do towards it falls in one of a few AREAS. Taking data
out covers gathering, reshaping, packing and sending; it does not matter whether the sending is a pen drive, a browser or a share, it falls in the same area.

An anchor is a definition of coverage, not a step. There is no order, none of them has to be filled, and filling more of them is not "getting further": it is only
more evidence. An event belongs to an area (it can belong to areas of several intents: what means little in one can mean a lot in another), and what an intent
weighs is the events that belong to its areas, each by its own weight (what was done, to what, by whom) -- one heavy event in one area is enough to matter, and
a number of light ones in one area add only a little. Covering more areas adds a little more. A count of files only ever amplifies.

Intents can contain other intents. Taking data out is partly gathering and partly hiding, so what falls in the areas of those counts toward it too (at a discount:
it is evidence of the bigger intent, not the whole of it). A single event is weighed once per intent it belongs to.

The bias is deliberate: a miss is worse than a false alarm. The price is paid by making a false alarm cheap to dismiss (a dismissal can be written down as a rule),
not by looking the other way.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Anchor:
    name: str
    says: str                       # what falls in this area, in plain words
    seen: bool = True               # False: an area we have no signal for yet (listed so nothing is pretended)


ANCHORS: dict[str, tuple[Anchor, ...]] = {
    "exfiltration": (
        Anchor("Gather", "files were pulled together"),
        Anchor("Transform", "something was changed so it would not look like what it is (renamed, converted, encrypted, hidden)"),
        Anchor("Compress", "files were packed into one"),
        Anchor("Transfer", "it was sent somewhere else: a drive, a share, the network"),
    ),
    "collection": (
        Anchor("Access", "files were opened or copied"),
        Anchor("Assemble", "files were brought together in one place"),
        Anchor("Consolidate", "they were packed into one"),
    ),
    "concealment": (
        Anchor("Disguise", "something was made to look like something else, or made hidden"),
        Anchor("Relocate", "it was moved where nobody looks"),
        Anchor("Protect", "it was locked or scrambled so others cannot read it"),
    ),
    "erasure": (
        Anchor("Remove", "something was deleted"),
        Anchor("Alter", "something was changed after the fact"),
        Anchor("Clear the trail", "the record of what happened was cleared"),
        Anchor("Switch off the record", "the thing that records was stopped", seen=False),
    ),
    "capture": (
        Anchor("Open the source", "restricted material was in front of the person"),
        Anchor("Capture", "a picture or recording of the screen was made"),
        Anchor("Keep", "the picture was saved as a file"),
        Anchor("Pass on", "the picture was sent somewhere"),
    ),
    "evasion": (
        Anchor("Test", "the watch was probed", seen=False),
        Anchor("Switch off", "the watch was stopped, or the machine went quiet"),
        Anchor("Dodge", "the work was moved where it is not watched", seen=False),
    ),
    "sabotage": (
        Anchor("Reach", "something that matters was touched"),
        Anchor("Disable safety nets", "a backup or a copy that would allow recovery was removed"),
        Anchor("Destroy", "something was deleted, scrambled, rewritten or locked"),
    ),
    "reach": (
        Anchor("Find", "someone looked at what is not theirs"),
        Anchor("Beyond role", "more files outside this person's work were opened"),
        Anchor("Widen", "it spread over several places"),
        Anchor("Return", "it happened again, another day"),
    ),
}

# an intent that is partly made of others: what falls in the children's areas counts toward the parent, at a discount
INCLUDES: dict[str, tuple[str, ...]] = {
    "exfiltration": ("collection", "concealment", "capture"),
    "sabotage": ("erasure",),
}
CHILD_SHARE = 0.6                  # a child's evidence is this much of the weight it would have in its own intent
AREA_CAP = 0.18                    # many light events in one area never add up past this by number alone (a heavy single event still counts at its own weight)
LIGHT = 0.12                       # an area below this has only trivial things in it
UNLINKED = 0.3                     # how much of the rest counts when the areas share no file, only the time
BREADTH = 0.04                     # each further area covered adds this much evidence (more kinds of thing, not "further along")

# how high coverage may go while it is only part of the picture: collecting alone is not harm, looking around is noted until it comes back another day
CEILING: dict[str, float] = {"collection": 0.55, "concealment": 0.70, "reach": 0.55, "evasion": 0.70}
DEFAULT_CEILING = 0.92


def anchor_names(behaviour: str) -> list[str]:
    return [a.name for a in ANCHORS.get(behaviour, ())]


def coverage(behaviour: str, own: dict[str, list[float]], children: dict[str, list[float]] | None = None, linked: bool = True) -> tuple[float, list[str]]:
    """How strongly an intent is covered, from the weights of the events in each of its areas (`own`: area -> weights) and in its children's areas (`children`:
    "child/Area" -> weights). Returns (weight, the areas covered, own first). No area is required and none comes first."""
    parts: list[tuple[str, float]] = []
    for area, ws in own.items():
        if ws:
            parts.append((area, _area(ws)))
    for key, ws in (children or {}).items():
        if ws:
            parts.append((key, _area(ws) * CHILD_SHARE))
    if not parts:
        return 0.0, []
    # an area with only trivial things in it (a photo on a drive, a zip of one's own working files, a download filed) is covered, but counts for very little: a whole
    # ordinary day touches several areas lightly, and that must not add up to something
    parts = [(a, w if w >= LIGHT else w * 0.4) for a, w in parts]
    rest = 1.0
    for _, w in parts:
        rest *= 1.0 - min(0.95, w)
    weight = (1.0 - rest) + BREADTH * max(0, sum(1 for _, w in parts if w >= LIGHT) - 1)
    covered = [a for a, _ in parts]
    if not linked:
        # areas that share no file and are only close in time are probably different pieces of work: the heaviest speaks, the rest add a little
        best = max(w for _, w in parts)
        weight = best + UNLINKED * (weight - best)
    return min(CEILING.get(behaviour, DEFAULT_CEILING), weight), covered


def _area(ws: list[float]) -> float:
    """One area: its heaviest event, or - when there are many - what they add up to, but numbers alone stop at AREA_CAP."""
    rest = 1.0
    for w in ws:
        rest *= 1.0 - min(0.95, w)
    return max(max(ws), min(AREA_CAP, 1.0 - rest))
