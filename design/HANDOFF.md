# Where the Operator Client UI stands — 24 Sep 2026

A snapshot for whoever picks this up next, which will be a fresh session. It records what exists,
what was decided, and what to do next.

**Read in this order:**

1. **`design/DECISIONS.md`** — what the user approved, what they rejected and why, the principles
   that shape every page still to be designed, and what has not been started. The Overview was
   redesigned several times before it landed; this is the file that stops the rejected shapes coming
   back.
2. **`design/BOARDS.md`** — what every board on the canvas is.
3. This file — where the code stands.

**Design canvas:** <https://claude.ai/artifact/71rNVLEqFPPwJ2mPoD7Vpw> — "Falcon Operator Design", 74
boards, version 40. Rejected proposals have been deleted from it.

## The short version

Phase 7 was paused because the GUI was *functional, not acceptable*. A full design was then made and
reviewed over many rounds, and the Super User **Overview** is now built on it.

**The Overview is one page and a perfect 2 × 2 grid** (board `K01`): **Authority**, **Rollout**,
**Today**, **Out of place**. No tabs. Each cell's title sits above it on the frame with a generated
state phrase beside it; the header is "Must see" and the time, with no description of the
organisation. The panels sit on the gradient — there is no grey sheet behind the body.

**Clicking a cell opens it in place** (board `K03`) rather than navigating: the cell grows where it
is and the panels around it become the gradient that explains it. **Authority is built end to end**
— its composition is `OpenedAuthority.qml`: the map as the hero, *Its client PCs* and *Sessions
there* as told panels beneath, and the reading down the right for the whole height. Escape or the
breadcrumb restores the grid exactly. **The composition belongs to the cell**, so Rollout, Today and
Out of place each need their own; Rollout's is already drawn (board `K04`).

Words are generated, never written: `operator_client/core/narrate.py`, held to twelve words for a
sentence and six for a cell's `brief`, with `tests/test_narrate.py` on every rule.

## Run it

```powershell
environ-operator\Scripts\python.exe design\run_gui.py super_user          # stubbed, no Engine
$env:FALCON_SHOT_EMPTY=1; ... design\run_gui.py super_user                 # a system with no data
```

## What to do next, in order

1. **Finish the opened state.** Rollout, Today and Out of place each need their own composition.
   Rollout's shape is drawn on board `K04` and is deliberately unlike Authority's — its subject is a
   fleet, so the hero runs the full width. `GridCell.openable` gates every cell: one with nothing to
   explain stays shut.
2. **Traversal into an Admin.** No GUI design, no code, no test — what the rail, the frame and the
   body become when a Super User enters an Admin's workstation, and how you get back. The Engine
   enforces it and the integration tests cover it; only the UI is missing. It is a backbone
   behaviour, so settle it before the pages that depend on it.
3. **The other Super User pages**: Views, Reports, Updates, Tasks, Flows, Assistance. None designed,
   none built.
4. **Pick chart treatments** from `C01`–`C10`. Two are applied (assistance → one line per pair;
   routing → lines and chips); the rest exist only as boards. `X01` (choosing a treatment in the
   slot) is designed and unbuilt, and the recommendation on it is in `DECISIONS.md`.
5. **Port the Admin views** one at a time against their boards, deleting each legacy view as its
   replacement lands. What carries over from the Super User work is a deliberate later decision.
6. **The remaining states**: the connect screen, loading, disconnected, the dialogs (`Dialogs`
   board), and the Worker Overlay and Dialog (`Worker` board).
7. **Un-pause Phase 7** in `PHASES.md` and update `design-brief.md`'s status line.

## How it was decided

The user's own Slack-style app (`ClassCap/classcap_desktop`) was the agreed reference for *architecture*
— coloured frame as identity, slim icon rail, accordion sidebar, white-on-dark body — not for colour.
A 15-board mood board (M01–M15) put every component in three or four variants; the user picked from it,
and those picks are the kit. Super User was then rejected twice: first for being the Admin screens with
items removed, then for being too restrained; the answer was to draw the system (D01–D03).

## Rules that are settled

- **One gradient frame**, always: `#121220 → #2A1F50 45% → #4B2F8A`, 155°. It never changes with state.
  Session state is said by a floating pill, the status line and the detail card — never by the frame.
- **Four toned meanings only**: accent `#8AA6E0`, ok `#7FB396`, warn `#D2A468`, danger `#DD8A8A`, each
  with a ~14 % tint. A border or highlight is a toned variation of a core colour, never a new hue.
- **Selection** is a 1 px inset line in a soft accent, or a filled muted row in the sidebar. **Never a
  left-edge accent** — the user's strongest dislike.
- **A body row is one line** — short title, at most one value, a chevron. No sentences in a body; the
  detail card explains. Titles ≤ 4 words, values ≤ 3.
- **No accordions in a body** (rows select, the card carries depth); accordions live *inside* the card.
- **The detail card** sits in a reserved 372 px lane, is always present, never opens or closes, has no
  close button, and shows an empty state when nothing is selected. The body column is a fixed 620 px.
