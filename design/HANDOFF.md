# Where the Operator Client UI stands — 27 Sep 2026

The snapshot to resume from. **Read `design/LEVELS.md` first** (the levels), then `design/DECISIONS.md` (what was
approved and rejected, and why), `design/TABS.md` (the five areas), `design/BOARDS.md` (what every board is),
`design/PATTERNS.md` (the measured patterns every page is checked against). This file is where the *code* stands;
**`design/ENGINE-WORK.md` is what the Engine and the Worker still owe the UI.**

**Branch** `phase7/design-and-gui-rebuild` · last commit `040fe7f` · **174 tests pass, `ruff check .` clean.**
The suite only means something with `FALCON_TEST_DATABASE_URL` set — without it the DB tests skip and pytest still says
"passed"; `conftest.py` prints which run you are in.
**Canvas** <https://claude.ai/artifact/71rNVLEqFPPwJ2mPoD7Vpw> — version 58, 162 boards, arranged by hand: its index is
*merged, never replaced* (`design/README.md`).

---

## WHERE WE ARE

**The approved design is built.** All four build steps are done (27 Sep 2026): the kit, levels 1-2, every Admin page,
Record, Work, level 4, the connection states, the dialogs and the Worker's windows. Every page was screenshotted
against its board and sent to the user.

