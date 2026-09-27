# The patterns that work — measured, so other pages can borrow them

Written 27 Sep 2026, after the rethought batch 1 and 2 (`HO03`, `FL06`–`FL08`, `AS03`, `RP03`, `RC02`–`CP02`) drew
*"Much much better, honestly, they all work well."* This is the reference to fix any page against. Every size
here is in CSS px on the 1440 × 900 board, and is what the QML should reproduce. Source: `design/batch1b_pages.py`,
`design/batch2b_mood.py`, `design/work_pages.py`, `design/actions_pages.py`.

Read with `DECISIONS.md` (what was rejected — 3c especially) and the Overview's rules there.

---

## 1. The page

| Part | Measure |
|---|---|
| Crumb | 12.5 px; current step white 600, the rest faint 400; a 12 px chevron between |
| Title | 24 px, bold, letter-spacing −0.3; beside it a **state phrase** 13 px in the page's tone ("seven machines · three need you") |
| Clock | right of the title, 12.5 px faint |
| Cells | the Overview's `kcell`: title 15 px white 600 **above** the cell on the frame, a ≤ 6-word state phrase right-aligned 12.5 px in tone; surface radius 18, padding 22 |
| Gaps | 20 between cells, 12 between page bands |
| Composition | **four cells**, widths doing the ranking (900 + 440, 620 + 720, 1360 over 520/420/380). Each page has its own signature — a band over three, a wide right column, a hero and a column, three columns, a tall queue and three |

## 2. The machine mark — a small screen

The one mark for a PC, everywhere. `calm_slot(label, state, size, sub)`.

- **Shape:** a rounded rectangle 1.5 px outline, `size` wide × `size·0.66` tall, radius `max(3, size·0.1)`, with a
  short stand and foot beneath (together +9 px). Fill is almost nothing (rgba white 0.03).
- **The number** sits inside, mono, `size·0.24` px, 600.
- **Quiet** (fine): outline rgba white 0.30, number `dim`. **Free / unused:** the same at 45 % opacity — unused is
  not a problem. **Needs someone:** outline and number take the tone (warn, danger); nothing else changes.
- **The reason is words beneath**, never a dot: name 12.5 px ink 600, then the line 11 px in tone
  ("a version behind"), centred, in a 150 px column.

**Sizes that work**

| Where | size | column | gap |
|---|---|---|---|
| The hero row of a page (Admin home) | **84** | 150 | 30 |
| Maximised chart | 58 | — | 14 |
| Inside a card beside words (machine, live) | 56 | — | 12 |
| A fleet line per department | 24 | — | 5 |
| A screen next to a line of text | 30–34 | — | 8–10 |

**At 84 it reads best — keep it there.** Do not shrink it to fit more machines; page instead (§3).

## 3. Paging, not shrinking — supersedes `DP10`

*The user, 27 Sep 2026: "instead of making things small when the pcs are many, it can be like clicking the far
right on the container scrolls horizontally to reveal next 4 or 2 pcs, same behavior when we click left."*

This **replaces** the `DP10` rule (shrink 46 → 30 → 16 → bars, never scroll) for rows of machines:

- The row keeps the **full-size mark** (84 on a page, 58 maximised). As many as fit are shown.
- **The container's far right edge is a hot zone**: clicking it slides the row left to reveal the next **4** machines
  (or **2** where the row is narrow). The far left edge does the same backwards. The slide animates (`Theme.durBase`).
- **No scrollbar is drawn.** The edge shows it can move: on hover a soft fade and a faint chevron in the gutter, and a
  small count ("8 more →") so nothing hidden is load-bearing. At either end the edge goes inert.
