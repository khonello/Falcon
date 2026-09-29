# The Operator Client UI — what we are building

Decided 29 Sep 2026. This replaces the bespoke design that ran from 24–28 Sep; that design and the
material defending it are deleted (recoverable at commit `a91cca4`).

**The premise: familiar beats distinctive.** The buyer is a company whose IT people have used fifty
admin consoles. Falcon should look like the fifty-first — light, flat, dense, blue accent, tables and
forms — so that nobody has to be taught it and nobody wonders whether it is real software. The previous
design was visually careful and commercially wrong: it read as a dashboard someone made rather than a
tool a company runs on.

**The idiom is Ant Design.** We are not shipping React, so we are not using antd's code — the client
stays PySide6 + QML over `FalconBridge`. We take antd's **design language** (its tokens, its component
inventory, its interaction conventions) and build those components in QML. `docs/UI-COMPONENTS.md` is
the build list.

---

## Tokens

Ant Design v5's defaults are the starting values. They are not sacred, but nothing changes without a
reason, and they change in one file (`Theme.qml`).

| | Value | Where |
|---|---|---|
| Primary | `#1677ff` | the one accent: primary buttons, links, selected menu item, focus ring |
| Success · Warning · Error · Info | `#52c41a` · `#faad14` · `#ff4d4f` · `#1677ff` | status only, never decoration |
| Text | `rgba(0,0,0,0.88)` primary · `0.65` secondary · `0.45` tertiary · `0.25` disabled | |
| Surfaces | `#ffffff` container · `#fafafa` layout/table header · `#f5f5f5` hover | |
| Border | `#d9d9d9` control · `#f0f0f0` split | |
| Radius | 6 (4 small, 8 large) | |
| Spacing | 4 / 8 / 12 / 16 / 24 / 32 | nothing between |
| Type | 14 base · 12 small · 16/20/24 headings · line-height 1.5714 | system UI stack |
| Control height | 32 (24 small, 40 large) | every input, button, select |
| Density | compact by default — an operator scans hundreds of rows | |
| Shadow | one level, `0 2px 8px rgba(0,0,0,0.15)`, for overlays only | never on a card at rest |

Dark mode is a later token swap, not a second design.

---

## The shell

```
┌──────────────────────────────────────────────────────────────────────┐
│ ▸ Falcon        Breadcrumb / page title        session · account · ⌄ │  header 56
├────────────┬─────────────────────────────────────────────────────────┤
│  Menu      │  Page header:  Title            [Primary action]        │
│  (sider    │  ───────────────────────────────────────────────────    │
│   240 →    │  Content: table · form · detail                         │
│   collapse │                                                         │
│   to 64)   │                                                         │
└────────────┴─────────────────────────────────────────────────────────┘
```

- **Sider** — `Menu`, one entry per area, collapsible to icons. The menu is the navigation; there is no
  second navigation anywhere.
- **Header** — `Breadcrumb` (Falcon › Departments › Operations), the connection and session state as a
  `Tag`, the account with a `Dropdown`. The window's own minimise / maximise / close stay where they
  are (the window is frameless and keeps that).
- **Page header** — the page's title on the left, its one primary action on the right (`Add machine`,
  `New task`). Secondary actions live in the table row or a `Dropdown`.
- **Content** — a table, a form, or a detail. Not a grid of panels.

---

## The pages

| Page | What it is | Shape |
|---|---|---|
| **Overview** | what needs a person right now | a row of `Statistic` cards over a table of things needing attention |
| **Departments** | every department, its Admins and machine count | table → drawer |
| **People** | Super Users, Admins, workers; who they are and what they are called | table → drawer, with the display-name form |
| **Machines** | every client PC, its state, version, who is on it | table with filters (department, status, version) |
| **Tasks** | assigned work and its verification | table → detail page (checks, files, verdict) |
| **Flows** | sync pipelines | table → detail page with the flow drawn |
| **Automation** | when → then rules | table → detail, and a 3-step wizard to create |
| **Actions** | the library, and each action's settings | table grouped by kind → form |
| **Assistance** | pings, channels, listeners, help across departments | list + conversation pane |
| **Resources** | tiers, violations, file search | table with tier filter |
| **Reports** | what was raised, to whom, and what was done | table → drawer |
| **Rollout** | versions, what is behind, the lever | table by department + progress |
| **Record** | the audit trail and sessions | the big table: sort, filter, date range, export |
| **Settings** | connection, certificate, this machine | form |

