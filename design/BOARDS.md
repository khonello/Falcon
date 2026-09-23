# What every board is

The canvas grew past the point where a board's name told you what it was for. This is the map; the
`INDEX` board on the canvas says the same thing visually.

**Everything here is Super User only, on purpose.** What carries over to Admin is decided afterwards.

| Prefix | What it is |
|---|---|
| `D01`–`D04` | **Pages.** The screens as they are built today, in QML. |
| `C01`–`C10` | **Charts.** One chart type per board, four ways to draw it. Pick one per slot. |
| `L01`–`L06` | **Layouts.** Ways of arranging a page's slots. Pick one per page. |
| `X01`–`X02` | **Behaviour.** How a slot is chosen, and what happens when a chart is clicked. |
| `M01`–`M15` | The component mood board (buttons, rows, cards…) — already picked from. |
| `S01`–`S04` | The Super User mood board — already picked from. |
| everything else | The Admin screens, the worker surfaces, the language, the dialogs. |

A **page** is a screen. A **slot** is one panel on it. A C-board holds that slot's alternatives.

## Page 1 — At a glance (`D01`)

The system's condition, in figures and the charts behind them.

| Slot | What it shows | Alternatives |
|---|---|---|
| The figures | four numbers, nothing drawn | `C10` |
| Rollout | one version across the departments | `C01` |
| The fleet | one mark per client PC | `C02` |
| Confirmations | the rollout landing, over the week | `C03` |
| Work, by department | tasks and flows, the same two measures | `C09` |

## Page 2 — The hierarchy (`D02`, and `D04` descended)

Who governs what, and what crosses between them.

| Slot | What it shows | Alternatives |
|---|---|---|
| The hierarchy | department → Admin → PC | `C04` |
| Assistance | who helped whom, across departments | `C06` |
| Report routing | where each category of report goes | `C07` |
| *…descended into one department:* | | |
| Its Admins | a list, not a chart | — |
| Sessions here | the same timeline, scoped | `C05` |
| In numbers | its rollout and its work | `C01` + `C09` |

## Page 3 — The record (`D03`)

What actually happened today.

| Slot | What it shows | Alternatives |
|---|---|---|
| Sessions today | who held each PC, and for how long | `C05` |
| Violations by tier | files where their tier does not allow them | `C08` |
| Deviations | a list, not a chart | — |

## Layouts, and what each is for

| Board | Structure | Suits |
|---|---|---|
| `L01` | three — a band of figures over two charts | page 1: the figures are read first |
| `L02` | three — one subject, two supporting | page 2: the map is the subject |
| `L03` | four, even | a survey; no one page in particular |
| `L04` | four, weighted around a lead story | page 3: the timeline is the lead |
| `L05` | five — band, two wide, two narrow | page 1 when it carries more |
| `L06` | five, asymmetric — a triage column | page 1 when triage comes first |

## Behaviour

| Board | What it settles |
|---|---|
| `X01` | A slot can be drawn several ways. The control lives in the slot's own header, and the choice is remembered per slot. One choice, set once — not a button met on every panel every day. |
| `X02` | The pages are visual and nearly wordless. Clicking a chart (or one mark in it) settles the chart to one side and brings text beside it: one sentence, then facts one line each, then at most one action. The chart never leaves the screen — the text is an extension of it. |

## The test a chart has to pass

*What question does this panel answer, and does the shape answer it faster than a sentence would?*

Three treatments were cut for failing it: a chord diagram for assistance, an orbit diagram for report
routing, and an occupancy band for sessions. Each was legible only once someone explained its geometry,
which is one explanation too many. The expressive versions that survived (`C06-D` arcs, `C07-D` sankey)
are kept as alternatives, not as defaults.
