# The Operator Client UI — what we are building

Decided 29 Sep 2026. This replaces the bespoke design that ran from 24–28 Sep; that design and the
material defending it are deleted (recoverable at commit `a91cca4`).

**The premise: familiar beats distinctive.** The buyer is a company whose IT people have used fifty
admin consoles. Falcon should look like the fifty-first — light, flat, dense, blue accent, tables and
forms — so that nobody has to be taught it and nobody wonders whether it is real software. The previous
design was visually careful and commercially wrong: it read as a dashboard someone made rather than a
tool a company runs on.

**The idiom is Ant Design 6** (6.6.5 is current as of 29 Sep 2026). We are not shipping React, so we
are not using antd's code — the client stays PySide6 + QML over `FalconBridge`. We take antd's **design
language** (its tokens, its component inventory, its interaction conventions) and build those components
in QML. `docs/UI-COMPONENTS.md` is the build list.

**The kit is drawn before it is built.** Every component below exists as a live page rendered with real
antd 6 and Falcon's own content, so it can be approved or changed before a line of QML is written. Ask
for the Console Kit link; regenerate it from the same source if it is ever lost.

---

## Tokens

Ant Design 6's defaults are the starting values. They are not sacred, but nothing changes without a
reason, and they change in one file (`Theme.qml`).

| | Value | Where |
|---|---|---|
| Primary | `#1677ff` — Ant blue, chosen 29 Sep 2026 | **interaction only**: primary buttons, links, the selected menu entry, focus rings. Never status |
| Will need someone | `#ad6800` | a version behind, waiting for a yes. Rare |
| Needs someone now | `#cf1322` | a file out of place, an update past the limit, a machine you are holding. Rarer |
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

### Colour is tonal, and hue is rationed

The rule the whole console follows, decided 29 Sep 2026 after looking at the kit: **tone carries
information, hue carries urgency.** Five hues in one table column is noise; the eye should be pulled
only where somebody has to act.

| Tone | Means | Drawn as |
|---|---|---|
| `rgba(0,0,0,0.25)` | quiet — free, unused, nothing recorded | a hollow dot, a faint outline |
| `rgba(0,0,0,0.45)` | present — at the PC, running, syncing. **Most of the screen** | a filled dot, secondary text |
| `rgba(0,0,0,0.88)` | the subject — the row you picked, the machine you are on | ink, medium weight |
| `#ad6800` | will need someone | a dot and its word, both in the tone |
| `#cf1322` | needs someone now | the same, and nothing else on screen competes |

**The two hues are matched in weight, not just in meaning.** A lighter colour at the same size reads as
a heavier mark — the same 92 × 5 px progress bar looked fatter in amber than in red until the amber was
deepened from `#d48806` to `#ad6800`. That also takes it from about 3:1 to 4.6:1 on white, which is the
contrast floor anyway. Any new tone is checked the same way: measured, not eyeballed.

Ant Design ships six status hues (blue, green, orange, red, purple, cyan) and uses them freely. **We use
two**, plus three weights of ink, plus the accent for things you can click. Green is not used at all: a
machine that is fine is quiet, not green. **A screen where nothing is wrong is entirely grey.**

**The ordinary case is grey, but never invisible.** On the day timeline a block for someone at their own
machine is `#bfbfbf` on a `#fafafa` lane — the ladder's own quiet tone, a clear step above the track it
sits in. Recessive is not the same as faint: if the normal case cannot be seen, the chart stops showing
how much of the day was normal.

**The day is 24 hours by default, and out of hours is shaded rather than hidden.** The user, 29 Sep 2026:
*"sneaky things happen at unusual times."* So the timeline opens on the whole day, with the hours outside
06:00–18:00 under a light grey band — an Admin entering a machine at 02:14 is exactly what this product
exists to show, and it is never cropped out of the first view anyone sees. **6 to 6** narrows it to the
working day when that is all you are looking at. The report calls an out-of-hours entry out in words.

