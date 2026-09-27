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
| **The department page, `DP05`–`DP08`** | Approved 25 Sep 2026 — *"the design works for me, not perfect but it works."* Four cells (Who governs · Its machines · Today · Waiting on you) over the signature *a pinwheel* — the two big cells on a diagonal; an Admin opened with *the reading leads*; the session drawn as a container on the page; and the four answers arriving in the lane that stated the cost. **Design approved, not yet in QML** — and "not perfect" is on the record, so refinement is expected during the build, not a new pass. |
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

**Whoever the cell draws is whoever is selected** (25 Sep 2026, `DP15`–`DP17`). Selecting had been
settled in words since 24 Sep but never drawn, so a reader looking at the journey could not find the
step where a department or an Admin is chosen — every board was a destination. The three states now
exist, and they fix the rule:

- **Single click selects**: a mark is *ringed* (never recoloured — colour already means state) and its
  text arrives beside it; a foot row becomes a filled muted row and the cell swaps to draw that person.
  **The crumb does not move.** Nothing has opened.
- **Double click enters**, and **the crumb grows by one**. That growth is the only reliable sign that
  you went somewhere rather than merely looked.
- At rest the **first Admin in the stable order is already the selected one**, which is why entering
  them takes no click first, and entering anybody else takes exactly one.

**A chart maximises; an area recomposes** (25 Sep 2026, the user's proposal, `DP11`). Double-clicking
a container opens it into *whatever explains it* — and what explains a chart is **more of that chart**,
not four more charts. So:

| The container stands for | Opening it gives you |
|---|---|
| an **area** — authority, a rollout, a day | a composition of several panels (`K03`–`K06`) |
| **one chart** — its machines, the fleet | that chart at full size, its words beside it, and nothing else |

It needs no new rule and no new gesture: the composition already belongs to the cell, and a maximised
chart is simply a composition of one panel. Same double click, same Escape, still one level.

**A set too big to draw does not get a scrollbar** (25 Sep 2026, `DP10`). The sample department had
seven machines; the design has to hold a hundred. **The mark shrinks while shrinking still says
something, and past that the drawing changes kind** — 46 px with the hostname inside, then 30 px
unlabelled, then 16 px dense, then one bar per Admin with only the exceptions named. **Never
horizontal scrolling**: a chart you have to scroll has stopped answering in one look, and it breaks
*a count is drawn against the largest*, because you can no longer see the largest. At every size the
cell answers the same three things — how many, how healthy, whose — and *which one, and what is wrong
with it* is the maximised view's job. That is why maximising and scale are one decision: the cell drops
the names to fit, and maximising is where they come back.

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
| **Machines grouped under an Admin's name** (`DP03`'s pick, and every board after it) | *"Machines are assigned to departments not admins... There is no these machines are associated with this admin."* Correct, and the system agrees: a PC carries a department, an Admin may traverse into any PC in theirs, and report routing goes to every Admin in the department. The grouping was drawn for five boards before anyone checked. **`Its machines` is now one set — the department's — and an Admin is drawn with what is theirs: their own workstation, their tasks, their flows.** No station says "answers for N". |
| **Two Admin stations crammed into one cell** (`DP05`, first cut) | *"The who governs is terrible."* Two people compressed side by side gave neither enough room. Replaced by **one Admin at full width**, the others named on a line at the foot — single click swaps who is drawn, double click enters them. |
| **A metrics card as the held session** (`DP07`, first cut) | CPU, memory, idle and a *Take a still* button. *"Not metrics, screenshot."* The held session now carries **a picture of their screen**, with the session facts beside it. The picture states its age, because it is a still and the transport for it is not built — see `PHASES.md`. |
| **The first traversal pass** (a sidebar-and-card-strip department screen, a tall amber banner) | "No way am accepting this disgusting work… this mood board you are giving me for department level is just terrible." The level was wrong (traversal starts in a *department*, which had never been drawn) and the page fell back on the pre-kit shell. Redrawn in the Overview's language; the banner became a 38 px red lid. |

Rejected from earlier in the phase and still binding: **left-edge accent borders** on selected rows
or cards, **tables anywhere**, a **docked right panel**, **accordions in a body**, **progress bars on
entity cards**, and **large action cards with switches**.

Boards for the rejected proposals have been removed from the canvas. They are recorded here so the
reasoning is not lost, not so they can be revived.

## 3a. Picked off the Tasks and Automation mood boards (26 Sep 2026)

The user, on the pre-kit Tasks screen: *"the task structure being table doesn't sit right and doesn't
reflect what we discuss for task creation at all"*, and of its assigner column: *"why is assigner
necessary since the user is assigner"*. On Automation and Actions: *"it not programmers using it so it
should intuitive visually using ux, not using things like k="*. Boards `TK01`-`TK03` and `AU01`-`AU03`
were drawn for it; these are the picks, in the user's words where a section got more than one. **More
than one pick in a section means they are combined, not chosen between.**

| Section | Picked |
|---|---|
| `TK01` the shape of the Tasks page | **Four cells** — the Overview's language |
| `TK01` one task, listed | **By person** — who is carrying what; never the assigner |
| `TK02` describing it | **Side by side** — your words, and the structure they fill, beside them |
| `TK02` what comes back | **Decisions, one at a time** + **Asked where it stands** + **The split, drafted** |
| `TK03` while it runs | **A checklist** + **The file itself** |
| `TK03` closing it | **Review, then decide** + **What the assignee sees** |
| `AU01` the Automation page | **When \| then** — two columns, joined |
| `AU01` one automation | **A recipe card** + **What it did** |
| `AU02` choosing what triggers it | **Fill the sentence** + **Three steps** + **Start from an example** |
| `AU02` saying the details | **A time is days and a clock** + **A place is a tier, or a folder** + **Machines are picked** — the threshold slider was *not* picked |
| `AU03` the library | **Grouped, with what it does** |
| `AU03` setting an action up | **When it runs** + **A custom action** + **Try it on one machine** |

