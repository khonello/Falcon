# Areas, not features: what the rail is called at each level

Decided 24 Sep 2026. **Nothing here is built or drawn yet** — this is the working document, and the
issues at the bottom are to be settled *in here* before the mood board or any QML is touched.

## The decision

The rail stops being one tab per feature area. Features are gathered into **areas named after the
question a person is asking**. Super User goes from eight tabs to **five**, and **Assistance folds
into Work**.

| Area | Gathers | The question it answers |
|---|---|---|
| **Must see** | the Overview (`K01`, built) | what needs me right now |
| **Authority** | departments, Admins, client PCs, appointing, display names, entering | who governs what, and where nobody does |
| **Rollout** | versions, approval, escalation, fleet health | what version is where, and what is stuck |
| **Record** | audit, sessions, Views, addressed reports, deviations, violations | what happened, and who was where |
| **Work** | Tasks, Flows, **Assistance** | what is moving through the organisation |

## How an area is entered: through its contents, not through tabs

**Settled 24 Sep 2026, and it governs every area.** An area is not a page with tabs across the top. It
is a small set of **containers — a chart, a drawing, a figure — one per thing the area covers**. You
enter a subject by clicking the thing itself.

- **Clicking a container opens it in place.** It grows where it stands and reveals what is specific to
  what you clicked; the page recomposes around it rather than navigating away.
- **The containers around it become the context that explains it**, re-scoped to the opened subject —
  quietened, expanded, or re-drawn for it, never left saying something about a different subject.
- **One level only.** Inside an opened container a click selects or filters; it never opens again.
- **Back is the same gesture, or Escape**, and the area returns exactly as it was.
- **A container with nothing to explain does not open.**

This is the rule the Super User Overview already runs on (`K01` at rest, `K03`–`K06` opened, all four
built) — it is now the rule for **all five areas**, not a trick the Overview plays. The door into a
subject is the drawing of that subject.

It also answers navigation downward: the department page (level 2) is what the **Departments**
container in Authority opens into, and entering an Admin (level 3) is what a department opens into.
The levels are the same gesture repeated, not three different navigations.

**Why this over tabs:** a tab row names things you have not seen yet and makes you guess which one holds
your answer. A container has already answered the page-level question by being drawn — you click it
because you saw something in it.

## If tabs are ever used anyway

Somewhere one will be needed — a filter inside an opened container, most likely. When it is:

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
a cell goes deeper into the area that owns it. ("Today" and "Out of place" both open into **Record** —
see issue 3.)

**Must see holds nothing of its own.** Everything on it lives in an area; it is a view, not a
container. If something can only be reached from Must see, that is a bug in the areas.

## Where every handler lands

| Area | Handlers |
|---|---|
| **Must see** | none of its own — it reads from the others |
| **Authority** | `hierarchy.tree`, `hierarchy.departments`, `hierarchy.department_create`, `hierarchy.account_create`, `hierarchy.account_get`, `hierarchy.account_offboard`, `hierarchy.pc_register`, `hierarchy.pc_rekey`, `hierarchy.set_display_name`, `hierarchy.set_self_name`, `hierarchy.resolve_names`, `hierarchy.traverse`, `hierarchy.end_session`, `hierarchy.extend_session` |
| **Rollout** | `updates.current`, `updates.approve`, `updates.rollout_health`, `updates.rollout_department`, `updates.prompt_admin`, `updates.report_status` |
| **Record** | `audit.recent`, `audit.deviations`, `hierarchy.sessions_today`, `reports.list`, `reports.mark`, `reports.addressed_view`, `resource.violations` |
| **Work** | `task.*` (create, get, list, propose, stack, start, verify, program_signal), `flow.*` (create, edit, list, status, history, pause, resume, trigger, consent, content, sync_result, delete), `assistance.*` (ping, respond, ping_status, search, channel(s), message, close_channel, listeners), `assisted_access.*` (request, accept, decline, close, status, set_available, available_helpers) |
| **no tab** | `control.*` — Automation and Actions are reachable only by entering an Admin (level 3) · `index.*` internal · `auth.*`, `system.*` transport · `hierarchy.session_state`, `hierarchy.claim_native` are chrome · `alerts.*` feeds indicators |
| **unplaced — see issues** | `reports.routing_get` / `routing_set`, `resource.tag` / `resource.resolve` |

## The proposed rule for overlaps: open lives in Work, closed lives in Record

Several things are legitimately both: a task is work until it is verified, then it is history; a
report waits on someone, then it is addressed; an assisted session is live, then it is a record of
who helped whom.

**Proposal:** *the open thing lives in its area, the closed thing lives in Record.* Work holds what is
still moving; Record holds what has stopped. This also gives Record a single definition — everything
finished, plus everything the past says about now.

It has a cost, in issue 2.

## Indicators — which area lights up

The rail carries indicator badges today (`falcon.indicators`). Each kind needs exactly one home,
otherwise a badge sends you to the wrong place:

| Indicator kind | Area |
|---|---|
| `unaddressed_ping` | Work |
| `deadline_reached` | Work |
| `flow_failure` | Work |
| `task_completed` | Work |
| `violation` | Record — **see issue 3** |
| rollout stalled | Rollout |
| unaddressed report | Record — **see issue 1** |
| session blocked / ended | chrome, no badge |

---

# Open issues — settle these here, before drawing

### 1. Reports are in two places at once
`reports.list` is *waiting on someone* (unaddressed) and *what happened* (addressed). By the open/closed
rule the unaddressed ones belong in Work and the addressed ones in Record — but a report is not "work
moving through the organisation" in the way a task or a flow is, and "Reports" as a word has lived in
its own tab for the whole project.
**Options:** (a) unaddressed → Work, addressed → Record; (b) all reports → Record, and Must see carries
the unaddressed ones; (c) Reports stays its own sixth area.
**Recommendation:** (b). Reports are a *record that sometimes needs an answer*; Must see already exists
to surface the ones that do, and a sixth tab undoes the point of five.

### 2. The open/closed rule splits things people think of as one list
If a verified task leaves Work, someone who closed a task yesterday will look for it under Work and not
find it. Same for a closed flow or a finished assisted session.
**Options:** (a) Work has a "Closed" filter that hands off to Record; (b) Record is only *sessions and
audit*, and each area keeps its own history; (c) closed items stay in their area, and Record is purely
a cross-cutting trail.
**Recommendation:** (a) — one filter, one hand-off, and the item is reachable from both. Worth a rule:
*a thing appears in two areas only if one of them is Must see or a filter that names the other.*

### 3. "Out of place" is current, not history
A restricted file sitting in `/workers/` is *true now*, not a thing that happened. Putting violations in
Record makes Record mean "the past **and** some of the present", which weakens the name.
**Options:** (a) Record covers "what the rules say about us, past and present" and the name stretches;
(b) violations move to Authority (they are about policy and who answers for it); (c) rename Record to
something that carries both — **Oversight**, **The trail**, **Standing**.
**Recommendation:** (a) with the name **Record** kept, because "Out of place" already has a front door on
the Overview and the word people use for it is "what is out of place", not "what is happening".

### 4. Report routing is a policy act, not a record
`reports.routing_set` decides *who receives which category of report* — that is an authority decision,
and the spec lists the routing-configuration UI as explicitly deferred (§10).
**Options:** (a) routing lives in Authority; (b) routing lives in Record beside the reports it shapes.
**Recommendation:** (a). Authority is where you decide who answers for what; Record is where you see
what they did about it.

### 5. Resource tiers have no home
`resource.tag` and `resource.resolve` set which tier a folder belongs to — access policy, which is
authority — while `resource.violations` reports the breaches, which is Record.
**Recommendation:** split them: tiers to **Authority**, violations to **Record**. Confirm that a
Super User configures tiers at all, or whether that is an Admin-only act (it may be, in which case it
is level 3 and not our problem yet).

### 6. Assistance folded into Work loses its two halves
For a Super User, assistance is mostly *oversight* — who helped whom, across departments — which is
Record by the open/closed rule. The live half (a ping waiting, a channel open) is Work.
**Recommendation:** live assistance → Work; finished assistance → Record; and the Super User's
cross-department *picture* of assistance (the `C06` chart) lives on the Overview or in Record, not as
a third copy. **Decide whether a Super User ever initiates assistance, or only watches it.**

### 7. "Must see" as a rail entry, when it is also the page's title
The Overview's header is "Must see" and the rail entry would be too. Harmless, or a stutter.
**Options:** (a) rail says "Must see", page header drops to just the time; (b) rail says "Overview",
page keeps "Must see".
**Recommendation:** (a) — one name for one place.

### 8. The Admin rail, if nouns must mean the same everywhere
Rule 2 says the nouns carry. An Admin has no Authority in the Super User sense, and has two areas the
Super User does not (`control.*` — Automation and Actions).
**Sketch, to be decided when level 3 is opened, not now:** Must see · Department · Work · Control ·
Record. Five again, same shape, and only "Department" and "Control" differ.

### 9. The department level's own four
Proposed, not yet agreed: **Who governs · Its machines · Today · Waiting on you** — which is what
`DP01`–`DP04` explore, so the picks and these names settle together. Alternatives floated: *The people
/ The fleet / The day / The queue*.
**Open:** whether these are tabs at all, or simply the four cells of the one department page. If they
are the cells, the level has no tabs and the rail stays the Super User's five.

---

## What this costs in code, when it is time

- `IconRail.qml` — `superNav` becomes five entries with new `key`s (`mustsee`, `authority`, `rollout`,
  `record`, `work`); `adminNav` waits for issue 8.
- `main.qml` — routes on `shell.viewKey`; every `shell.show("…")` call site changes with the keys.
- `tests/test_operator_gui.py` — finds views by `objectName`; renaming views touches it.
- The views themselves: `TasksView` + `FlowsView` + `AssistanceView` become one **Work** surface, which
  is a merge, not a rename. `ReportsView` splits between Record and Authority (issue 4).
- Nothing in the Engine changes. Areas are a UI grouping; handlers keep their `<area>.<op>` names.