**Every drawing carries a Report toggle.** A chart shows the shape of something at a glance; it is
slower to *act* on. So any drawing that takes a moment to decode has a `Segmented` switch above it —
**Chart · Report** — and the report is the same data as sentences in a small table: who, which machine,
when, for how long, and what it means. The chart is never the only way to read something. (The user,
29 Sep 2026: *"it the only piece that is nice but can take awhile to make sense of"*.)

**The one exception: a chart whose job is telling kinds apart.** The day timeline distinguishes four
things — at their own machine, an Admin entered, you entered, assisted by consent — and three greys
cannot do that at a glance. So it uses grey for the ordinary case (most of the chart) and a hue per kind
of entry, each named in its legend. Nothing else on a page may do this; if a second chart needs it, it
needs a reason of the same weight.

**Cards are filled, not outlined** — an empty white box on a white page is a line drawing of nothing.
Decided once, for every surface:

| | Surface | Why |
|---|---|---|
| **Filled** `#fafafa` | figures, summary cards, machine tiles, anything read rather than filled in | the fill is what makes it a thing; forty outlined tiles is a grid of empty frames |
| **Filled, tinted** | an exception — a violation, a machine that needs someone, a broken node in a graph | the tint *is* the state; no border, and never a left-edge stripe |
| **Outlined** `#fff` | a card holding a form; a conversation list | the inputs are white and would float on a fill; message rows need an edge to sit against |
| **Neither** | a drawer's label/value block, `Empty`, `Timeline`, `Tree`, `Table` | they sit on the page itself |

A card never goes inside another card — that is a `Divider`.

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

0. **Label and value read down one column**, label left and value right, with hairline dividers — never
   antd's two-column bordered grid, which makes you hunt for which value belongs to which label. Past
   about six facts, group them under plain headings.
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
7a. **An alert is one line** — an icon, what happened, and at most one act, all on that line. antd's
   description block (a paragraph under the message) is never used: what would have gone there belongs
   on the page the act opens. Three kinds only — red where somebody must act, amber where somebody will
   have to, grey for everything else. **There is no blue alert and no green one: good news is grey.**
8. **Status is a `Tag` or a `Badge`**, coloured from the status tokens, with the word always present —
   never colour alone.
9. **Nothing typed that can be picked.** Folders, machines, people, actions, programs come from
   `Select` / `TreeSelect` / `Transfer`, not from a text field. (This rule survives from the old design
   because it is about correctness, not looks.)
10. **The Engine decides; the page renders.** The UI never computes authority, never hides what the
    Engine would refuse — it asks and reports the answer.
11. **No left-edge stripes. Anywhere.** Nothing — no banner, card, row, alert or panel — carries a
    coloured bar down its left side. Once one row has one, every row wants one and the page becomes a
    barcode. State is said by a dot, a tint on the whole surface, or the words. This is a hard rule.
12. **A button is two words at most.** It names the act and stops; who it affects and what it costs are
    said beside it or in the confirm, never inside the label. *End session*, not "End their session".
    *Assign Admin*, not "Assign an Admin to Logistics". *Re-check*, not "Check them again". The same
    holds for menu entries and the confirm's own buttons.

13. **A secret is shown once, so the form does not close on success.** Registering a machine, creating
    an account and rekeying all hand back a client key the Engine will never print again. Those forms
    have a second half: the same modal turns into the answer — a `warn` alert saying it is shown once,
    the identifiers, the key in a selectable block, and *Copy key* where the submit button was. The
    `message` still fires, because the act did happen; it is the modal that waits.

14. **Anything a model proposed is a page you have to read.** Never a filled-in form you can submit
    without looking: the ask and the answer are two steps of the same modal, the second says *nothing
    is saved yet*, and the commit button is on that page only. Whatever made it uncertain — a guessed
    deadline, a name that already exists, more than one task in one sentence — is a `warn` or `danger`
    alert at the top, in the words of what it means, not the name of the flag.