Every page is reachable from the sider. No page is reachable only by clicking a chart.

**What belongs on each page** comes from the role references — `docs/design/super-user-reference.md`, `admin-reference.md` and `client-reference.md` — which list every capability each role has, gathered from the design documents. Build a page from its role's list, not from memory.

---

## Interaction rules

Stated once, so no screen invents its own.

1. **A row opens a `Drawer`** from the right for detail. A subject with its own workspace (a task, a
   flow, an automation) opens a **page** instead, with the breadcrumb growing.
2. **The primary action is top-right** of the page header, and there is exactly one.
3. **Create and edit are a `Form`** in a `Modal` (short) or a `Drawer` (long), validating inline —
   message under the field, never a toast.
4. **Anything destructive or costly gets a confirm** that names the cost before the verb:
   *"Ending R. Mensah's session puts OPS-04 back to them. They are not warned."* `Popconfirm` for small
   things, `Modal.confirm` for real ones.
5. **Tables carry their own controls**: column sort, column filters, a search box, pagination, and an
   `Empty` state that says what would be here and how to make one.
6. **`Skeleton` while loading**, never a spinner over a blank page.
7. **`message` for the result of something you did**; `notification` for something that arrived on its
   own (a ping, a report, a session blocked).
8. **Status is a `Tag` or a `Badge`**, coloured from the status tokens, with the word always present —
   never colour alone.
9. **Nothing typed that can be picked.** Folders, machines, people, actions, programs come from
   `Select` / `TreeSelect` / `Transfer`, not from a text field. (This rule survives from the old design
   because it is about correctness, not looks.)
10. **The Engine decides; the page renders.** The UI never computes authority, never hides what the
    Engine would refuse — it asks and reports the answer.

---

## What stays custom

antd has no vocabulary for these, and they are the product:

| | What it draws | Built from |
|---|---|---|
| **Day timeline** | who held each machine, and when | custom Canvas/Shapes in a `Card` |
| **Fleet view** | a department's machines at a glance, 4 to 240 | `Table` by default; a compact grid as a second view |
| **Flow graph** | source → transforms → destinations, and where it broke | custom, in the flow's detail page |
| **Hierarchy** | department → Admin → machine | antd `Tree` where it is a list; custom only if a picture earns it |
| **Session banner** | you are inside someone's machine, and for how long | `Alert` banner with a countdown |
| **Machine cell** | a machine's state inside a table row | `Badge` + hostname + a reason |

The rule for all of them: **use the antd component unless it genuinely cannot say the thing.** A table
is the default answer.

---

## Dropped from the old design

Named so nobody reinstates them by accident: the dark gradient frame; four-cell pages; "no tables";
panels whose main content is a generated sentence; the drawn machine mark as the only way to show a PC;
the density system (figure/chart/told/reading); board-driven design.

Kept, because they were about correctness rather than looks: nothing typed that can be picked; the cost
stated before the act; the Engine decides and the page renders; a panel is never blank (now an `Empty`
state); words that come from data rather than from a designer.

---

## How this gets built

`docs/UI-COMPONENTS.md` is the checklist, in priority order. The first slice is the shell plus one real
page — **Record**, because it is the most table-shaped and the current UI's weakest point — and that
slice is the proof that the idiom works before the other thirteen pages follow.

The QML stays a thin layer over `FalconBridge`: every request is `falcon.call(type, payload, cb)`, and
typed errors come back as `(false, {code, message})`. That has not changed and does not change.