- **Exceptions are never hidden by paging:** the state phrase over the cell still names them ("three need looking
  at"), and a machine that needs someone off-screen shows its number in the edge count ("8 more, OPS-12 needs you →").
- Keyboard: Left / Right arrows page when the row has focus.
- The order is the stable one (by hostname) — paging never re-sorts.

**The same idea goes vertical** (*the user, 27 Sep 2026: "all listing or card that goes vertical should use that paging
idea … But if you feel like actual scrolling for vertical is better, we can use that."*):

- **A stack of cards in a fixed-height cell pages vertically.** As many cards as fit are shown whole; the cell's
  **bottom edge** is the pager — a soft fade, a down-chevron, "2 more ↓", and the name of any hidden card that needs
  someone. The top edge pages back. Cards slide, never scroll by the pixel. (Waiting on you, To address, By person.)
- **A continuous record read top to bottom scrolls** — the trail, a channel's messages, a history. Paging would cut a
  sentence in half; a thin, quiet scrollbar that appears on hover is right there.
- Horizontal rows of marks page sideways (above). A list is never shrunk to fit.

The `FleetGrid` scale ladder in QML (and `slot_size()` in `design/scale.py`) must change to this when next touched.

## 4. Cards, not rows

- **A person** (`person_card`): avatar 34, name 13 px ink 600, a line 11.5 px (in tone when it says something), an
  optional state word right; padding 12 / 14, radius 14, `pane` fill. Anchored left. Stack with 9–10 px gaps.
- **A thing** (`thing_card`): the same card with a **bare** 18 px icon in its tone instead of the avatar.
- **The chosen card** is a filled `select` row with white title — never a left-edge accent.
- A list of anything is a stack of these, under a plain 11.5 px faint heading ("To address", "Addressed this week").

## 5. Icons stand bare

No rounded-square tiles behind icons. An icon is a 1.6–1.75 stroke line glyph, 14–18 px, in its tone, beside its
words. A tile is only allowed where the icon *is* the whole target (none currently).

## 6. Trees for anything that branches

(`FL07`, *"very beautiful, just breathtaking"*.)

- Nodes are cards: padding 9 / 12, radius 12, `pane`, a bare 17 px icon, label 12.5 px 600, sub 10.5 px faint.
  Widths 150–190.
- Joins are **cubic curves** (mid-x control points), stroke rgba white 0.22, 2–2.5 px, round caps.
- A broken branch: its nodes get a 1.5 px danger ring and its curves go **dashed** danger; the rest stays quiet.
- Where a thing has several good drawings, offer them as **plain-text view tabs** (Tree · Sentence · Card), the tree
  the default.

## 7. Sentences with blanks

- Every blank is a slot: soft fill of its tone, radius 7, 600, with a small chevron — it looks pressable and reads as
  a word. 17 px for the lead sentence of a page, 12–13 px inside a cell.
- Optional additions chain after it as **"then …"** words and slots, ending in a dashed "+ then…" slot.
- The whole thing reads back as one sentence before anything is saved.

## 0. Legible before beautiful — the rule over all the others

*The user, 27 Sep 2026, on RC03 / RO03: "this is not easy to parse, don't get too hung up on it [being] nice ... it's
actually going to be used and must be easily parsed."* Rejected there: **the lanes of who-was-where, the tick runs of
update attempts, and the lever as a person card over a message box.**

**When a thing will be read in order to act on it, write it.** One card per fact, one sentence per card
("R. Mensah entered OPS-04 · 10:02 – 10:22 · 20 minutes · Adjoa was blocked"), and the one act on the same card
("Ask R. Mensah to look"). What is fine folds into a single line ("Everyone else stayed at their own machine").
No geometry to decode, nothing to count, no form to fill before acting. Drawings are for shape at a glance;
anything a person must read closely is words. `RC04` and `RO04` are the reference.

**The day timeline stays** (*"Am not opposing the timeline ... just make it readable like it done in super user areas"*):
use the Overview's own one (`dept_day` / `DayTimeline`) — a lane per machine labelled on the left, an hour axis with
gridlines, blocks in grey (at their own PC), amber (an Admin entered), red (you), and a legend under it naming the
colours and the machines never signed in. Never a bare set of bars without axis or legend. Pair it with the written
entries as its key (`RC05`).

## 8. Counts of events are ticks — only where nobody reads them one by one

Use sparingly (see section 0): a tick run is a texture, not a record. Ticks on a line: 3 px wide, radius 2; quiet ones 55 % height in rgba white 0.35; the ones needing someone full height
(14–18 px, 40 on a timeline) in their tone. Never squares, never a rainbow.

## 9. Colour

Four toned meanings only (ok, warn, danger, accent), always with a word. Calm by default: quiet things are grey
outlines and dim text; **colour lands only on what needs a person**. Identity colour (a department's) is a 9 px stamp
beside a title, never on marks.

## 10. Choosing among several

Never a lineup of tinted pill buttons. In order of preference:
1. **The things themselves as targets** — tiers drawn as folders you drop a file onto (the hovered one opens: dashed
   outline, soft fill of its tone).
2. **A fill-in sentence** slot that opens its choices.
3. **One picker.**
4. **Plain-text choices**, the current one in ink, the rest faint — the tab rule.

## 11. Words

Generated, never typed as code: no `k=v`, ids, paths or ISO times on anything a person fills in. Sentences ≤ 12 words,
state phrases ≤ 6. A cost is said before the act ("It will leave 7 worker machines…").