15. **When the Engine has written the sentence, the console says that sentence.** A stopped flow's
    suggestion, a refused act's message, a deviation's reason: they are already written once, on the
    server, in words chosen for a person. The UI renders them. It does not paraphrase them, map them
    to its own copy, or reduce them to a status word — the word goes in the `Tag`, the sentence goes
    beside it. A refusal a person can answer (a destination that already holds files) becomes rule 4's
    confirm, carrying the Engine's own line inside the cost.

16. **A wire identifier is never shown to a person.** `lock_session`, `threshold.cpu`, `used_with_file`
    are names for the protocol. One file per area turns them into words — `Task.qml`, `Sync.qml`,
    `Doing.qml` — and every page reads from it, so a thing is called the same thing in a table, a
    drawer and a sentence. A key with no entry falls back to itself with the punctuation softened,
    which looks wrong on purpose: that is how a missing word gets noticed.

17. **A drawer or modal belongs to the page that opened it.** They live in the window's overlay, which
    the page's own visibility does not reach, so each one carries `page:` and closes when that page is
    left. Without it a detail panel sits over the next page as if it belonged there.

18. **A rule is shown as the state of a control, not as a sentence about a rule.** The turn in a
    Message Channel is whether the box can be typed into. The N+1 gate is whether *Approve next* is
    enabled. The sentence is still there underneath, for the person who wants to know why — but the
    control has already said it, and nobody has to read to find out what they may do.

19. **What a role may see decides the columns, not only the rows.** The Super User sees every report
    whatever the routing says, so they get no *addressed* column: it would always read "open" and mean
    nothing. They get the View instead, which answers a different question — who addressed what — and
    is structurally never a report.

20. **The Overview is a list of acts, not a dashboard.** No tile counting something nobody has to do
    anything about, no chart of a number that is fine. Each line is one thing a person has to act on,
    in the words of what it is, with why it matters underneath, and it opens the page where it gets
    done. Red is what cannot wait, amber is what can. When there is nothing, the page says so and
    stays quiet — good news is grey and brief.

21. **A setting that cannot change anything is not a control.** Almost everything in this system is
    decided by the Engine and merely rendered, so Settings holds only what a person can really change:
    the connection, and the name those below them see. The rest is one sentence saying where the
    decisions are made.

22. **One switch between views of the same thing.** List, Grid and Day are the same fleet seen three
    ways, so they are one `Segmented` and not three pages — and the span switch beside it (24 hours ·
    6 to 6) only appears while the Day is showing. A `Segmented` is never navigation and never a
    filter: the data does not change, only how you are looking at it.

23. **The day's one licensed colour exception.** A bar has nothing but colour to say what it is with,
    so the timeline may use three hues — at the PC, entered, assisted — and nothing else in the
    console may. It is spent there because it buys something no word could at that size. Everywhere
    else, including the fleet grid, "entered" is a word and the accent stays for interaction.

---

## What stays custom

antd has no vocabulary for these, and they are the product:

| | What it draws | Built from |
|---|---|---|
| **Day timeline** | who held each machine, and when. Two switches: **6 to 6 · 24 hours** for the span (**24 hours is the default** — the night is shaded, never cropped) and **Chart · Report** for how you read it | custom Shapes + `Table`, behind two `Segmented`s |
| **Fleet view** | a department's machines at a glance, 4 to 240 | `Table` by default; a compact grid as a second view |
| **Flow graph** | source → transforms → destinations, and where it broke | custom, in the flow's detail page. Its nodes are **filled** like every other card — the source one step darker, the broken one a tinted fill rather than a red ring, and only its link stays dashed red |
| **Hierarchy** | department → Admin → machine | antd `Tree` where it is a list; custom only if a picture earns it |
| **Session banner** | you are inside someone's machine, and for how long | one row on a red tint: whose machine, which machine, a real `Progress` bar for the clock, and the way out. No stripe down the left, no hairline on an edge, and no second treatment — this is the only one |
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
