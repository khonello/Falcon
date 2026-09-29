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
| **Button** | primary (one per page header), default, text, link, danger; `small`/`middle`; loading state while a call is in flight | **P0** |
| **Icon** | one stroke set, 14/16/20px — we keep the existing `Icons.qml` path data, restyled | **P0** |
| **Typography** | `Title` (page, section), `Text` (default, secondary, disabled, danger), `Paragraph`, `Link`, `code` for hostnames and versions | **P0** |
| Divider | between form sections and drawer blocks | P1 |
| FloatButton | — | skip |

## Layout

| antd | In Falcon | Priority |
|---|---|---|
| **Layout** (`Sider`, `Header`, `Content`) | the shell: 240px collapsible sider, 56px header, content | **P0** |
| **Grid** (row/col, 24 columns, gutters) | page composition: form columns, card rows | **P0** |
| **Space** | consistent gaps between buttons, tags, controls | **P0** |
| Flex | thin wrapper over the same idea | P1 |

## Navigation

| antd | In Falcon | Priority |
|---|---|---|
| **Menu** (inline, collapsible) | the sider: one entry per area, badge for what needs a person | **P0** |
| **Breadcrumb** | Falcon › Departments › Operations › R. Mensah — the only depth indicator | **P0** |
| **Pagination** | every table; page size 20/50/100 | **P0** |
| **Dropdown** | row actions ("…"), the account menu, bulk actions | **P0** |
| **Tabs** | inside a detail page: a task's Checks · Files · History | **P1** |
| **Steps** | the 3-step automation wizard (When → Where → Do); flow creation | **P1** |
| Anchor | — | skip |

## Data entry

| antd | In Falcon | Priority |
|---|---|---|
| **Form** | label above or left, required mark, inline validation, submit/cancel footer — one component every form uses | **P0** |
| **Input** (+ `TextArea`, `Search`, `Password`) | names, descriptions, the table search box, the client key | **P0** |
| **Select** (single, multiple, search) | department, assignee, action, program, version — *nothing typed that can be picked* | **P0** |
| **Checkbox** (+ group) | table row selection, permission lists, "don't warn me" | **P0** |
| **Radio** (+ `Radio.Button` group) | mutually exclusive choices: tier, verification mode, severity | **P1** |
| **DatePicker** + **RangePicker** | the Record's date range, task deadlines, schedules. **Qt has none — this is real work and it is P0 for Record** | **P0** |
| **TimePicker** | an automation's time of day | **P1** |
| **Switch** | enable/disable an automation, availability to help | **P1** |
| **InputNumber** | timeouts, thresholds, retention days | **P1** |
| **TreeSelect** | picking a folder from the file index; picking a machine within a department | **P1** |
| **Transfer** | choosing listeners, choosing machines an automation targets | **P2** |
| **Cascader** | department → machine in one control, where a tree is too heavy | **P2** |
| **AutoComplete** | file search, hostname search | **P2** |
| **Upload** | a custom action's script file (today it is dropped onto a panel) | **P2** |
| **Slider** | a threshold ("processor above 85%") shown against what is normal | **P2** |
| Mentions · Rate · ColorPicker | — | skip |

## Data display