- **The sidebar names the category; the pills filter on a different axis.** Never the same axis twice.
- **Stable order** in the sidebar (admins, then PCs by hostname). It never resorts by state.
- **The card shows what is selected**, never what was just triggered; results are confirmed by a toast.
- **Avatars are neutral** with no state dot; session state is an icon (person / lock / monitor / shield).
- **Buttons are tonal or ghost only.** Chips are soft. Inputs are filled.
- **No tables anywhere. Cards in one space are all one size.** Consistency within a space; a different
  accepted variant in a different space is fine.
- **Super User is designed for its own job**, not the Admin screens adapted: what cannot be done in that
  space is not named in it (no Automation/Actions entry at all).
- **A chart must pass one test**: *what question does this panel answer, and does the shape answer it
  faster than a sentence would?* Three treatments were cut for failing it (a chord diagram, an orbit
  diagram, an occupancy band) — each was legible only once its geometry had been explained. Expressive
  treatments are kept as alternatives, never as the default.
- **Panel density** (`P01`): a panel is a Figure (1), a Chart (2), a Chart told (3) or a Reading (4), and
  a layout is a sequence of them running diagonally from shape to words. The page explains itself without
  a click; the click is kept for the item-level question. A sentence is generated from a condition, never
  written, and falls back to the plain fact when no condition matches.
- **Layout is editorial, not a preference**: one layout per page, chosen once, never per viewer.
- **Each page has its own structural signature**, so you know which page you are on before reading a
  word: page 1 is a band over two columns, page 2 an equal quartet, page 3 a lead and a column.
- **A panel is never blank** (`P05`). Three cases, and only two get a notice: a **zero is a result** and
  is drawn normally; **nothing yet** keeps the chart's own structure, quietened, with the notice laid
  over it; **not enough** draws the shape's frame and says what is missing.
  The gradient itself is **declared, not assumed**: every panel carries a `density`, each page exposes
  its `readingOrder`, and `tests/test_operator_gui.py` refuses a page whose density ever falls. A *reading* panel takes no
  overlay — its content is words, so it simply says so, and keeps the rules its fact rows would sit on.
- **Visual first, text on demand** (`X02`): a page is nearly wordless; clicking a chart settles it to one
  side and brings text beside it — one sentence, then facts one line each, then at most one action. The
  chart stays on screen, because the text is an extension of it.
- **Charts**: identity uses a validated categorical ramp (`#3987e5 #d95926 #199e70 #c98500 #d55181`,
  checked against the `#12151C` chart surface); the four status colours stay reserved and always carry a
  word beside the hue.

## What exists

### The design (this folder → the canvas)

| Row on the canvas | Boards |
|---|---|
| The Admin shell | `Main`, `SuperUser`, `Traversing` |
| Sessions | `Occupied`, `Assisted`, `Tasks` |
| Work | `Flows`, `Automation`, `Actions`, `Automation-Live`, `Assistance` |
| Policy | `Resources`, `Reports`, `States` |
| Worker + language | `Worker`, `Tokens`, `Dialogs` |
| Mood board | `M01`–`M15` — every component in 3–4 variants |
| The lane | `Lane-Filled`, `Lane-Empty` |
| Super User | `SU-Departments`, `SU-Views`, `SU-Updates`, `SU-Audit` |
| Super User mood board | `S01-Shape`, `S02-Figures`, `S03-Authority`, `S04-Descent` |
| **Super User dashboards** | `D01-Glance`, `D02-Hierarchy`, `D03-Record` ← the direction the user loved, and `D04-Department`, the descent |
| **Chart mood boards** | `C01`–`C10` — one chart type per board, four ways to draw it (rollout, fleet, confirmations, hierarchy, sessions, assistance, routing, violations, work, the figures) |
| **Layout structures** | `L01`–`L06` — the same content in three, four and five panels, weighted differently |
| **Behaviour** | `X01` choosing how a slot is drawn · `X02` reading a chart (visual → text) |
| **The map** | `INDEX` — which board is what, and which page's slot it fills |
| **The pages, composed** | `P01` the four panel densities · `P02`–`P04` the three pages built from them · `P05` a panel is never blank — **built** |

### The code (`operator_client/gui/qml/`)

Built on the new kit and running: `Theme.qml` (tokens, plus back-compat aliases so unported views still
load), `Icons.qml` + `Icon.qml` (stroke glyphs as SVG path data drawn with QtQuick.Shapes — no image
assets), `Txt`, `Chip`, `TBtn`, `GBtn`, `IconBtn`, `Avatar`, `Pills`, `CardRow`, `DetailCard`, `KeyRow`,
`Sidebar`, `SbSection`, `SbRow`, `IconRail`, `TopBar`, `Body`, `HomeView`, and a rewritten `main.qml`.

