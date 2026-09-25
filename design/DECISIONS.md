# What was decided, what was rejected, what is still open

The Phase 7 design ran long and covered a lot of ground. This file is the durable record so none of
it has to be rediscovered: what the user approved, what they rejected and why, the principles that
should shape every page that has not been designed yet, and what has not been started.

Read with `BOARDS.md` (what each board is) and `HANDOFF.md` (where the code stands).

---

## 1. Approved, and built

| | |
|---|---|
| **The Super User Overview is `K01` — a perfect 2 × 2 grid** | Four equal cells, no tabs. Chosen over `K02`, which put the ranking into the cell sizes. |
| **The four cells** | **Authority** (who governs what, and where nobody does) · **Rollout** (the lever only a Super User holds) · **Today** (who held each machine) · **Out of place** (files against their tier, and deviations). |
| **Titles sit above the cells**, on the frame, not inside them | Each carries its state phrase on the right, in the tone. The cell itself is a clean surface holding only the drawing. |
| **The header is "Must see" and the time** | The line describing the organisation ("three departments, three Admins, fourteen client PCs") was **removed on request** — a Super User already knows that. The page says what they must see. |
| **The dashboards are drawn on the frame** | No grey sheet behind the body. The gradient shows between the panels. |
| **The department page, `DP05`–`DP08`** | Approved 25 Sep 2026 — *"the design works for me, not perfect but it works."* Four cells (Who governs · Its machines · Today · Waiting on you) over the signature *an equal pair over a split*; an Admin opened with *the reading leads*; the session drawn as a container on the page; and the four answers arriving in the lane that stated the cost. **Design approved, not yet in QML** — and "not perfect" is on the record, so refinement is expected during the build, not a new pass. |
| **`D01`–`D03`, the Super User dashboards** | The first unreserved "beautiful" of the whole pass. `D04` is the descent into one department. |

## 2. Approved principles — these shape every page still to be designed

**Panel density, and the visual-to-words gradient** (`P01`–`P04`). The user's own idea, and the one
to carry furthest: *"first one mostly visual with little text and last one mostly text with some
visuals… the text with the visuals collaboratively explain things."* Made into a system:

| | Density | What the panel holds |
|---|---|---|
| 1 | **Figure** | a number and a word — no chart, no sentence |
| 2 | **Chart** | a shape and its legend — no sentence |
| 3 | **Chart, told** | a shape, and the one sentence it is making |
| 4 | **Reading** | a sentence, facts one line each, one small mark, at most one action |

A layout is a **sequence of densities running diagonally**: shape at the top left, words at the
bottom right. The page then answers without anything being clicked. This was implemented and tested
on the three-tab Overview before that page was replaced by the grid — **the principle survives and
applies to every page that has more than one panel.**

**A panel is never blank** (`P05`). Three cases, only two of which get a notice:

- **A zero is a result.** Drawn normally, no notice. "All 14 confirmed" and "no violations in
  /workers/" are answers, not absences.
- **Nothing yet** — the chart keeps its own structure (rows, lanes, track), quietened, with the
  notice laid **over** it, never in place of it.
- **Not enough** — the shape's frame, and what is missing.
- A **reading** panel takes no overlay: its content is words, so it says so, and keeps the rules its
  fact rows would have sat on.

**A chart has to pass one test.** *What question does this panel answer, and does the shape answer
it faster than a sentence would?* If it needs its geometry explained before it can be read, it is
the wrong chart.

**Sentences are generated, never written** (`operator_client/core/narrate.py`). One template per
condition, filled from the same data the chart drew. No condition matched → state the plain fact and
never manufacture an insight. Twelve words maximum, enforced in code. The six-word `brief` beside a
cell title is enforced the same way.

**Each page gets its own structural signature** so you know which page you are on before reading a
word — a band over two columns, an equal quartet, a lead and a column. Do not give two pages the
same shape. The same holds one level down: **an opened cell's composition belongs to that cell**,
not to the Overview.

**The shape the user named**, from board `P03` and reused for `K03`: a big chart top-left, two
"told" panels (density 3) in a row beneath it, and one tall **reading** panel (density 4) down the
right for the whole height. It suits a subject whose shape is the point and whose meaning needs
saying at length.

