# Areas, not features: what the rail is called at each level

Decided 24 Sep 2026. **The nine open issues were settled 25 Sep 2026** — what follows is the decision,
not a proposal. The reasoning for each is at the bottom, under *The nine, settled*, so a closed
question is not reopened by accident. Still nothing here is drawn or built.

## The decision

The rail stops being one tab per feature area. Features are gathered into **areas named after the
question a person is asking**. Super User goes from eight tabs to **five**, and **Assistance folds
into Work**.

| Area | Gathers | The question it answers |
|---|---|---|
| **Must see** | the Overview (`K01`, built), plus the **unaddressed reports** | what needs me right now |
| **Authority** | departments, Admins, client PCs, appointing, display names, entering, **report routing** | who governs what, and where nobody does |
| **Rollout** | versions, approval, escalation, fleet health | what version is where, and what is stuck |
| **Record** | audit, sessions, Views, **all reports**, deviations, violations, finished work | what happened, and who was where |
| **Work** | Tasks, Flows, **live assistance (watched, not started)** | what is moving through the organisation |

## How an area is entered: through its contents, not through tabs

**Settled 24 Sep 2026, and it governs every area and every level.** An area is not a page with tabs
across the top. It is a small set of **containers — a chart, a diagram, a drawing, a figure — one per
thing the area covers**. You enter a subject by going into the thing itself.

### One gesture, one meaning

| Gesture | Means | Everywhere |
|---|---|---|
| **Single click** | *select / inspect.* The mark or row is selected and its text arrives beside it. Nothing moves, nothing opens. | a chart mark, a row, a slot |
| **Double click** | *go deeper into this.* | any container that has something behind it |
| **Escape, or the crumb, or the back arrow** | come back out, exactly as it was | everywhere |
| **Enter key** | same as double click, on the focused container | keyboard equivalent, required |

This settles a conflict between two rules that were both approved and disagreed: `K01` said *clicking a
cell opens it*, while `X02` said *clicking a chart brings its text beside it*. They cannot both own the
single click. **Single click inspects; double click enters.** It is also the idiom of every desktop
file manager, so it arrives already learned.

### What "deeper" means depends on the container

Both are the same gesture and both are reversed the same way; only the distance differs.

- **A container that owns a subject within its area** recomposes the area around it: it grows where it
  stands, the other containers re-scope to what was opened, the crumb gains a step. (`K03`–`K06`.)
- **A container that stands for a place with its own page** — a department, an Admin, a client PC —
  takes you to that place. The crumb gains a step the same way.

**Double-clicking a mark enters that mark's subject; double-clicking the container's own ground enters
the container's subject.** Double-clicking Operations inside the Departments map goes to Operations;
double-clicking the map itself goes to Departments.

### Not everything is enterable, and the enterable must say so

- A container with **nothing behind it** does not respond to a double click — the same rule as *a cell
  with nothing to explain does not open* (`P05`, `K01`).
- **An enterable container advertises it**: the pointer changes, the container lifts on hover, and the
  hover state names where it goes ("Operations ›"). Nothing invisible is load-bearing.
- A container is enterable only when there is a genuine space behind it. A figure, a legend, a single
  sentence are not doors.
- **One level per gesture.** Depth comes from repeating the gesture, never from one click landing two
  levels down.

### Starting a session makes a container; entering it is the same double click

**The user's proposal, 24 Sep 2026, and it keeps traversal inside the one gesture instead of making it
a special navigation.**

Starting a traversal **does not move your window**. It creates the session, and the session shows up as
a **small landscape container** on the page where you started it — the Admin or the client PC you
entered, now marked as held, carrying the countdown.

- **Double-clicking that container takes your window into that level**, where the lid at the top says
  what is going on. Exactly the gesture used for everything else.
- **Escape comes back out while you are still holding the session.** The container stays where it is,
  still counting down, and the same double click goes back in. Holding and looking are two different
  things, and the Engine already works this way: the session lives until it is ended or expires,
  whatever your window happens to be showing.
- **Leaving is an explicit act** — on the lid, or on the container. It is never a side effect of
  navigating away.
- The same shape one level further down: an Admin entering a client PC gets the same container, and
  double-clicking it is what puts them in that machine.

This also gives the countdown a home while you are *not* inside: it is on the container, in the place
that names the machine, rather than floating over a page it has nothing to do with.

**Where the container lives when you have navigated elsewhere — settled: both.** It stays on the page
where it was started, *and* it is mirrored into Must see for as long as it exists, because a held
session is by definition something you must see. There is only ever one per person
(`sessions.active_for_account` returns one), so there is never a list of them. The mirror is the same
container, not a second design, and it obeys the two-areas rule below: Must see is one of the two
places, so the duplication is allowed.

**What the container can honestly show.** There is **no screen streaming in the protocol** — nothing in
`engine/` or `protocol/` carries frames, and Assisted Access's "screen, read only" ceiling is a design
intention with nothing implementing it. What exists today:

- `control.metrics` — CPU, memory and idle seconds, reported by the Worker client;
- the active window and the machine's own identity;
- a **`screenshot` Action** (`engine/control/actions.py`), which is a still taken on demand, not a feed;
- the session itself: who is blocked, how long is left, how you got in.

So the container is a **live-state card, not a viewport**: metrics, the machine, the countdown. Drawing
a fake screen preview would promise something the system cannot do. If a real preview is wanted, a
still via the `screenshot` Action is reachable now; a live feed is a new Engine capability and a
separate decision.

### It is the same gesture at every level

Super User → department → Admin is **one gesture repeated**, not three different navigations:
double-click a department in Authority to go to the department; double-click an Admin there to enter
them. The Admin level then hands over the Admin screens that already exist.

## If tabs are ever used anyway

Somewhere one will be needed — a filter inside an opened container, most likely, and the Work area's
**Closed** hand-off is exactly that case. When it is:

- **Plain text only.** No pill, no box, no background, no underline, no chevron.
- **The current one differs by colour** (and weight, at most). Nothing else changes.
- Set out like a header row, spaced, reading as words rather than controls:

```
  Name            Age            Sex
  ^ current, in ink; the others faint
```

This replaces the filled `Pills` treatment wherever a *tab* is meant. `Pills` stays what it is — a
filter on a different axis from the sidebar — and is not to be used as a tab row.

## The two rules the names have to keep

1. **A tab is a question someone asks, not a module.** If what is inside cannot be said without
   listing features, the name is wrong.
2. **The same noun means the same thing at every level.** Only the scope changes — Work is Work
   whether you are Super User or Admin; one sees three departments, the other sees one. The rail then
   only has to be learned once.

## The Overview's cells are the front doors

`K01` already names its four cells **Authority · Rollout · Today · Out of place**. Three of them are
area names, so the Overview is the front door to the rail rather than a separate vocabulary: opening
a cell goes deeper into the area that owns it. ("Today" and "Out of place" both open into **Record**.)

**Must see holds nothing of its own** — with two exceptions that are mirrors, not homes: the
unaddressed reports, which live in Record, and a held session's container, which lives on the page it
was started from. Everything else on Must see lives in an area. If something can only be reached from
Must see, that is a bug in the areas.

## Where every handler lands

| Area | Handlers |
|---|---|
| **Must see** | none of its own — it reads from the others. It *surfaces* `reports.list` (unaddressed) and the held session. |
| **Authority** | `hierarchy.tree`, `hierarchy.departments`, `hierarchy.department_create`, `hierarchy.account_create`, `hierarchy.account_get`, `hierarchy.account_offboard`, `hierarchy.pc_register`, `hierarchy.pc_rekey`, `hierarchy.set_display_name`, `hierarchy.set_self_name`, `hierarchy.resolve_names`, `hierarchy.traverse`, `hierarchy.end_session`, `hierarchy.extend_session`, **`reports.routing_get`, `reports.routing_set`** |
| **Rollout** | `updates.current`, `updates.approve`, `updates.rollout_health`, `updates.rollout_department`, `updates.prompt_admin`, `updates.report_status` |
| **Record** | `audit.recent`, `audit.deviations`, `hierarchy.sessions_today`, **`reports.list`, `reports.mark`, `reports.addressed_view`**, `resource.violations`, plus the closed half of Work (verified tasks, finished flows, finished assistance) |
| **Work** | `task.*` (create, get, list, propose, stack, start, verify, program_signal), `flow.*` (create, edit, list, status, history, pause, resume, trigger, consent, content, sync_result, delete), and **read-only**: `assistance.ping_status`, `assistance.channels`, `assistance.listeners`, `assisted_access.status`, `assisted_access.available_helpers` |
| **no tab — level 3, or another client entirely** | `control.*` — Automation and Actions are reachable only by entering an Admin · **`resource.tag`, `resource.resolve`** — tiering is an Admin act · **`assistance.ping`, `respond`, `search`, `message`, `close_channel`, `set_available`** and **`assisted_access.request`, `accept`, `decline`, `close`** — a Super User watches assistance, never starts it |
| **not a tab at all** | `index.*` internal · `auth.*`, `system.*` transport · `hierarchy.session_state`, `hierarchy.claim_native` are chrome · `alerts.*` feeds indicators |

## The overlap rule: open lives in its area, closed lives in Record

Several things are legitimately both: a task is work until it is verified, then it is history; a
report waits on someone, then it is addressed; an assisted session is live, then it is a record of
who helped whom.

**The rule:** *the open thing lives in its area, the closed thing lives in Record.* Work holds what is
still moving; Record holds what has stopped. That gives Record a single definition — everything
finished, plus everything the past says about now.

**And the hand-off that makes it survivable:** Work carries one **Closed** filter that hands off to
Record, so a task verified yesterday is reachable from the place its owner will look for it. Which
gives the rule that keeps the five honest:

> **A thing appears in two areas only if one of them is Must see, or a filter that names the other.**

## Indicators — which area lights up

The rail carries indicator badges today (`falcon.indicators`). Each kind needs exactly one home,
otherwise a badge sends you to the wrong place:

| Indicator kind | Area |
|---|---|
| `unaddressed_ping` | Work |
| `deadline_reached` | Work |
| `flow_failure` | Work |
| `task_completed` | Work |
| `violation` | Record |
| rollout stalled | Rollout |
| unaddressed report | **Must see** — that is where the unaddressed ones are surfaced and answered; Record carries no badge |
| session blocked / ended | chrome, no badge |

---

# The nine, settled

Settled 25 Sep 2026. Four were the user's call; the other five went to the recommendation that was
already argued here, and the two answers agreed. Recorded so the reasoning is not rediscovered — not so
the options can be reopened.

### 1. Reports are in two places at once — **all reports → Record; Must see carries the unaddressed ones**
*The user's call.* A report is a *record that sometimes needs an answer*, not work moving through the
organisation the way a task or a flow is. Must see already exists to surface the ones that need
answering, so it does that job instead of Work, and a sixth area is avoided. Rejected: splitting
unaddressed into Work (blurs what Work means), and Reports as its own sixth area (undoes the point of
five).

### 2. The open/closed rule splits lists people think of as one — **a Closed filter in Work that hands off to Record**
One filter, one hand-off, and the item is reachable from both places. This is also the first real use of
the plain-text tab treatment above. The general rule it produced is stated under *The overlap rule*: a
thing appears in two areas only if one of them is Must see, or a filter that names the other.

### 3. "Out of place" is current, not history — **Record stretches, and keeps its name**
Record means *what the rules say about us, past and present*. "Out of place" already has its front door
on the Overview, and the words people use for it are "what is out of place", not "what is happening".
Rejected: moving violations to Authority, and renaming Record to Oversight / The trail / Standing.

### 4. Report routing is a policy act, not a record — **routing lives in Authority**
`reports.routing_set` decides who receives which category of report; that is deciding who answers for
what, which is Authority's whole definition. Record is where you see what they did about it. Note the
spec still lists the routing-configuration **UI** as explicitly deferred (§10) — this settles *where* it
goes, not that it is being built now.

### 5. Resource tiers have no home — **tiering is Admin-only, so it is level 3**
*The user's call.* `resource.tag` and `resource.resolve` are not on a Super User surface at all; a Super
User sees only `resource.violations`, in Record. Nothing to design for this now — it arrives when level 3
is opened.

### 6. Assistance folded into Work loses its two halves — **a Super User watches assistance, never starts it**
*The user's call.* Live pings and open channels appear in Work **read-only**; finished assistance is in
Record by the open/closed rule; and the cross-department *picture* of assistance (the `C06` chart) is
drawn **once**, on the Overview, not copied into a third place. The acting handlers — ping, respond,
message, close, search, availability, and the whole of `assisted_access.*` — belong to the Admin and
worker surfaces.

### 7. "Must see" as a rail entry when it is also the page title — **one name, the rail's**
The rail entry says **Must see**; the page header drops to just the time. One name for one place.

### 8. The Admin rail — **deferred to level 3, deliberately**
Rule 2 says the nouns carry, but an Admin has no Authority in the Super User sense and has two areas the
Super User does not (`control.*`). The sketch stands as a sketch, to be decided when level 3 is opened:
**Must see · Department · Work · Control · Record** — five again, same shape, and only "Department" and
"Control" differ. Nothing is built from it yet.

### 9. The department level's own four — **Who governs · Its machines · Today · Waiting on you**
*The user's call.* And they are **cells, not tabs**: the department is one page of four cells, the rail
stays the Super User's five (you are deeper inside **Authority**, not somewhere else), and the crumb and
title say how deep. The widths do the ranking and **Today is the wide cell** — a department at rest is
read by its day. These are the names `DP01`–`DP04` explored, so the mood-board picks and the names
settle together. Rejected: *The people / The fleet / The day / The queue* — it reads as an inventory
rather than as the questions the rail is named after.

---

## What this costs in code, when it is time

- `IconRail.qml` — `superNav` becomes five entries with new `key`s (`mustsee`, `authority`, `rollout`,
  `record`, `work`); `adminNav` waits for issue 8 and level 3.
- `main.qml` — routes on `shell.viewKey`; every `shell.show("…")` call site changes with the keys.
- `OverviewView.qml` — the header loses the words "Must see" and keeps the time (issue 7).
- `tests/test_operator_gui.py` — finds views by `objectName`; renaming views touches it.
- The views themselves: `TasksView` + `FlowsView` + the read-only half of `AssistanceView` become one
  **Work** surface, which is a merge, not a rename, plus its one **Closed** filter. `ReportsView`
  splits: the report pane into Record, routing into Authority.
- Nothing in the Engine changes. Areas are a UI grouping; handlers keep their `<area>.<op>` names.
