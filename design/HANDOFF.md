# Where the Operator Client UI stands — 24 Sep 2026

A snapshot for a fresh session: what exists, what was decided, and the one thing to do next.

**Read `design/LEVELS.md` first** — the levels, which one is being worked on, and the rule that only
that level's UI is touched. Then in this order: `design/DECISIONS.md` (what the user approved, rejected and why — it is what
stops the rejected shapes coming back) → `design/BOARDS.md` (what every board is) → this file (where
the code stands and what to do next).

**Design canvas:** <https://claude.ai/artifact/71rNVLEqFPPwJ2mPoD7Vpw> — "Falcon Operator Design",
84 boards, **version 44**. Rejected and superseded proposals are deleted from it. Branch
`phase7/design-and-gui-rebuild`; **122 tests green, `ruff check .` clean**. No QML has changed in this
pass — everything below is design.

---

## CONTINUE FROM HERE — the department level, waiting on picks from its mood board

**We work one level at a time** (`design/LEVELS.md` — read it first). Level 1 Super User is designed
and built. **Level 2, the department, is the current and only work.** Level 3, the Admin, was designed
and built in the earlier pass and is not to be redesigned: traversing into an Admin hands over *those*
screens. Level 4, a client PC, has not started.

**What just happened.** Two passes at the department went wrong and were thrown away or parked: the
first fell back on the pre-kit sidebar-and-card-strip shell, the second mixed level 3 into level 2 (a
red "you are inside" lid on a department screen). The cause was the same both times — **the department
never had a mood board**, so approaches were never put side by side and picked from. Super User had
`S01`–`S04`; the Admin console had `M01`–`M15`.

**`DP01`–`DP04`, the department mood board, is now on the canvas** (`design/dept_mood.py`), in the same
format as the others: one facet per board, two sections, four approaches at the same size, each
captioned so a pick can be named.

| Board | Section 1 | Section 2 |
|---|---|---|
| `DP01` shape | Colonnade · Floor first · Roster · Split | where the Admins sit: Columns · Header band · Ledger · On the machines |
| `DP02` people | one Admin: Station · Ledger line · Figures · Portrait | what is said: their machines · their work · one sentence · a state word |
| `DP03` machines | the seven: Grouped by Admin · One waffle · Day lanes · Roster | one machine: Slot · With its Admin · Its day · Figure |
| `DP04` doors | choosing: Opens in place · Detail lane · Drill · Reveal | asking to enter: In the cell · A confirm · A reading · Two doors named |

**THE NEXT STEP: one word from the user.** The mood board has done its job; picking from a menu of
option names was a bad way to ask and was dropped. The department page is to be built from this
combination unless the user changes part of it:

> Admins as columns across the top · each drawn as a **station** (avatar, machine, then the slots they
> govern) · the seven client PCs **grouped under the Admin** who answers for them · entering asked for
> with **the cost stated first, then the act** · everything opened by **double click, in place**.

`T01` (at rest) and `T02` (an Admin chosen) are the pre-mood-board attempts — material, not the answer.
Rebuild from the combination above, screenshot it, and let the user react to the real page.

**Settled since, and binding on everything drawn from here**

- **Areas, not features** (`TABS.md`): the Super User rail is five — **Must see · Authority · Rollout ·
  Record · Work** — with Assistance folded into Work. Nine open issues in that file are to be settled
  *in the document* before any of it is drawn.
- **An area is entered through its contents, not through tabs.** Each area is a handful of containers,
  one per thing it covers.
