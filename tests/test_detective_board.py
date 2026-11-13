"""Detective's board kept as it grows (common/detective.py `_Board`), against the way it was worked out before: from the whole board, on every event.

Rebuilding the pieces of work from every hit on every event made one busy machine cost 42 ms an event, enough to hold the single-threaded Engine (12 Nov 2026). The
pieces are now kept as hits arrive. These tests keep the old way as the reference: on random boards, every piece must come out the same (members, weight, areas in
order, linked, things, latest events), built one event at a time or in one pass after a trim.
"""

from __future__ import annotations

import itertools
import random
import time

from common.anchors import ANCHORS, INCLUDES, coverage
from common.detective import THREAD, Detective, Hit, Memory, Sig, _Board

AREAS = {b: [a.name for a in anchors] for b, anchors in ANCHORS.items()}


def _reference(behaviour: str, hits: list[Hit]) -> dict[frozenset[int], tuple]:
    """The pieces of one intent's board as the code worked them out before 12 Nov 2026 (from `Detective._coverage`, every hit, every time)."""
    family = {behaviour, *INCLUDES.get(behaviour, ())}
    mine = [h for h in hits if h.behaviour in family]
    parent = list(range(len(mine)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    by_time = sorted(range(len(mine)), key=lambda i: mine[i].at)
    for a, b in itertools.pairwise(by_time):
        if mine[b].at - mine[a].at <= THREAD:
            union(b, a)
    first_with: dict[str, int] = {}
    holders: dict[str, int] = {}
    for i, h in enumerate(mine):
        for t in h.things:
            if t in first_with:
                union(i, first_with[t])
                holders[t] += 1
            else:
                first_with[t], holders[t] = i, 1
    shared = {i for i, h in enumerate(mine) if any(holders[t] > 1 for t in h.things)}
    groups: dict[int, list[int]] = {}
    for i in range(len(mine)):
        groups.setdefault(find(i), []).append(i)
    out = {}
    for idx in groups.values():
        comp = [mine[i] for i in idx]
        own: dict[str, list[float]] = {}
        kids: dict[str, list[float]] = {}
        mine_sigs = {h.sig for h in comp if h.behaviour == behaviour}
        for h in comp:
            if h.behaviour == behaviour:
                own.setdefault(h.anchor, []).append(h.weight)
            elif h.sig not in mine_sigs:
                kids.setdefault(f"{h.behaviour}/{h.anchor}", []).append(h.weight)
        linked = any(i in shared for i in idx)
        w, covered = coverage(behaviour, own, kids, linked or len(comp) == 1)
        out[frozenset(idx)] = (round(w, 9), covered, linked, bool(own), frozenset().union(*(h.things for h in comp)), round(min(h.at for h in comp), 6),
                               {s.at for s in sorted({h.sig for h in comp}, key=lambda x: x.at)[-14:]})
    return out


def _pieces(board: _Board) -> dict[frozenset[int], tuple]:
    members: dict[int, list[int]] = {}
    for i in range(len(board.hits)):
        members.setdefault(board.find(i), []).append(i)
    out = {}
    for root, idx in members.items():
        p = board.piece[root]
        assert p.size == len(idx)
        w, covered = p.weigh(board.behaviour)
        out[frozenset(idx)] = (round(w, 9), covered, p.linked, bool(p.own), frozenset(p.things), round(p.first_at, 6), {s.at for s in p.sigs})
    return out


def _random_batches(seed: int, n: int, gap: float) -> list[list[Hit]]:
    """Events, each with one or more hits in random intents and areas, sharing files now and then; some arrive late, and some reuse an earlier event."""
    rnd = random.Random(seed)
    t, out, sigs = 1_700_000_000.0, [], []
    for _ in range(n):
        t += rnd.random() * gap
        at = t - (rnd.random() * 3 * THREAD if rnd.random() < 0.05 else 0.0)
        s = rnd.choice(sigs) if sigs and rnd.random() < 0.03 else Sig(at, 1, "created", f"C:\\f{rnd.randint(0, 99)}.docx", thing=f"h{rnd.randint(0, 300)}")
        sigs.append(s)
        batch = []
        for _ in range(rnd.choice((1, 1, 2, 3))):
            b = rnd.choice(list(AREAS))
            things = frozenset({s.thing} | ({f"h{rnd.randint(0, 300)}"} if rnd.random() < 0.3 else set()))
            batch.append(Hit(b, rnd.choice(AREAS[b]), s.at, round(rnd.random() * 0.4, 3), things, s))
        out.append(batch)
    return out


def test_pieces_kept_as_hits_arrive_are_the_pieces_worked_out_from_the_whole_board():
    for seed, n, gap in ((1, 400, 60.0), (2, 600, 900.0), (3, 300, 4000.0), (4, 500, 5.0)):
        batches = _random_batches(seed, n, gap)
        hits = [h for b in batches for h in b]
        for behaviour in ANCHORS:
            board = _Board(behaviour)
            for batch in batches:
                board.add(batch)
            want = _reference(behaviour, hits)
            assert _pieces(board) == want, (seed, behaviour)
            assert _pieces(_Board.built(behaviour, batches)) == want, (seed, behaviour)


def test_a_full_board_is_trimmed_in_batches_and_comes_out_as_if_built_from_what_is_kept():
    m = Memory()
    batches = _random_batches(5, 5200, 2.0)
    for batch in batches:
        m.add_hits(batch, batch[0].at)
    assert 4000 <= len(m.hits) <= 4500
    for behaviour, board in m.boards.items():
        assert _pieces(board) == _reference(behaviour, m.hits), behaviour


def test_one_busy_machine_costs_well_under_a_millisecond_an_event_and_never_holds_the_engine():
    """The measurement that found it (12 Nov 2026): 10,000 events on one machine, about one a second. Before: 42 ms an event once the board was full."""
    rnd = random.Random(1)
    verbs = ["created", "modified", "renamed", "deleted", "copied", "opened", "moved"]
    folders = [r"C:\Users\ama\Documents", r"C:\Users\ama\Desktop", r"C:\Users\ama\Downloads", r"C:\Users\ama\Documents\Finance", r"E:\backup"]
    exts = [".docx", ".xlsx", ".pdf", ".txt", ".zip", ".png", ".csv"]
    det, t, took = Detective(clock=lambda: 1_700_000_000.0), 1_700_000_000.0, []
    for _ in range(10_000):
        t += rnd.random() * 2
        v = rnd.choice(verbs)
        old = f"{rnd.choice(folders)}\\file{rnd.randint(0, 3000)}{rnd.choice(exts)}" if v in ("renamed", "moved") else ""
        s = Sig(t, 1, v, f"{rnd.choice(folders)}\\file{rnd.randint(0, 3000)}{rnd.choice(exts)}", old, f"h{rnd.randint(0, 5000)}", "",
                rnd.choice(["hand", "started", "alone"]), "", frozenset({"restricted"}) if rnd.random() < 0.03 else frozenset())
        t0 = time.perf_counter()
        det.feed(s)
        took.append(time.perf_counter() - t0)
    took.sort()
    assert took[len(took) // 2] < 0.004, f"median {took[len(took) // 2] * 1000:.2f} ms"      # ~0.6 ms here; generous for a slow test machine
    assert took[-1] < 0.5, f"worst {took[-1] * 1000:.0f} ms"