**An area is entered through its contents, not through tabs** (24 Sep 2026, `TABS.md`). Each area is a
handful of containers — one per thing it covers — and clicking one opens it in place, the rest
becoming the context that explains it. One level only; back restores the area exactly. The Overview's
`K01`→`K03`–`K06` behaviour is the general rule, not a special case. Where a tab row is genuinely
needed it is **plain text with colour marking the current one** — no pill, box or underline.

**One gesture, everywhere** (24 Sep 2026, `TABS.md`): **single click inspects** — a mark or row is
selected and its text arrives beside it — and **double click enters**, whether that means an area
recomposing around a container or moving to a place with its own page. Escape, the crumb or the back
arrow comes out; Enter is the keyboard equivalent. An enterable container advertises itself on hover;
one with nothing behind it does not respond. This settled the standing conflict between `K01` and
`X02`, which both claimed the single click.

**A session is a container, not a navigation** (24 Sep 2026): starting a traversal creates the session
and draws it as a small landscape container with the countdown; double-clicking it takes the window
into that level, and Escape comes back out *while the session is still held*. Holding and looking are
different things. There is no screen streaming in the protocol, so it is a live-state card, never a
viewport.

**Five areas, and the nine questions about them are closed** (25 Sep 2026, `TABS.md`). The rail is
**Must see · Authority · Rollout · Record · Work**. What was settled, in one line each: all reports live
in **Record** and Must see carries the unaddressed ones; Work has one **Closed** filter that hands off to
Record; Record covers past *and* present and keeps its name; report **routing** is an Authority act;
resource **tiering** is Admin-only and so belongs to level 3; a Super User **watches** assistance and
never starts it; the rail owns the name "Must see" and the page header drops to the time; the Admin rail
is deferred to level 3; and the department's four cells are **Who governs · Its machines · Today ·
Waiting on you**, with Today the wide one. The rule that keeps five honest: **a thing appears in two
areas only if one of them is Must see, or a filter that names the other.**

**Layout is editorial, not a preference.** One layout per page, chosen once, never per viewer.

**Four cells, and the widths vary.** The user's own call, made on the `T02` board: *"the width
varies and usually four is the sweet spot."* So a level's page is **four cells**, never a stack of
full-width bands, and their widths do the ranking — 670/670 over 900/440, or 440/900 over 670/670.
Which cell is the wide one is what gives the page its signature, and it moves with the subject: at
rest in a department the day is wide; inside an Admin their *automation* is wide and the person
shrinks, because the lid and the rail already say whose machine it is. Detail arrives by opening a
cell, not by crowding the page — the Overview's rule (`K01` → `K03`–`K06`), carried down every level.

**A count is drawn against the largest, not on its own.** "Its client PCs" draws as many slots as
the biggest department has and fades the ones this department does not fill, so its size is legible
at the same time as its state. Applies wherever one member of a set is shown alone.

**Colour** stays as already settled: one gradient frame that never changes, four toned meanings,
identity uses the categorical ramp, every hue carries a word.

## 3. Explicitly rejected — do not bring these back

| Rejected | Why |
|---|---|
| **A page of sentences / a duty officer's log** (`H01`–`H03`) | "Ewwww." "Would rather eat dirt." The Overview states things with charts, not paragraphs. |
| **Tabs on the Overview** | Three tabs existed only because there was a chart dump to carve up. One page. |
| **The organisation description in the header** | A Super User knows their own department count. |
| **The original in-app "At a glance"** | "Not really feeling it" — four boxes with small charts parked in them and air around everything. |
| **Chord diagram** (assistance), **orbit diagram** (routing), **occupancy band** (sessions) | "Not intuitive… should be an easier and preferred way to see data and not reason hard on what the hell is going on." Each was only legible once its geometry had been explained. |
| **Hex fleet, slope chart** | Decoration and specialist reading; neither earned its place. |
| **Identical rounded cards on a grid, repeated** | The module that made every early take interchangeable. A page needs an organising idea, not a card kit. |
| **Empty space where a chart has no data** | "I'd rather the visual exists, with a no information notice… rather than the space being empty." |
| **The first traversal pass** (a sidebar-and-card-strip department screen, a tall amber banner) | "No way am accepting this disgusting work… this mood board you are giving me for department level is just terrible." The level was wrong (traversal starts in a *department*, which had never been drawn) and the page fell back on the pre-kit shell. Redrawn in the Overview's language; the banner became a 38 px red lid. |

