# The levels, and the rule for working on them

Written down 24 Sep 2026, from the user, after a pass that mixed two levels in one set of boards.

## The rule

**One level at a time.** Its UI is settled before the next one is opened. Do not put a second level's
chrome, state or screens into the level being worked on — a badge, a lid, a rail entry or a panel that
belongs to the level below is a mistake, not a preview.

**We are at DEPARTMENT level.** Everything drawn or changed until that is settled must be department
work.

## The levels

| | Level | What it is | Status |
|---|---|---|---|
| 1 | **Super User** | the whole system: the Overview (`K01`) and its four cells opened (`K03`–`K06`) | **designed and built** |
| 2 | **Department** | a place: its Admins, its client PCs, its day, what waits on you. Where you choose whom to enter. | **in progress — this is the current work** |
| 3 | **Admin** | what you get when you traverse into an Admin's workstation | **already designed, and built** — see below |
| 4 | **Client PC** | a worker's machine, enterable from the department by a Super User, or by its Admin | not started |

Levels 1 and 2 are **looking** — nothing is held, nobody is blocked, no clock runs. Levels 3 and 4 are
**holding** — a session exists, a deadline runs, someone is blocked out of their own machine.

## What "traverse into an Admin" shows

**The Admin interface that was already designed and built.** Traversal does not get a new set of
screens invented for it. When a Super User enters an Admin's workstation they are handed that Admin's
own surfaces — the work from the earlier pass:

- Boards: `Main` (Admin at home), `Tasks`, `Flows`, `Automation`, `Actions`, `Automation-Live`,
  `Assistance`, `Resources`, `Reports`, plus `Traversing`, `Occupied`, `Assisted` for the session states.
  They live in `design/v5.py` and `design/v7.py` and are on the canvas, rows 1–4.
- QML: `TasksView`, `FlowsView`, `ControlView`, `AssistanceView`, `ReportsView`, `HierarchyView`,
  `HierarchyRail` — all still in `operator_client/gui/qml/`, mounted, tests passing.

**None of it has been discarded**, and none of it is to be redesigned as part of department work.

## What belongs to which level (the mistake to avoid repeating)

| Belongs to **department** (level 2) | Belongs to **admin** (level 3) |
|---|---|
| the department page: its Admins, its client PCs, its day, what waits on you | the red lid / "you are inside" badge, and the countdown |
| choosing an Admin, and choosing a client PC | the rail becoming theirs |
| the act of asking to enter, and the answer that comes back | everything shown *inside*: their Automation, Actions, Tasks, Flows |
| — | leaving, the deadline expiring, being evicted |

The red lid is **admin-level chrome**. It must not appear on a department screen.

## Crossing a level is the same gesture as everything else

**Double click enters, single click inspects** (`TABS.md`). Crossing from Super User to a department,
and from a department into an Admin, is that gesture repeated — not three different navigations. And
starting a session does not move the window: it draws a container, and double-clicking *that* is what
puts you at the level below.

## The levels share one visual language; depth is told, not restyled

Super User and department are **deliberately close**: the same containers, the same four-cell
composition, the same words. A level is not a new skin, and nothing about the frame, the palette or the
kit changes as you go down. What tells you where you are:

1. **The crumb** — `Everything › Operations` — which grows by one step per gesture.
2. **The page's own title**, which is the name of the place you are in.
3. **The subject's identity colour**, stamped small beside that title. Departments already carry one
   from the categorical ramp (Operations, Finance, Logistics). It marks the place without touching the
   four reserved state colours, and it is the cheapest honest way to say "you are one level in".
4. **The rail stays the Super User's five** while a Super User is looking — you are deeper inside
   **Authority**, not somewhere else. The rail says which area; the crumb and the title say how deep.

Holding a session (level 3 and 4) is the only thing that changes chrome, and it does it with the lid
— because that is a state, not a depth.

## Every level gets a mood board first

Super User had `S01`–`S04`, the Admin console had `M01`–`M15`. A level's approaches are put side by
side at the same size and **picked from** before any page is composed. Skipping that step is what
produced two wrong passes at the department.

**`DP01`–`DP04` is the department's** — shape, people, machines, doors; four approaches each.
Nothing on them is a finished screen, and nothing on them is from the level below.

## The boards, sorted by level

- **Department (current work):** `DP01`–`DP04` the mood board, to pick from · `T01` the department at rest · `T02` an Admin chosen · `T04` the
  answer that comes back when you ask to enter.
- **Admin level, parked until level 3 is opened:** `T03` (inside an Admin), `T05` (the lid and its
  clock). Both were drawn during department work, which was the mixing. They stay on the canvas as
  parked material; when level 3 is opened, the question they answer is how the **existing** Admin
  screens are wrapped, not what replaces them.
- **Its own state machine, not a level:** `T06` assisted access. Parked with the same reasoning.

## The rail

Named areas, not one tab per feature: **Must see · Authority · Rollout · Record · Work** for Super
User, Assistance folded into Work. `design/TABS.md` holds the mapping, and **its nine open issues were
all settled on 25 Sep 2026** — so drawing is no longer blocked on it. The Admin rail is the one piece
deliberately left for level 3.

**The rail does not change at department level.** A Super User looking at a department is deeper inside
**Authority**; the crumb and the title say how deep.

## Settled while working at department level

- **The four cells are named: Who governs · Its machines · Today · Waiting on you** (25 Sep 2026, the
  user's call, `TABS.md` issue 9). They are **cells, not tabs** — the department is one page — and
  **Today is the wide one**, because a department at rest is read by its day.
- **Four cells, and the widths vary** — the user's call: *"the width varies and usually four is the
  sweet spot."* A level's page is four cells, never a stack of full-width bands; the widths do the
  ranking and which cell is wide is the page's signature.
- Detail arrives by **opening a cell**, not by crowding the page — the Overview's rule carried down.
- Everything else in `DECISIONS.md` still holds.