- **One gesture: single click inspects, double click enters.** Escape, the crumb or the back arrow comes
  out; Enter is the keyboard equivalent. This resolved a standing conflict between `K01` (a click opens
  a cell) and `X02` (a click brings a chart's text beside it) — they cannot both own the single click.
  An enterable container advertises itself on hover; one with nothing behind it does not respond.
- **A session is a container.** Starting a traversal does not move the window: it creates the session,
  which appears as a small landscape container carrying the countdown, and *double-clicking that* is
  what takes the window into the Admin. Escape comes back out while the session is still held. There is
  **no screen streaming in the protocol**, so the container is a live-state card (`control.metrics`, the
  machine, the countdown), never a fake viewport.
- **The levels share one visual language.** Depth is told by the crumb, the title and the subject's
  identity colour — not by restyling. Only *holding* a session changes chrome, because that is a state,
  not a depth.
- **If a tab row is ever needed**: plain text, colour on the current one, no pill, box or underline.

**Settled at this level so far**

- **Four cells, and the widths vary** — *"the width varies and usually four is the sweet spot."* A
  level's page is four cells, never full-width bands; the widths do the ranking, and which cell is
  wide is the page's signature.
- Detail arrives by **opening a cell**, not by crowding the page — the Overview rule carried down.
- A department has **two doors**: an Admin, and a client PC. A Super User may enter either; the client
  PC does not have to be reached through its Admin.
- Levels 1–2 are **looking** (nothing held, no clock). Levels 3–4 are **holding**.

**Parked, because they belong to level 3:** `T03` (inside an Admin), `T05` (the lid and its clock),
and `T06` (assisted access, its own state machine). They stay on the canvas labelled `PARKED`. When
level 3 is opened, the question is how the **existing** Admin screens are wrapped — not what replaces
them.

**How to work it:** draw it as a board in `design/` first → `gen.py` → screenshot with Edge → show the
user → only then QML + a test. Every piece of UI work is presented as **images in the conversation**,
never described. And no UI change without being asked for it.

---

## What is built

**The Super User Overview is one page and a perfect 2 × 2 grid** (board `K01`): **Authority**,
**Rollout**, **Today**, **Out of place**. No tabs. Each cell's title sits above it on the frame with
a generated state phrase beside it; the header is "Must see" and the time, with no description of the
organisation. The panels sit on the gradient — no grey sheet behind the body.

**Clicking a cell opens it in place**: the cell grows where it is and the panels around it become the
gradient that explains it. Escape or the breadcrumb restores the grid exactly. **The composition
belongs to the cell — all four are built and no two share a shape**, so you know which one you opened
before reading a word:

| Cell | Composition | Board | Its shape |
|---|---|---|---|
| Authority | `OpenedAuthority.qml` | `K03` | the map as hero, two told panels beneath, the reading down the right |
| Rollout | `OpenedRollout.qml` | `K04` | the fleet across the full width, three panels beneath |
| Today | `OpenedToday.qml` | `K05` | a lead running the whole height, a column of three beside it |
| Out of place | `OpenedOutOfPlace.qml` | `K06` | three full-width bands, shape to words, read downward |

A cell with **nothing to explain does not open** (no ungoverned department, no approved version, no
client PCs, nothing out of place) — checked on an empty system. One level only: inside an opened cell
a click selects or filters, it never opens again.

**Words are generated, never written**: `operator_client/core/narrate.py`, pure functions over the
dicts the handlers already return, reached from QML as `falcon.narrate(topic, data)`. Twelve words for
a sentence and six for a cell's `brief`, both enforced with a raise, not a long line; a topic with no
matching condition states the plain fact. `tests/test_narrate.py` holds every topic to those rules.

## Run it, render it, check it

```powershell
environ-operator\Scripts\python.exe design\run_gui.py super_user      # a real window, stubbed, no Engine
$env:FALCON_SHOT_EMPTY=1; ... design\run_gui.py super_user            # a system with no data

environ-operator\Scripts\python.exe design\shot_gui.py design\shots super_user 0    # the Overview, at rest
$env:FALCON_SHOT_OPEN="rollout"; ... design\shot_gui.py design\shots super_user 0   # a cell opened
                                                  # authority | rollout | today | place
environ-operator\Scripts\python.exe design\shot_gui.py design\shots admin

environ-engine\Scripts\python.exe design\gen.py       # -> design/boards/*.dc.html (git-ignored)
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 `
        "--screenshot=design\shots\K05-Opened-Lead.png" "file:///$PWD/design/boards/K05-Opened-Lead.dc.html"

environ-engine\Scripts\python.exe -m pytest tests/test_operator_gui.py tests/test_narrate.py -q
environ-engine\Scripts\python.exe -m ruff check .
```

Edge writes its `--screenshot` **after** the process returns and only to an absolute path — wait a
moment and check the file. To change the design: edit the module, re-run `gen.py`, screenshot, then
publish the changed `boards/<name>.dc.html` to the canvas as `project/<name>.dc.html` (one Artifact
call: `root` = a folder holding `project/…`, `file_path` = `project/canvas.json` only when the board
list changes). `design/README.md` has the detail.

## Rules that are settled

- **One gradient frame**, always: `#121220 → #2A1F50 45% → #4B2F8A`, 155°; it never changes with
  state. Session state is said by a floating pill, the status line and the detail card.
- **Four toned meanings only**: accent `#8AA6E0`, ok `#7FB396`, warn `#D2A468`, danger `#DD8A8A`, each
  with a ~14 % tint. A border or highlight is a toned variation of a core colour, never a new hue.
- **Charts**: identity uses the categorical ramp (`#3987e5 #d95926 #199e70 #c98500 #d55181`, validated
  against the `#12151C` chart surface, stated once as `Theme.series(i)`); the four status colours stay
  reserved and always carry a word beside the hue.
- **Selection** is a 1 px inset line in a soft accent, or a filled muted row in the sidebar. **Never a
  left-edge accent** — the user's strongest dislike.
- **A body row is one line**: short title (≤ 4 words), at most one value (≤ 3 words), a chevron. No
  sentences in a body — the detail card explains. **No accordions in a body**; they live inside the card.
- **The detail card** sits in a reserved 372 px lane, is always present, never opens or closes, has no
  close button, and shows an empty state when nothing is selected. The body column is a fixed 620 px.
  It shows **what is selected**, never what was just triggered; results are confirmed by a toast.
- **The sidebar names the category; the pills filter on a different axis**, never the same one twice.
  The sidebar keeps a **stable order** (admins, then PCs by hostname) and never resorts by state.
- **Avatars are neutral**, no state dot; session state is an icon (person / lock / monitor / shield).
  **Buttons are tonal or ghost only.** Chips are soft. Inputs are filled.
- **No tables anywhere. Cards in one space are all one size.** A different accepted variant in a
  different space is fine.
- **Super User is designed for its own job**, not the Admin screens adapted: what cannot be done in
  that space is not named in it (no Automation/Actions entry at all).
- **A chart must pass one test**: *what question does this panel answer, and does the shape answer it
  faster than a sentence would?* Three treatments were cut for failing it (chord, orbit, occupancy
  band). Expressive treatments stay as alternatives, never as defaults.
- **Panel density** (`P01`): a panel is a Figure (1), a Chart (2), a Chart told (3) or a Reading (4),
  and a layout is a sequence of them running diagonally from shape to words, so the page answers
  without a click. **Layout is editorial, not a preference** — one layout per page, chosen once.
- **Every page, and every opened cell, has its own structural signature**, so you know where you are
  before reading a word. Never give two of them the same shape.
- **A panel is never blank** (`P05`): a **zero is a result**, drawn normally; **nothing yet** keeps
  the chart's own structure, quietened, with the notice laid over it; **not enough** draws the shape's
  frame and says what is missing. A *reading* panel takes no overlay — its content is words.
- **Visual first, text on demand** (`X02`): clicking a chart settles it to one side and brings text
  beside it — one sentence, then facts one line each, then at most one action. The chart stays.
- **A count is drawn against the largest, not on its own** (a department's PCs are drawn as as many
  slots as the biggest department has, the unfilled ones faded).

## What exists

### The design (`design/*.py` → the canvas)

| Row on the canvas | Boards |
|---|---|
| The Admin shell · sessions · work · policy | `Main`, `SuperUser`, `Traversing`, `Occupied`, `Assisted`, `Tasks`, `Flows`, `Automation`, `Actions`, `Automation-Live`, `Assistance`, `Resources`, `Reports`, `States` |
| Worker + language | `Worker`, `Tokens`, `Dialogs` |
| Mood boards | `M01`–`M15` (every component in 3–4 variants) · `S01`–`S04` (Super User) — both already picked from |
| The lane | `Lane-Filled`, `Lane-Empty` |
| Super User pages | `SU-Departments`, `SU-Views`, `SU-Updates`, `SU-Audit` · dashboards `D01`–`D04` (superseded by the grid) |
| Charts | `C01`–`C10` — one chart type per board, four ways to draw it |
| Layouts | `L01`–`L06` — the same content in three, four and five panels |
| Behaviour | `X01` choosing how a slot is drawn · `X02` reading a chart |
| Densities and pages | `P01`–`P05` |
| **The Overview** | `K01` the grid (built) · `K02` the rejected ranked alternative · `K03`–`K06` the four cells opened |
| The map | `INDEX` — **out of date**; `design/BOARDS.md` is the current map |

### The code (`operator_client/gui/qml/`)

The kit: `Theme.qml` (tokens, plus back-compat aliases so unported views still load), `Icons`+`Icon`
(stroke glyphs as SVG path data drawn with `QtQuick.Shapes` — no image assets), `Txt`, `Chip`, `TBtn`,
`GBtn`, `IconBtn`, `Avatar`, `Pills`, `CardRow`, `DetailCard`, `KeyRow`, `Sidebar`/`SbSection`/`SbRow`,
`IconRail`, `TopBar`, `Body`, `HomeView`, and `main.qml` (gradient frame, floating state pill, toast,
status line).

The charts, all `QtQuick.Shapes` and plain rectangles — no charting library: `Panel`, `Legend`, `Hero`,
`StackedBars`, `Waffle`, `FleetGroups`, `DeptSlots`, `QuietStrip`, `Trend`, `MiniBar`, `HealthCard`,
`OrgMap`, `Arcs`, `RoutingMap`, `DayTimeline`, `DevStrip`, `EnteredRows`, `TierBars`, plus `Sentence`
and `ReadingBody` for the words.

`OverviewView.qml` holds the data and the grid; `GridCell.qml` is one cell (title above it on the
frame, `openable`, the never-blank notice); the four `Opened*.qml` are its compositions, chosen by
`opened` on a `StackLayout`. Everything on them is real: `hierarchy.tree`, `updates.rollout_health`,
`hierarchy.sessions_today`, `resource.violations`, `audit.deviations`, `reports.routing_get`,
`task.list`, `flow.list`, and `audit.recent` with prefix `update.attempt` for the confirmations trend.

Two things the opened panels needed from below the UI: `updates.rollout_health` now reports how many
attempts each PC behind has lost (`failures`, `last_attempt_at`), so *What is blocking* can name the
machine the N+1 gate rests on; and `TierBars` takes a `notes` map so a violation is named on the tier
line it broke. The opened Rollout groups its fleet squares by department — hostname numbers repeat
across departments, so an ungrouped row of them says nothing.

**Role differences live in exactly one place**: `IconRail.qml`'s `adminNav` / `superNav`. Each entry
carries a `key` and `main.qml` routes on `shell.viewKey`, so the rails can differ in length; a view
switches to another with `shell.show("hierarchy")`.

Still pre-kit, mounted hidden so their tests keep passing: `TasksView`, `FlowsView`, `ControlView`,
`AssistanceView`, `ReportsView`, plus `ConnectView` and `Btn`, `Field`, `DataTable`, `Picker`,
`SegmentedControl`, `Eyebrow`, `Section`. Orphaned by the rebuild and safe to delete when their
replacements land: `HierarchyView.qml`, `HierarchyRail.qml`. `GlancePage`, `HierarchyPage` and
`RecordPage` were deleted when the three Overview tabs went.

## Qt gotchas already paid for

- A **nested layout fills by default**: a `RowLayout` inside a `ColumnLayout` starves its sibling
  unless told `Layout.fillHeight: false`. This cost an hour twice.
- **Size a panel by its content, not by a fraction of the window**, when its content is words:
  `Layout.preferredHeight: 77 + body.implicitHeight` (77 = a `GridCell`'s title line and padding).
  Chasing percentages clips the last row or the action button.
- A component's children only land where you meant if the alias is a **`default property alias`**.
- `icon` is FINAL on `AbstractButton` — our buttons use `iconName`.
- `font.families` is not available in this Qt build — `Theme.pick()` resolves one family at runtime.
- `font.pixelSize` rejects fractional values, so the boards' 11.5 / 12.5 px map onto `Theme.fMeta` /
  `Theme.fBody`, never `+ 0.5`.
- A duplicated `Layout.*` property in one object is a load error, not a warning.
- The legacy views call `root.notify(...)`, so `main.qml` carries `property var root: shell`.

## Two things the user will ask about

- **Screenshots, always.** Every piece of UI work is presented as images in the conversation, not
  described. Render it, look at it, send it.
- **Say what is not done.** The unported views show an honest "Being rebuilt on the new kit"
  placeholder rather than pretending; keep that habit in the reporting too.