Rejected from earlier in the phase and still binding: **left-edge accent borders** on selected rows
or cards, **tables anywhere**, a **docked right panel**, **accordions in a body**, **progress bars on
entity cards**, and **large action cards with switches**.

Boards for the rejected proposals have been removed from the canvas. They are recorded here so the
reasoning is not lost, not so they can be revived.

## 4. Proposed, still open

| | |
|---|---|
| **`X01` — choosing how a slot is drawn** | Each chart has alternatives; the control lives in the slot's own header. My recommendation, given and not yet answered: ship it as **one choice per slot, set once**, not a cycle button met on every panel — a panel that changes form under you costs what a re-sorting list costs. The mechanism is the same either way. **Not built.** |
| **`K03`–`K06` — a cell opened in place** | The user's own idea, and the strongest of the pass: clicking a chart does not navigate — the page **recomposes** around it. The clicked cell grows where it already is, and the panels around it become the gradient that explains it. **The composition is per cell, not fixed**, and no two cells share a shape: Authority opens into the **P03 shape** (a big chart, two told panels beneath it, one tall reading panel down the right — `K03`, the shape the user picked out by name); Rollout opens wide, its fleet across the top and three panels beneath (`K04`); Today opens as a lead running the whole height with a column of three beside it (`K05`), because a record is read down; Out of place takes no hero at all and becomes three full-width bands read downward (`K06`), because its subject is small. Four rules: the cell grows **where it is** and never jumps to first position; **one level only** (inside, a click selects or filters); back is the same gesture or Escape and restores the grid exactly; a cell with **nothing to explain does not open** — with no version approved, no PCs, or nothing out of place, that cell stays shut. **All four are BUILT.** |
| **`C01`–`C10`, the chart treatments** | Ten boards, four treatments each. Two have been applied (assistance → one line per pair; routing → lines and chips). **The other thirty-odd exist only as boards.** |
| **`L01`–`L06`, the layout structures** | Three-, four- and five-panel arrangements. Superseded for the Overview by the grid; still the library for pages with more than one panel. |
| **`K02`** | The same four cells ranked by size. Kept as the alternative to the chosen `K01`. |

## 5. Not started

The Overview is one page of what is now a seven-entry rail. Everything below is untouched.

**Super User pages** — none of these have been designed or built. They are now named by the area that
owns them (`TABS.md`), not by feature, because the eight-tab rail is gone:

- **Record** — audit, sessions, Views (who addressed which report, when), all reports, deviations,
  violations, and the closed half of Work.
- **Rollout** — approval, rollout by department, the escalation lever.
- **Authority** — departments, Admins, client PCs, appointing, display names, entering, and report
  routing (whose UI the spec still defers, §10).
- **Work** — Tasks, Flows, and live assistance watched read-only, plus its one **Closed** filter.

**Traversal into an Admin is designed (`T01`–`T06`) but not built.** A department is a place drawn in
the Overview's language — a colonnade of Admin columns over the day they share — and entering one is a
*state* of that place, under a slim red lid. Still unbuilt in QML.

**Superseded:** The Engine enforces it and
the integration tests cover it, but *how the UI changes when a Super User enters an Admin's
workstation* — what the rail becomes, what the frame says, what is hidden, how you get back — has no
design and no code. This is a Hierarchy-backbone behaviour, so it should be settled before the
dependent pages are drawn.

**Admin views** — Tasks, Flows, Automation, Actions, Assistance, Reports are still the pre-kit
screens, mounted hidden behind a placeholder. What of the Super User work carries over to Admin is a
decision that has been deliberately deferred.

**States and surfaces** — the connect screen, loading, disconnected, the dialogs (`Dialogs` board),
and the Worker Overlay and Dialog (`Worker` board).
