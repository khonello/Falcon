# The component build list

Ant Design 6's inventory, in antd's own groups, with what each is for **in Falcon** and when we build
it. `docs/UI.md` is why; this is what.

Every row here is drawn live in the **Console Kit** page (real antd 6, Falcon's content) so it can be
judged before it is built.

**Priority**

- **P0** — the demo path cannot happen without it (shell, Record, Machines, Tasks, one form, one confirm)
- **P1** — needed before the console is complete
- **P2** — worth having, not before a sale
- **skip** — no use here; listed so nobody wonders whether it was forgotten

Every one of these is a QML component in `operator_client/gui/qml/`, styled from `Theme.qml`'s tokens.
Qt Quick Controls gives us a starting point for a few (`Button`, `TextField`, `CheckBox`, `ComboBox`,
`Menu`, `Popup`, `TabBar`); the rest are ours. Nothing is a stock control left unstyled.

---

## General

| antd | In Falcon | Priority |
|---|---|---|
| **Icon** | one stroke set, 14/16/20px — we keep the existing `Icons.qml` path data, restyled | **P0** |
| Divider | between form sections and drawer blocks | P1 |
| FloatButton | — | skip |

## Layout

| antd | In Falcon | Priority |
|---|---|---|
| Flex | thin wrapper over the same idea | P1 |

## Navigation

| antd | In Falcon | Priority |
|---|---|---|
| **Steps** | the 3-step automation wizard (When → Where → Do); flow creation | **P1** |
| Anchor | — | skip |

## Data entry

| antd | In Falcon | Priority |
|---|---|---|
| **Select** (single, multiple, search) | department, assignee, action, program, version — *nothing typed that can be picked* | **P0** |
| Mentions · Rate · ColorPicker | — | skip |

## Data display

| antd | In Falcon | Priority |
|---|---|---|
| **Tag** | status everywhere: `on 1.4.2`, `behind`, `offline`, `waiting`, `you are inside`. Colour from the status tokens, word always present | **P0** |
| **Empty** | what would be here, and the one way to make one | **P0** |
| **Card** | grouping on Overview and inside detail pages | **P0** |
| **Segmented** | small view switches inside a page (Table / Grid for a fleet) | **P2** |
| Calendar · Carousel · Image · QRCode · Tour · Watermark | — | skip |

## Feedback

| antd | In Falcon | Priority |
|---|---|---|
| **Modal** (+ `Modal.confirm`) | create/edit forms; every act with a cost, naming the cost before the verb | **P0** |
| **message** | the result of something you did ("Session ended", "Flow retired") | **P0** |
| **Drawer** | detail from a table row; long forms | **P0** |
| **notification** | something that arrived on its own: a ping, a report, being blocked | **P1** |

## Other

| antd | In Falcon | Priority |
|---|---|---|
| Affix | sticky table header — part of Table here | P2 |

---

## Falcon's own

antd has no vocabulary for these; they are built in the same language, from the components beside them.

| Component | What it draws | Built from | Priority |
|---|---|---|---|
| **FlowGraph** | source → transforms → destinations, and the branch that broke | Shapes in the flow's page | **P1** |

---

## Second wave — the whole inventory (30 Sep 2026)

The first wave built what the pages needed and stopped there, which left the kit a subset of the board.
Everything above now exists in `operator_client/gui/qml/`:

| Group | Added in the second wave |
|---|---|
| General | `Divider`, `Avatar`, `Count` (Badge), `Spin` |
| Navigation | `RowMenu` (Dropdown), `Tabs`, `Steps`, Pagination's page-size changer |
| Data entry | `Check`, `Radio`, `Toggle` (Switch), `Num` (InputNumber), `TimeField`, `TreeSelect`, `Suggest` (AutoComplete), `Transfer`, `Level` (Slider), `Upload`, `Secret` (Password), `Search` |
| Data display | `Tree`, `Collapse`, `Feed` (List), `Trail` (Timeline), `Statistic`, `Progress`, `Tip` (Tooltip), `Popover`, row selection in `Table` |
| Feedback | `Popconfirm`, `Result`, notification (`Msg.news` / `Msg.urgent`, drawn by `Toast`) |

Two judgements worth recording:

- **Cascader is folded into `TreeSelect`.** A cascade is a tree drawn sideways, and the tree is the
  shape people already know from the sider. One control, not two that do the same job.
- **`Slider` is `Level`**, because the useful thing is not the slider — it is the band of ordinary
  readings drawn behind the handle. "Above 85%" means nothing until you can see these machines sit at
  20–45 all day.

**The board, in itself.** `KitView.qml` draws the entire kit out of the real components, with Falcon's
content, in the same sections as the published Console Kit — so what is judged is what ships:

```powershell
environ-operator\Scripts\python.exe scripts\preview.py --view kit
```

It is not an area of the console; the shell lets that one view through and the sider never offers it.
One test loads it, which is the cheapest check that no component in the kit is broken.

### Third wave — the pages adopt it (30 Sep 2026)

| Page | What it took |
|---|---|
| Machines | a `Search`, row selection with a **bulk bar** over the heading, a `RowMenu` per row (Enter · Run an action · Rekey), and `BulkRun` — one action across the chosen machines, one call each, because that is how the Engine takes them |
| People | an `Avatar` in the name column, a `RowMenu` (Open · Offboard) |
| Automation | the enabled switch is a `Toggle` **in the row**, where the thing being switched is; `RowMenu` for the rest. *To become a `Check` (UI.md rule 35)* |
| Flows | `RowMenu`: Open · Pause/Resume · Retire, without opening the drawer |
| Actions | `RowMenu`: Open · Run it now |
| Tasks | the drawer is `Tabs` — Checks (with a count of what has not passed) and History, drawn as a `Trail` |
| New task | `Steps` (Say it → Read what came back) and a `Radio` where a Select hid the second choice |
| New rule | `Steps` (When → Where → Do), a `TimeField` instead of a typed "18:30", a `Num` for the interval, and a `Transfer` for the machines — which are watched matters as much as which are not |
| Reports | the pane switch is a `Segmented`: the same reports seen two ways |
| Rollout | a `Progress` per department, because the gate is held department by department |
| Settings | not connected is a `Result` that takes the page, not a note at the top of it |
| Departments | a `Segmented`: the table, or the hierarchy as a `Tree` |
| Record | the search box is a `Search` and empties itself |
| The sider | counts what needs a person, per area — from Overview's own list, so the two can never drift |

The table itself grew the column kinds these needed: `menu`, `toggle`, `avatar`, `tip`, plus row
selection and the bulk bar that replaces the heading while a set is chosen.

### Fourth wave — from the console concept (1 Oct 2026)

The concept (then `design/console-concepts.html`, removed 3 Nov 2026; UI.md rules 26–38) needs these. None of them is built in
QML yet. The priorities are a proposal, ordered by how much of the concept depends on each one.

| Component | What it does | Used by | Built from | Priority |
|---|---|---|---|---|
| **TimeChart** | a time series with real axes, a crosshair tooltip, events marked as diamonds, a threshold line, a shaded dwell band; follows the page's 1h / 6h / 24h / 7d range | machine page, rule page, CPU condition | Shapes | **P0** |
| **EventHistogram** | events per interval, stacked by kind, drag across it to narrow the table below | Overview, Audit log | Shapes + mouse area | **P1** |
| **SmartText** | a description box that underlines people, files, dates and programs as they are typed, with a picker on click or pause and `@` for people | New task | Qt's `QSyntaxHighlighter` on a `TextArea`, a `Popup` for the picker | **P1** |

Changes to what exists:
- **Tables:** short lists inside panels become rows (UI.md rule 37).
- **Machines:** loses four columns (rule 30).
- **ScriptPanel:** its check runs as the script is typed, as `falcon.validateScript` already does
  when it is sent.
- **Actions:** the action library becomes the only list the rule builder's *Do* step offers.

---

## Order of work

1. ~~**Tokens + shell** — `Theme.qml`, `Layout`, `Menu`, `Breadcrumb`, `Button`, `Typography`, `Icon`.~~ *done*
2. ~~**Table, and the Record page** — with sort, filters, a `RangePicker` and `Empty`. This is the proof
   that the idiom works; nothing else starts until it looks like software a company buys.~~ *done*
3. ~~**Machines and Departments** — Table + Drawer + `Descriptions` + `Tag` + `MachineCell`.~~ *done*
4. ~~**One form end to end** — register a machine: `Modal` + `Form` + `Select` + validation + `message`.~~
   *done — and it grew a `Toast`, an `Alert`, and rule 13: a key shown once keeps the modal open.*
5. **Tasks, Flows, Automation, Actions** — each a table, a detail, and its wizard.
   *Tasks done — the proposal step is the rule made visible: `task.propose` fills a second page of
   the same modal, and `task.create` only fires from there. Not yet built: editing a proposed item
   by hand (the linked `used_with_file` index makes removal unsafe), so the assigner's choices are
   keep the stack, drop a deadline, or say nothing is checked.*
   *Flows done — table, drawer, pause/resume/retire, and a create form that is source + destinations
   and nothing else. No stage editor: the JSON shapes of a Flow stage's `config` are on the deferred
   list (spec §10), so branch/transform/categorize wait for that decision, not for the UI.*
   *Automation and Actions done — the library with its Run, and rules that read as one sentence.
   A built-in's parameters come from the Engine's own catalogue, so the form cannot offer a field
   it does not want. A Custom Action is checked by `falcon.validateScript` before it is sent, which
   is the same check the Engine and then the worker run again. No condition builder beyond what the
   Engine requires (a time event needs a time): `condition_spec`'s shape is deferred too.*
6. **The rest**: Assistance, Resources, Reports, Rollout, Overview, Settings.
   *Assistance, Resources, Reports and Rollout done. Overview, People and Settings are what is
   left. Not built: `reports.routing_set` (deferred), tagging a file by hand (`resource.tag`),
   `assistance.search` and `assistance.add_listener` from the UI — the drawer says Listeners
   exist and how they work, but adding one still goes through the TUI.*
   *Overview, People and Settings done — all fourteen pages exist. Overview is a list of acts, not
   a dashboard. People provisions the account and its PC together and shows the key once (rule 13).
   Settings holds only what a person can actually change: the connection, and the name those below
   them see.*
7. ~~**The custom four**: DayTimeline, FleetGrid, FlowGraph, ScriptPanel.~~ *done, plus the two P0s
   that had been missed: `Segmented` and `SessionBanner`. Machines carries one switch — List · Grid ·
   Day — because all three are the same fleet seen differently. The flow graph lives in the flow's
   drawer. `ScriptPanel` is one component used twice: read-only in the Actions drawer, editable in
   the form, with the same check under it.*

The Worker Client's five windows are on the same palette: `worker_client/windows/qml/Window.qml`
writes the tokens out rather than importing them, because that package does not depend on the
Operator Client. If a token changes here it has to be changed there too — there are eleven of them,
in one block at the top of that file.

Tests come back with step 2: `tests/test_operator_gui.py` was deleted with the old views, and the new
one is written against the new components as they land.