| antd | In Falcon | Priority |
|---|---|---|
| **Table** | the backbone. Column sort, column filters, row selection, expandable rows, fixed header, pagination, loading, `Empty`. Record · Machines · Tasks · Flows · Reports · Actions · Resources all use it | **P0** |
| **Tag** | status everywhere: `on 1.4.2`, `behind`, `offline`, `waiting`, `you are inside`. Colour from the status tokens, word always present | **P0** |
| **Descriptions** | label/value blocks in every drawer: a machine, a person, a task | **P0** |
| **Empty** | what would be here, and the one way to make one | **P0** |
| **Card** | grouping on Overview and inside detail pages | **P0** |
| **Badge** | counts on menu entries, a dot on a machine that needs someone | **P0** |
| **Statistic** | the Overview's figures: machines, behind, open sessions, unaddressed reports | **P1** |
| **Avatar** | people, in tables and drawers; initials, no photographs | **P1** |
| **Tooltip** | a truncated cell's full value; why a control is disabled | **P1** |
| **List** | the assistance conversation, a channel's messages — the one place a table is wrong | **P1** |
| **Timeline** | a report's history, a task's events, an audit trail for one subject | **P1** |
| **Tree** | the hierarchy where it is a list rather than a picture | **P1** |
| **Collapse** | long forms (an action's advanced settings) | **P2** |
| **Segmented** | small view switches inside a page (Table / Grid for a fleet) | **P2** |
| **Popover** | a machine's summary on hover in a dense view | **P2** |
| Calendar · Carousel · Image · QRCode · Tour · Watermark | — | skip |

## Feedback

| antd | In Falcon | Priority |
|---|---|---|
| **Modal** (+ `Modal.confirm`) | create/edit forms; every act with a cost, naming the cost before the verb | **P0** |
| **message** | the result of something you did ("Session ended", "Flow retired") | **P0** |
| **Skeleton** | while a page's first reply is outstanding | **P0** |
| **Drawer** | detail from a table row; long forms | **P0** |
| **Alert** | the session banner, a lost connection, a department with no Admin | **P0** |
| **Popconfirm** | small destructive acts inline in a row | **P1** |
| **notification** | something that arrived on its own: a ping, a report, being blocked | **P1** |
| **Spin** | inside a button and a small pane; never over a whole page | **P1** |
| **Result** | connection failed, permission refused, nothing found — with the way forward | **P1** |
| **Progress** | rollout progress per department; a long action | **P1** |

## Other

| antd | In Falcon | Priority |
|---|---|---|
| **ConfigProvider** equivalent | `Theme.qml`: tokens, density, and later a dark swap, in one place | **P0** |
| Affix | sticky table header — part of Table here | P2 |

---

## Falcon's own

antd has no vocabulary for these; they are built in the same language, from the components beside them.

| Component | What it draws | Built from | Priority |
|---|---|---|---|
| **MachineCell** | a machine inside a table row: hostname, `Badge` for state, reason | Badge + Text | **P0** |
| **SessionBanner** | you are inside someone's machine, the clock, the way out | Alert + Progress | **P0** |
| **DayTimeline** | who held each machine and when, an hour axis, a legend | Canvas/Shapes in a Card | **P1** |
| **FleetGrid** | a department's machines compactly when the table is too slow to scan | Segmented switch beside the Table | **P1** |
| **FlowGraph** | source → transforms → destinations, and the branch that broke | Shapes in the flow's page | **P1** |
| **ScriptPanel** | a custom action's file, its validation result, its output | Upload + Typography `code` | **P2** |

---

## Order of work

1. ~~**Tokens + shell** — `Theme.qml`, `Layout`, `Menu`, `Breadcrumb`, `Button`, `Typography`, `Icon`.~~ *done*
2. ~~**Table, and the Record page** — with sort, filters, a `RangePicker` and `Empty`. This is the proof
   that the idiom works; nothing else starts until it looks like software a company buys.~~ *done*
3. ~~**Machines and Departments** — Table + Drawer + `Descriptions` + `Tag` + `MachineCell`.~~ *done*
4. ~~**One form end to end** — register a machine: `Modal` + `Form` + `Select` + validation + `message`.~~
   *done — and it grew a `Toast`, an `Alert`, and rule 13: a key shown once keeps the modal open.*
5. **Tasks, Flows, Automation, Actions** — each a table, a detail, and its wizard.
6. **The rest**: Assistance, Resources, Reports, Rollout, Overview, Settings.
7. **The custom four**: DayTimeline, FleetGrid, FlowGraph, ScriptPanel.

Tests come back with step 2: `tests/test_operator_gui.py` was deleted with the old views, and the new
one is written against the new components as they land.