**What is next, in order:**
1. **The Engine / Worker pass** -- `design/ENGINE-WORK.md`, 15 items, fixed together in one pass (the user: *"I don't
   want to mix ui with engine work"*; only mundane fixes were done inline and are listed there). The biggest: the Worker
   relaying OS signals (1), built-in actions honouring their settings (4), a program inventory (5), report summaries and
   "seen" (7), every open channel for the Super User (10), a client PC's live state and "not reachable" (12), the three
   Worker windows still without triggers (14), and **registering machines from the local network** (15, the user's
   idea: the machine asks, a person confirms with a pairing code).
2. **Decisions that are the user's to make** (not to be settled alone): whether an Admin may govern more than one
   department (13 -- DG01's "assign an existing Admin"); the deferred items in `CLAUDE.md` still stand.
3. **Leftovers from before the rebuild** -- see *Not yet done* below.
4. Then the phases as `PHASES.md` orders them: Phase 8 human passes (GUI first), 9 packaging (incl. the Worker's
   windows as frozen exes), 10 hardening.

### What is built, page by page

Render any page with `environ-operator/Scripts/python.exe design/shot_gui.py design/shots <role> <view>` (set
`QT_QPA_FONTDIR=C:\Windows\Fonts`); the flags pick the state. The Worker's windows: `design/shot_worker.py`.

| Page | Board | QML | Screenshot with |
|---|---|---|---|
| Must see (Super User) | `OV02` | `OverviewView`, `DeptCard`, `DeptRolloutCard` | `super_user 0`, `FALCON_SHOT_SCALE=1` |
| Rollout | `RO05`, `RO06` | `RolloutView`, `MachineGrid` | `super_user 2`, `FALCON_SHOT_ROLLOUT_DEPT=<id>` |
| Record | `RC05` | `RecordView` | `super_user 3` |
| Work | `WK03` | `WorkView` | `super_user 4` |
| A department (level 2) | `DP18` | `DepartmentView` | `super_user 1`, `FALCON_SHOT_DEPT=<id>`, `FALCON_SHOT_MAX=machines` |
| Entering / inside an Admin (level 3) | `DP06`-`DP09` | `EnteringAdmin`, `HeldCard`, `SessionLid` | `FALCON_SHOT_ENTER`, `_ANSWER`, `_HOLD`, `_INSIDE`, `_TAB=<key>` |
| The Admin's home | `HO03` | `AdminHome` | `admin 0` |
| Tasks | `TK04`-`TK06` | `TasksView`, `NewTask` | `admin 1`, `FALCON_SHOT_TASK=<id>`, `FALCON_SHOT_NEWTASK=1` |
| Flows | `FL06`-`FL08` | `FlowsView`, `NewFlow`, `FlowTree` | `admin 2`, `FALCON_SHOT_FLOW=<id>`, `FALCON_SHOT_NEWFLOW=1` |
| Automation | `AU04`, `AU08`-`AU10` | `AutomationView`, `NewAutomation`, `Automate` (words) | `admin 3`, `FALCON_SHOT_NEWAUTO=<step>`, `_AUTOEV=<i>` |
| Actions | `AU05`-`AU07` | `ActionsView` | `admin 4`, `FALCON_SHOT_ACTION=<id>`, `FALCON_SHOT_CUSTOM=1` |
| Assistance | `AS03` | `AssistanceView` | `admin 5`, `FALCON_SHOT_FIND=<text>` |
| Reports | `RP03` | `ReportsView` | `admin 6` |
| Resources (from the Admin's home) | `RS03` | `ResourcesView` (`shell.subPage`) | `FALCON_SHOT_RESOURCES=1` |
| A client PC (level 4) | `CP03` | `PcView` (`shell.enterPc`, `heldPc`) | `FALCON_SHOT_PC=<id>`, `FALCON_SHOT_STEPOUT=1` |
| Connecting / lost / renamed | `ST01`, `ST03` | `ConnectView`, the lid's wordings | `FALCON_SHOT_CONNECT=<kind>`, `_LOST=1`, `_RENAMED=1` |
| Dialogs | `DG01` | `CostDialog` (`shell.ask`, `shell.showKey`) | `FALCON_SHOT_DIALOG=<extend/rekey/offboard/register/admin/key/force>` |
| The Worker's windows | `WR01`, `TK07` | `worker_client/windows` | `design/shot_worker.py` |

**Rules the build settled** (and that any new screen must keep):
- **One bar for every session and connection state** -- `SessionLid`, worded by `shell.lidMode`: inside, holding
  (Go in), blocked (Claim it back), lost (Retry now), renamed (Understood). No pill, no second banner, no status-line
  echo (the user, 27 Sep 2026: *"why is traversal alert never consistent"*). The one exception is DP09: a Super User
  holding an Admin, stepped out, is carried by the department's container and Must see.
- **Only an act with a cost interrupts**, and it is `shell.ask`: the cost said before the button, the button names the
  act, Cancel beside it, a one-time key shown once.
- **Double click enters, single click inspects**, at every level -- a machine mark's `doubleClicked` enters a client PC.
- **Nothing typed that can be picked** (folders from `index.folders`, files from search, machines as marks, actions by
  name); **nothing offered that cannot happen** (no "file is opened" trigger, no lock length the Worker ignores) --
  the gap goes to `ENGINE-WORK.md` instead.
- The PATTERNS.md rules: no squares with dots, no icon tiles, no pill lineups; legible before beautiful; never one
  container for many departments' machines; page, never shrink; test at ~12 departments x 60 machines.

### Not yet done (UI)

- **The Super User's Authority area** (rail index 1) still opens the pre-kit "Everything" screen (`HomeView` with
  `HierarchyRail`); departments are reached from Must see's cards. `HierarchyView.qml` / `HierarchyRail.qml` are
  orphaned and go once Authority is rebuilt.
- **A loading skeleton per cell** (ST02). Empty cells already say what is missing and the next step.
- **Still pre-kit components**, kept for the few places that use them: `DataTable`, `Picker`, `Btn`, `Eyebrow`,
  `Section`, `SegmentedControl` (restyled to plain-text tabs).
- The Record/Work/Rollout stubs in `shot_gui.py` are sample data, not an Engine; every page also runs against the real
  Engine through the same `falcon.call`s the tests use.

---

## Earlier: level 3 (25 Sep 2026)

Levels 1, 2 and 3 are built. **Level 3 (entering an Admin) went in on 25 Sep 2026** and is waiting
for the user to look at it in the running app (`design/run_gui.py super_user`: Authority → double-click
Operations → double-click R. Mensah → Enter → *End theirs and enter* → Go in). Two decisions were
taken to build it (`TABS.md` issue 8): **the Admin keeps their seven-entry rail**, and **you land on
their home page**. The user's standing instruction for this level: *literally show how their interface
looks* — the red lid is the only difference.

Level 3's four loose ends were closed the same day:
- **The held session is mirrored into Must see** — the same container, one line, in the header
  (`HeldCard.compact`, `objectName: "heldMirror"`).
- **The Admin's own screens are mounted** on their rail's entries — Tasks, Flows, Automation (the
  Dashboard tab), Actions (the Actions tab), Assistance, Reports — for an Admin at home and a Super
  User inside alike, because they are one interface. They are the pre-kit screens, table and all,
  shown as they are. Rollout · Record · Work (Super User) now say *Not designed yet*.
- **The Engine scopes what a Super User sees inside** (`protocol/viewing.py`). The client sends
  `"view": "session"` on the listed reads only while the window is inside (`falcon.viewThroughSession`,
  bound to `shell.insideNow`); `engine/dispatch.py` answers those as the Admin being looked through,
  and only for a Super User holding a traversal into an Admin workstation. Writes never narrow, and
  `Context.viewed_by` keeps the audit trail on the real Super User. Holding without looking narrows
  nothing — that is why the client has to say it.
- **"Not reachable" is a level-4 answer, not a level-3 one**: inside an Admin you see their data from
  the Engine, not their screen, so their machine being offline stops nothing. What was wrong instead —
  the lane telling you a signed-out Admin "gets a red screen" — now says *nobody is blocked*.

Then, in the order that keeps the primary path whole:

1. **Record** — audit, sessions, Views, all reports, deviations, violations. The biggest unbuilt area,
   and the one three Overview cells already open into.
2. **Rollout** — approval, rollout by department, the escalation lever.
3. **Work** — Tasks + Flows + watched assistance as one surface, with the single *Closed* filter that
   hands off to Record. A merge, not a rename.
4. **A proportions pass on the department.** Its cells stretch to fill the window while the boards size
   them to their content, so a small department looks emptier in the app than on the board. Not a
   fault; the next refinement.

**Level 4, a client PC, has not started.**

---

## What is built

**Level 1 — the Super User Overview** (`K01`). One page, a perfect 2 × 2 grid: **Authority**,
**Rollout**, **Today**, **Out of place**. No tabs, and no page title — the rail owns the name, so the
header is the time. Panels sit on the gradient; no sheet.

Clicking a cell **opens it in place**; Escape or the crumb restores the grid exactly. The composition
belongs to the cell and no two share a shape, so you know which you opened before reading a word:

| Cell | Composition | Board | Its shape |
|---|---|---|---|
| Authority | `OpenedAuthority.qml` | `K03` | the map as hero, two told panels beneath, the reading down the right |
| Rollout | *(retired: Rollout is its own page, `RolloutView`)* | `K04` | — |
| Today | `OpenedToday.qml` | `K05` | a lead running the whole height, a column of three beside it |
| Out of place | `OpenedOutOfPlace.qml` | `K06` | three full-width bands, shape to words, read downward |

A cell with **nothing to explain does not open** — checked on an empty system.

**The rail is the five areas** — Must see · Authority · Rollout · Record · Work (`IconRail.superNav`).
`adminNav` is untouched and waits for level 3, so the two rails spell the same place differently:
`main.qml` routes on `onMustSee` / `onAuthority` rather than literal keys, and `shell.show()` resolves
either spelling.

**Level 2 — the department** (`DepartmentView.qml`, boards `DP05`–`DP17`). Four cells in a **pinwheel**
— Who governs and Today on the diagonal — drawn on the frame, crumb `Authority › Operations`, the
department's identity colour beside the title. Reached by **double-clicking a department in the
Authority map**; `shell.departmentId` holds it, and because a department is *inside* Authority the rail
does not change.

- **One gesture.** Single click selects (an Admin's foot row swaps who the cell draws); double click
  enters and **the crumb grows**. That is the acceptance test, and it is in the suite.
- **Whoever the cell draws is whoever is selected** — at rest the first Admin in the stable order,
  which is why entering the first needs no click and entering anyone else needs exactly one.
- **`FleetGrid`** picks its mark size from the count — 46 px labelled, 30, 16, then bars past ~120 —
  and never scrolls. It mirrors `slot_size()` in `design/scale.py`; keep the two in step.
- **`Its machines` maximises**: double click and that chart fills the page with its words beside it,
  every mark back to 46 px with its hostname. Escape restores the four cells.
- **An Admin never owns machines.** A client PC belongs to a *department*: `accounts` carries
  `department_id` and no supervising Admin, an Admin may traverse into **any** PC in their department,
  and report routing resolves to **every** Admin in it. So the page says *"All N Admins here govern all
  M machines"*, an Admin is drawn with their own workstation and their work, and no station says
  "answers for N". The boards were redrawn to match on 25 Sep 2026.

**Level 3 — inside an Admin** (`SessionLid`, `EnteringAdmin`, `HeldCard`, `Ring`; boards `T05`,
`DP06`–`DP09`). The shell owns it: `shell.inside` is set by the double click, `shell.heldAdmin` is
*derived* from `falcon.session` and the tree (so a session already running at connect is still named),
and `insideNow` is both together. Inside, `IconRail.role` is `"admin"`, the sheet is the grey one
(`onFrame` false), `HomeView.asDepartment` scopes the home page, and a window-level `Shortcut` makes
Escape step out. One ticking clock (`shell.nowMs`) feeds every countdown; the arithmetic is in `Day`
(`leftText`, `leftFraction`). On the department, **double click** opens the drawn Admin
(`GridCell.openOnDoubleClick` — the Overview's cells still open on a click, by design), and the lane's
words come from four new `narrate` topics: `enter_cost`, `enter_answer`, `held`, `workstation`.
`shot_gui.py` renders each state: `FALCON_SHOT_ENTER=1`, `+ FALCON_SHOT_ANSWER=occupied`,
`FALCON_SHOT_HOLD=1`, `FALCON_SHOT_INSIDE=1` (all with `FALCON_SHOT_DEPT=1`, view 1).

**Words are generated, never written**: `operator_client/core/narrate.py`, pure functions over the
dicts the handlers already return, reached as `falcon.narrate(topic, data)`. Twelve words for a
sentence, six for a cell's `brief`, both enforced with a raise. `tests/test_narrate.py` holds every
topic to it.

---

## What is designed and not built

Nothing from the approved boards is left unbuilt except ST02's loading skeleton. What the boards show and the Engine
cannot yet supply (a screen image of a held machine, "what is in front", "not reachable", a program to pick, "where
it should be", a file's journey, ...) is in `design/ENGINE-WORK.md`, and each page shows its honest empty state or
leaves the cell out until then.

---|---|---|
| "Not reachable" when entering a client PC | `DP08`, fourth card | level 4 — needs the Engine to refuse an offline Worker |
| Assisted access (its own state machine) | `T06` | parked with level 3 |
| Record, Rollout, Work | none yet | no design |
| Level 4, a client PC | none | not started |

**One dependency this inherits:** `DP07` shows a picture of the held machine's screen. Nothing carries
that image today — the `screenshot` Action writes a PNG on the worker and returns a *path*. The Engine
work is agreed for later and is written down in `PHASES.md`. Until it exists that panel shows its empty
state rather than a placeholder image.

---

## Run it, render it, check it

```powershell
environ-operator\Scripts\python.exe design\run_gui.py super_user          # a real window, stubbed, no Engine
$env:FALCON_SHOT_EMPTY=1; ... design\run_gui.py super_user                # a system with no data

# the app, offscreen -> design/shots/gui-*.png
environ-operator\Scripts\python.exe design\shot_gui.py design\shots super_user 0     # Must see
$env:FALCON_SHOT_OPEN="rollout"; ...                                                # a cell opened
$env:FALCON_SHOT_DEPT=1; ... design\shot_gui.py design\shots super_user 1            # a department
$env:FALCON_SHOT_DEPT=1; $env:FALCON_SHOT_MAX="machines"; ...                        # a chart maximised

environ-engine\Scripts\python.exe design\gen.py                            # -> design/boards/*.dc.html
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 `
        "--screenshot=design\shots\DP05-Department.png" "file:///$PWD/design/boards/DP05-Department.dc.html"

$env:FALCON_TEST_DATABASE_URL="postgresql://falcon:falcon@localhost:5432/falcon_test"
environ-engine\Scripts\python.exe -m pytest -q
environ-engine\Scripts\python.exe -m ruff check .
```

Edge writes its `--screenshot` **after** the process returns, and only to an absolute path.

**The three sequences**, built from the real screenshots so a break in continuity is visible rather
than argued about: `design/journey_strip.py` (Must see → Authority → department → an Admin → a chart
maximised, shoot at 1440×2130), `flow_strip.py` (through holding a session, 1440×1620),
`maximise_strip.py` (the gesture alone, at 96 machines, 1440×1120). Each writes
`design/boards/<NAME>.html` to screenshot.

**Every piece of UI work is presented as images in the conversation**, never described.

---

## Traps already paid for

- **Never write a property from its own change handler.** `onInsideNowChanged` setting `inside` was a
  binding loop *and* sent the window to Must see, because the rail was still the Admin's when
  `show("authority")` ran. Watch the input (`onHeldAdminChanged`) instead.
- **A `MouseArea` sized from its `Row` is a polish loop** that starves every other layout in the window
  (the rail and top bar rendered garbled). Wrap the row in an `Item` and fill that.
- **`signal left()` never registers.** `left` collides with an `Item` member: the signal is dropped and
  the handler refused with *Cannot assign to non-existent property "onLeft"*. It is `back()`. Suspect
  any signal named after an anchor or geometry property.
- **QML errors were invisible** until `gui/app.py` connected `engine.warnings`. Keep that — it caught a
  deleted function and a misnamed property within minutes of being added. The GUI test fixture
  disconnects it before teardown, because tearing the engine down re-evaluates bindings against a
  `falcon` that is already gone.
- **Read the fields the handlers actually return.** `updates.rollout_health` gives `pcs_behind` (rows
  saying `escalated`), not `pcs`; a violation row carries `found_on_pc_id` and `hostname`. Reading the
  wrong names drew every machine green while the page named a violation beside it — no crash, just a
  page contradicting itself.
- **A page drawn in the Overview's language sits on the frame.** `main.qml`'s sheet is transparent when
  `shell.onFrame`; forgetting a new page there gives it the old Admin-console grey sheet.
- **A `property var` is a `QJSValue` from QML and a plain dict when it came back through the bridge.**
  `tests/test_operator_gui.py` has a `val()` helper that reads either.
- **A nested layout fills by default**: a `RowLayout` inside a `ColumnLayout` starves its sibling
  unless told `Layout.fillHeight: false`.
- **Size a panel by its content, not a fraction of the window**, when its content is words:
  `Layout.preferredHeight: 77 + body.implicitHeight`.
- A component's children land where you meant only with a **`default property alias`**.
- `icon` is FINAL on `AbstractButton` — our buttons use `iconName`.
- `font.families` is not in this Qt build (`Theme.pick()` resolves one at runtime), and
  `font.pixelSize` rejects fractional values.
- A duplicated `Layout.*` property in one object is a **load error**, not a warning.
- The legacy views call `root.notify(...)`, so `main.qml` carries `property var root: shell`.
- **`GridCell`'s body is a Column**: a child with `height: parent.height` collapses to 0. Use `height: <cellId>.room`.
- A `RowLayout` whose cells `fillHeight` fills too, whatever its `preferredHeight`: give it `Layout.maximumHeight`
  and `Layout.fillHeight: false` to cap it.
- A `bool` bound to `a && b` gets `undefined` when `a` is missing -- write `!!a && b`.
- A new singleton does nothing until it is listed in `qmldir` (`singleton Name 1.0 Name.qml`); until then calls on
  it fail with "is not a function".
- `grabWindow` needs `from PySide6.QtQuick import QQuickWindow` imported, and offscreen shots need
  `QT_QPA_PLATFORM=offscreen` -- without it a real topmost window opens and the capture hangs.
- `shot_gui.py`'s `_at(hour, days_ago)` takes an hour of the day and a day count, never negative hours.
- A state set before the page has loaded shows an empty page (the page never fetched); set it in `later()`.
- Views outside the Operator's main document still reach `shell` (the root id) and `falcon`, but not other ids
  such as `overview` -- pass what they need as properties (`PcView.holder`).
- Worker tests build `WorkerConfig(windows=False, ...)`: with windows on, a block or a task opens real windows.

---

## The code map (`operator_client/gui/qml/`)

**The kit**: `Theme` (tokens, `tone()`, `series()`, `initials()`), `Icons`+`Icon` (stroke glyphs as SVG
path data via `QtQuick.Shapes` — no image assets), `Txt`, `Chip`, `TBtn`, `GBtn`, `IconBtn`, `Avatar`,
`Pills`, `CardRow`, `DetailCard`, `KeyRow`, `Sidebar`/`SbSection`/`SbRow`, `IconRail`, `TopBar`, `Body`,
`HomeView`, `main.qml` (gradient frame, floating pill, toast, status line).

**The charts**, all `QtQuick.Shapes` and rectangles — no charting library: `Panel`, `Legend`, `Hero`,
`StackedBars`, `Waffle`, `FleetGroups`, `FleetGrid`, `DeptSlots`, `QuietStrip`, `Trend`, `MiniBar`,
`HealthCard`, `OrgMap`, `Arcs`, `RoutingMap`, `DayTimeline`, `DevStrip`, `EnteredRows`, `TierBars`,
plus `Sentence` and `ReadingBody` for the words.

**Shared logic**: `Day.qml` (singleton) is the day arithmetic — `nowHours`, `hoursOf`, `sessionState`,
`blocksFor`, `lanesFor`, `windowStart`/`windowEnd`. A lane is a PC and a block is a session whatever
page is asking, so no view owns it.

**The pages**: `OverviewView` holds the Overview's data and grid, `GridCell` is one cell, the four
`Opened*.qml` are its compositions; `DepartmentView` is level 2. Everything on them is real —
`hierarchy.tree`, `updates.rollout_health`, `hierarchy.sessions_today`, `resource.violations`,
`audit.deviations`, `reports.routing_get`, `task.list`, `flow.list`, and `audit.recent` with prefix
`update.attempt`.

**Built in the rebuild** (27 Sep 2026): the kit (`MachineMark`, `PagedRow`, `PagedColumn`, `InfoCard`, `SentenceSlot`,
`FlowTree`, `MachineGrid`, `GridCell.room`), the singletons `Fleet` (machine status), `Automate` (trigger and action
words), and every page in the table at the top. `Field` is restyled (no floating placeholder).

**Still pre-kit**: `Btn`, `DataTable`, `Picker`, `Eyebrow`, `Section`. **Orphaned, and deletable once the Super User's
Authority area is rebuilt**: `HierarchyView.qml`, `HierarchyRail.qml`. Retired in the rebuild: `FleetGrid`,
`OpenedRollout`, `ControlView`, `ActionPicker`, the floating state pill.

**The design** is `design/*.py` → `design/boards/*.dc.html` → the canvas. `design/BOARDS.md` is the map
of what every board is; the canvas's own `INDEX` board is out of date.