**The Overview** (`OverviewView.qml`) holds the data and the grid; `GridCell.qml` is one cell, with
its title above it on the frame, `openable` gating whether it opens, and the never-blank notice.
`OpenedAuthority.qml` is Authority's opened composition. `DeptSlots`, `ReadingBody`, `Sentence`,
`Panel`, `Legend`, `Hero` and the chart components are the kit it is built from.
**`GlancePage`, `HierarchyPage` and `RecordPage` were deleted** when the three tabs went.

**The sentence layer is real code**: `operator_client/core/narrate.py`, pure functions over the dicts
the handlers already return, reached from QML as `falcon.narrate(topic, data)`. The twelve-word limit is
enforced in `_say` (a raise, not a long line), a topic with no matching condition states the plain fact,
and `tests/test_narrate.py` holds every sentence to those rules. `design/shot_gui.py` with
`FALCON_SHOT_EMPTY=1` renders a freshly bootstrapped system, which is how the never-blank rule is checked
in the real app rather than only on a board.

**The Super User dashboards were ported** (D01–D04) and then superseded by the grid. Rail entry **Overview**, which Super User leads with;
`OverviewView.qml` holds the data and three pages — `GlancePage`, `HierarchyPage`, `RecordPage` — behind
pills, with a breadcrumb that descends into one department and backs out again. The chart kit, all drawn
with `QtQuick.Shapes` and plain rectangles (no image assets, no charting library): `Panel`, `Legend`,
`Hero`, `StackedBars`, `Waffle`, `Trend`, `MiniBar`, `HealthCard`, `OrgMap`, `Arcs`, `RoutingMap`,
`DayTimeline`, `TierBars`. The categorical ramp is stated once as `Theme.chartSeries` / `Theme.series(i)`.

Everything on those pages is real: `hierarchy.tree`, `updates.rollout_health`, `hierarchy.sessions_today`,
`resource.violations`, `audit.deviations`, `reports.routing_get`, `task.list`, `flow.list`, and
`audit.recent` with prefix `update.attempt` for the confirmations trend. A panel with nothing behind it
says so instead of drawing an empty chart.

Still the pre-kit versions, mounted hidden so their tests keep passing: `TasksView`, `FlowsView`,
`ControlView`, `AssistanceView`, `ReportsView`, `ConnectView`, plus `Btn`, `Field`, `DataTable` etc.

**Role differences live in exactly one place**: `IconRail.qml`'s `adminNav` / `superNav`. Each entry now
carries a `key`, and `main.qml` routes on `shell.viewKey` rather than an index, so the two rails can differ
in length; a view switches to another with `shell.show("hierarchy")`.

### Checks

Full suite → 117 passed (`tests/test_operator_gui.py` → 2 passed, 1 skipped). `ruff check .` → clean (`design/` is excluded; its
long inline-style lines are the point).

## Qt gotchas already paid for

- A **nested layout fills by default**: a `RowLayout` inside a `ColumnLayout` will starve its
  sibling unless told `Layout.fillHeight: false`. This cost an hour twice.
- A component's children only land where you meant if the alias is a **`default property alias`**;
  otherwise they attach to the wrapper and spill over everything above it.
- `icon` is FINAL on `AbstractButton` — our buttons use `iconName`.
- `font.families` is not available in this Qt build — `Theme.pick()` resolves one family at runtime.
- `font.pixelSize` rejects fractional values.
- The legacy views call `root.notify(...)`, so `main.qml` carries `property var root: shell`.

## Working commands

Two things paid for since: Edge writes its `--screenshot` **after** the process returns and only to an
absolute path, so wait a moment and check the file; and `font.pixelSize` still rejects fractional values,
so the boards' 11.5 / 12.5 px sizes map onto `Theme.fMeta` / `Theme.fBody`, never `+ 0.5`.

```powershell
environ-engine\Scripts\python.exe design\gen.py            # -> design/boards/*.dc.html (git-ignored)

# a board, as a picture
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 `
        "--screenshot=design\shots\D01-Glance.png" "file:///$PWD/design/boards/D01-Glance.dc.html"

# the real app, as a picture (stubbed bridge, offscreen)
environ-operator\Scripts\python.exe design
un_gui.py super_user   # a real window, stubbed, to click through
environ-operator\Scripts\python.exe design\shot_gui.py design\shots admin
environ-operator\Scripts\python.exe design\shot_gui.py design\shots super_user 0 1     # Overview, page 1
environ-operator\Scripts\python.exe design\shot_gui.py design\shots super_user 0 1 1   # ... descended into department 1

environ-engine\Scripts\python.exe -m pytest tests/test_operator_gui.py -q
```

To change the design: edit the module, re-run `gen.py`, screenshot, then publish the changed
`boards/<name>.dc.html` to the canvas as `project/<name>.dc.html`. `design/README.md` has the detail.

## Two things the user will ask about

- **Screenshots, always.** Every piece of UI work is presented as images in the conversation, not
  described. Render, look at it, send it.
- **Say what is not done.** The unported views show an honest "Being rebuilt on the new kit" placeholder
  rather than pretending; keep that habit in the reporting too.
