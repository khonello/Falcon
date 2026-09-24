# Where the Operator Client UI stands — 24 Sep 2026

A snapshot for a fresh session: what exists, what was decided, and the one thing to do next.

**Read in this order:** `design/DECISIONS.md` (what the user approved, rejected and why — it is what
stops the rejected shapes coming back) → `design/BOARDS.md` (what every board is) → this file (where
the code stands and what to do next).

**Design canvas:** <https://claude.ai/artifact/71rNVLEqFPPwJ2mPoD7Vpw> — "Falcon Operator Design",
76 boards, version 41. Rejected proposals have been deleted from it. Branch
`phase7/design-and-gui-rebuild`; **122 tests green, `ruff check .` clean**.

---

## CONTINUE FROM HERE — traversal into an Admin

**No GUI design, no code, no test.** The Engine enforces it and the integration tests cover it; only
the UI is missing. It is Hierarchy-backbone behaviour, so it is settled *before* the pages that
depend on it (Views, Reports, Updates, Tasks, Flows, Assistance for Super User; then the Admin
views).

**The question to answer:** what the window becomes when a Super User enters an Admin's workstation,
and how you get back out.

- The frame **never** changes colour (settled rule) — so what says "you are inside someone else's
  machine"? Today the shell has a floating state pill, the status line and `TopBar`; the design has
  to make that unmistakable without touching the gradient.
- What happens to the **rail**: does the Super User keep their own eight entries, gain the Admin's
  (Automation, Actions — the combo only reachable by entering an Admin), or swap wholesale?
- What the **body** shows, what is hidden, and what the countdown looks like: a traversal carries a
  deadline (`traversal_limit_minutes`) and can be extended; that is chrome, not a page.
- **Getting back**: ending the session vs. the deadline expiring vs. being blocked by a superior.
- The same shape must answer **Assisted Access**, which is a *separate* state machine — do not reuse
  the traversal code path (design rule from the spec).

**What already exists to build on**

| Layer | What is there |
|---|---|
| Engine | `hierarchy.traverse` (`{pc_id, force}`; `force` = block-or-end, vertical only, never against an un-evictable Super User), `hierarchy.end_session`, `hierarchy.extend_session`, `hierarchy.session_state`, `hierarchy.claim_native`; pushes `session.blocked`, `session.ended` |
| Bridge | `falcon.traversing`, `falcon.superUserBanner`, `falcon.sessionText`, `falcon.session`; state-changing replies update `ClientState` inside `bridge.request` |
| Tests | `tests/test_integration.py` scenario 1 and `test_network_drop_mid_traversal_with_real_clients`; `tests/test_operator_gui.py` drives a real traversal through the bridge |
| Boards | `Traversing` and `Occupied` exist from the Admin pass and are in the current kit — read them first; they are the starting point, not necessarily the answer |
| Legacy code | `HierarchyView.qml` (pre-kit) holds the old traverse / extend / end levers and is **no longer mounted**; `HomeView.qml` is the built Hierarchy screen |

**How to work it** (the process that produced everything above): draw it as a board in `design/`
first → `gen.py` → screenshot with Edge → show the user → only then QML + a test. Every piece of UI
work is presented as **images in the conversation**, never described.

Then, in order: the other Super User pages (Views, Reports, Updates, Tasks, Flows, Assistance — none
designed, none built) · chart treatments from `C01`–`C10` (two applied, the rest are boards only;
`X01` is designed and unbuilt, recommendation in `DECISIONS.md`) · the Admin views, one at a time,
deleting each legacy view as its replacement lands · the remaining states (connect, loading,
disconnected, `Dialogs`, the Worker Overlay and Dialog) · un-pause Phase 7 in `PHASES.md` and update
`design-brief.md`'s status line.

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