**Approved, 26 Sep 2026:** `TK04`-`TK07` and `AU04`, the pages composed from these picks — *"The #2 works
fine for me, am not really complaining."* Designed, not yet built.

**Approved, 26 Sep 2026:** `AU05`-`AU10` (Actions, each action's own settings, a custom action, the three steps of
making an automation, and the level control redrawn as a meter) -- *"Very good work done."* Designed, not yet built.

**Each action asks for what it needs** (the user, with the AU picks): *"each action can have it specify
needs so it visuals or designs are not necessarily standard."* There is no one settings form. Notify asks
for a message, Lock the screen for how long, Rename a file for which file and its new name, Close a
program for which program, and a Screenshot asks for nothing. The control follows the need.

Nothing on a mood board is typed as code, and that is now a rule for every page: **no `k=v`, no ids,
no ISO timestamps, no path prefixes** in anything an Admin or Super User fills in. A detail is set with
the control that fits it.

## 3b. Batch 1: the Admin's remaining pages (27 Sep 2026)

The user: *"Resolve conflict yourself, just note the visual direction that am feeling so you can slide through
without too many questions."* The picks off `HO01`, `FL01`, `FL02`, `AS01`, `RP01`, composed into `HO02`,
`FL03`-`FL05`, `AS02`, `RP02`:

| Page | Picked |
|---|---|
| Admin home | **Four cells**; one machine as **Slots** + **One line each** |
| Flows page | **Map of every flow** (*"I don't see how this will look"* — so it is drawn for real on `FL03`), **From → to** (the listing, not its look — cards now), **Four cells** |
| One flow | **A tree** (*"very beautiful, just breathtaking"*), **A sentence**, **A recipe card** — the tree is the default view, the other two the viewer's choice |
| Making a flow | **Fill the sentence** (*"the options below chained for 'then' are nice"*) + **Checked before saving** |
| When a flow needs you | **The broken branch** + **The fix, offered** + **Kept, not overwritten** |
| Assistance | **The ping, unmissable**; **By person** as avatar-led rectangles anchored left, not a list; **Listening** with *"a small visual spice"*; **One search box** + **Grouped by where** |
| Reports | **A queue to address**, **A timeline**, **Four cells**; one report as **A reading, then mark** |

**THE SLOT RULE — system-wide, and it overrides earlier boards.** *"The only issues I have ever had with slots
is the color ranging, not just here but everywhere."* A set of marks is **calm**: one quiet fill for every mark,
and colour only on the exceptions that need someone — a thin ring and a dot. A machine that is fine is not
green; it is quiet. `calm_slot` in `design/batch1_pages.py` is the drawing. **The built `FleetGrid` (level 2)
and every fleet/slot drawing on the Overview must move to it when next touched.**

## 3c. Batches 1 and 2 rethought (27 Sep 2026)

*"I don't like the square with dots inside. Rethink it."* then *"Rethink the whole batch, 1 and 2"*, and on
RS01's Tag by dropping: *"I hate the lineup of 4 buttons, I hate the button design there too."*

**This supersedes the slot rule in 3b.** Rejected, everywhere:
- **A square mark with a dot in it** (the calm slot). A machine is now **a small screen with its number** — a
  faint outline when quiet, outline and number in the tone when it needs someone, the reason said beneath it.
  `calm_slot` in `design/batch1b_pages.py`; `MK01` draws it and its alternatives.
- **Icons sitting in rounded-square tiles.** Icons stand bare.
- **A lineup of tinted pill buttons** as a choice. Choose among several by the things themselves (shelves to drop
  onto), one picker, a fill-in sentence, or plain words.
- **Lanes of squares.** Counts of events are ticks on a line; the ones needing someone stand taller in their tone.

Redrawn: `MK01`, `HO03`, `FL06`-`FL08`, `AS03`, `RP03` (batch 1, still awaiting approval) and `RC02`, `RO02`, `WK02`,
`RS02`, `CP02` (batch 2 mood boards, awaiting picks). `HO02`-`RP02` and `RC01`-`CP01` are superseded.

**Approved, 27 Sep 2026:** batch 1 rethought (`MK01`, `HO03`, `FL06`-`FL08`, `AS03`, `RP03`) -- *"Much much better,
honestly, they all work well."* The small-screen machine mark in particular (*"worked extraordinarily especially at
that sizing"*). The patterns behind them are measured in **`design/PATTERNS.md`**, the reference for fixing other pages.

**Paging replaces shrinking for rows of machines** (supersedes `DP10`): the mark stays full size, and clicking the far
right / left of the container slides the next 4 (or 2) into view. `PATTERNS.md` section 3.

**Batch 2 picked, 27 Sep 2026** -- the user: batch 2's rethought boards "all work well", every facet open to use.
Composed into `RC03` Record, `RO03` Rollout (the first drawing of edge paging), `WK03` Work, `RS03` Resources (reached
from the Admin's home, no rail entry added), `CP03` a client PC at level 4 under level 3's lid.

**Rejected, 27 Sep 2026, on `RC03` / `RO03`:** the who-was-where lanes, the update-attempt ticks, and the lever as a
person card over a message box -- *"not easy to parse ... must be easily parsed."* Redone as `RC04` / `RO04`: a card and a
sentence per fact, the act on the same card. The rule is `PATTERNS.md` section 0.

**The timeline is kept, made readable** (27 Sep 2026): `RC05` uses the Overview's day timeline with axis and legend, beside
the written entries. Supersedes `RC04`'s cards-only Record.

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
