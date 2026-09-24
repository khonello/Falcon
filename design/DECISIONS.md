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

**Layout is editorial, not a preference.** One layout per page, chosen once, never per viewer.

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

Rejected from earlier in the phase and still binding: **left-edge accent borders** on selected rows
or cards, **tables anywhere**, a **docked right panel**, **accordions in a body**, **progress bars on
entity cards**, and **large action cards with switches**.

Boards for the rejected proposals have been removed from the canvas. They are recorded here so the
reasoning is not lost, not so they can be revived.

## 4. Proposed, still open

| | |
|---|---|
| **`X01` — choosing how a slot is drawn** | Each chart has alternatives; the control lives in the slot's own header. My recommendation, given and not yet answered: ship it as **one choice per slot, set once**, not a cycle button met on every panel — a panel that changes form under you costs what a re-sorting list costs. The mechanism is the same either way. **Not built.** |
| **`K03`/`K04` — a cell opened in place** | The user's own idea, and the strongest of the pass: clicking a chart does not navigate — the page **recomposes** around it. The clicked cell grows where it already is, and the panels around it become the gradient that explains it. **The composition is per cell, not fixed:** Authority opens into the **P03 shape** (a big chart, two told panels beneath it, one tall reading panel down the right — `K03`, and the shape the user picked out by name); Rollout does not want that shape at all, because its subject is a fleet, so it opens wide with the hero across the top and three panels beneath (`K04`). Every cell declares the composition its own subject needs. Four rules: the cell grows **where it is** and never jumps to first position; **one level only** (inside, a click selects or filters); back is the same gesture or Escape and restores the grid exactly; a cell with **nothing to explain does not open**. **Authority is BUILT** — click the cell to open it, Escape or the breadcrumb to restore. Rollout, Today and Out of place still need their own compositions. |
| **`C01`–`C10`, the chart treatments** | Ten boards, four treatments each. Two have been applied (assistance → one line per pair; routing → lines and chips). **The other thirty-odd exist only as boards.** |
| **`L01`–`L06`, the layout structures** | Three-, four- and five-panel arrangements. Superseded for the Overview by the grid; still the library for pages with more than one panel. |
| **`K02`** | The same four cells ranked by size. Kept as the alternative to the chosen `K01`. |

## 5. Not started

The Overview is one page of what is now a seven-entry rail. Everything below is untouched.

**Super User pages** — none of these have been designed or built:

- **Views** — the Super-User-only record of who addressed which report, when.
- **Reports** — routing configuration and the report pane.
- **Updates** — approval, rollout by department, the escalation lever.
- **Tasks**, **Flows**, **Assistance** — the Super User's view of each.

**Traversal into an Admin is neither implemented nor tested in the GUI.** The Engine enforces it and
the integration tests cover it, but *how the UI changes when a Super User enters an Admin's
workstation* — what the rail becomes, what the frame says, what is hidden, how you get back — has no
design and no code. This is a Hierarchy-backbone behaviour, so it should be settled before the
dependent pages are drawn.

**Admin views** — Tasks, Flows, Automation, Actions, Assistance, Reports are still the pre-kit
screens, mounted hidden behind a placeholder. What of the Super User work carries over to Admin is a
decision that has been deliberately deferred.

**States and surfaces** — the connect screen, loading, disconnected, the dialogs (`Dialogs` board),
and the Worker Overlay and Dialog (`Worker` board).
