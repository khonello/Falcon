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

**The console concept (1 Oct 2026) goes further than the kit.** *Falcon Concepts* is a whole working
console on sample data: eleven pages, live charts, and the create and resolve flows. It was reworked
with the user over a day until it read as software a company buys. Its source is
`design/console-concepts.html`; the kit's is `design/console-kit.html`. Both are complete pages that
can be republished as they are. **Where the concept and an older rule below disagree, the concept
wins.** Those rules are marked *superseded* in place, and the new ones are under *Decided 1 October
2026* at the end. What the concept shows but nobody has decided yet is listed there too, as still open.

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

**The day opens on working hours, and nothing outside them is ever hidden silently.** *Superseded 1 Oct
2026; on 29 Sep it opened on 24 hours.* The user, 1 Oct: *"make 6 to 6 default with default working
frame adjustable."* So the occupancy chart opens on 06:00–18:00. The frame is two hour pickers beside
the chart, and **24 hours** is one click away. The 29 Sep reason still holds: *"sneaky things happen at
unusual times"*. So any session outside the frame is named in a line under the chart (*1 session
outside this view: A. Quaye on LOG-02 at 02:14*), with a button to show the whole day. A non-owner
session that starts outside the frame is outlined in amber and labelled. In the 24-hour view the hours
outside the frame are shaded. The report calls an out-of-hours entry out in words.

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

**The concept (1 Oct 2026) adds two pages and changes four.**
- **Issues** (new): every open problem from every source, typed, each with its own way to resolve it
  (rule 31).
- **Sessions** (new): the occupancy chart, non-owner sessions, and entries outside working hours,
  split out of Record.
- **Tasks**: a tall table. A row opens the task's page; below it is the new-task area (rule 32).
- **Automation** and **Flows**: each creates through a step wizard on its own page, not a modal
  (rule 33).
- **Actions**: a library page with *Run once* and a custom-action editor, and the single source the
  rule builder picks from (rule 34).
- **Record**: the concept calls it *Audit log* and adds a histogram you can drag across to narrow the
  table.

Departments, People, Assistance, Resources and Settings were not drawn in the concept and stand as
they are.

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
   message under the field, never a toast. *Partly superseded 1 Oct 2026: a creation with several
   decisions in sequence (a rule, a flow) is a step wizard on its own page; see rule 33.*
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
    alert at the top, in the words of what it means, not the name of the flag. *The principle stands,
    but the form is superseded 1 Oct 2026: on the Tasks page the proposal unfolds beside the
    description rather than as the second step of a modal. Nothing is created until the person
    confirms, and every field says whether it came from a rule, the model or the person (rule 32).*

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

20. ~~**The Overview is a list of acts, not a dashboard.**~~ *Superseded 1 Oct 2026.* The concept's
    Overview was approved as it stands. It has a row of six figures, each with a trend line and its
    change in words (*10 / 11 online, LOG-02 offline since 02:31*), a fleet map, the open issues,
    event volume by kind, a live activity feed, and a department summary. What survives of the old
    rule is the discipline. Every figure states what it counts and over what period. The open issues
    are one-line rows that open where the work gets done. Colour on the fleet map is spent only where
    someone has to act (rule 29).

21. **A setting that cannot change anything is not a control.** Almost everything in this system is
    decided by the Engine and merely rendered, so Settings holds only what a person can really change:
    the connection, and the name those below them see. The rest is one sentence saying where the
    decisions are made.

22. **One switch between views of the same thing.** List, Grid and Day are the same fleet seen three
    ways, so they are one `Segmented` and not three pages — and the span switch beside it (Working
    hours · 24 hours, with the frame adjustable) only appears while the Day is showing. A `Segmented` is never navigation and never a
    filter: the data does not change, only how you are looking at it.

23. **The day's one licensed colour exception.** A bar has nothing but colour to say what it is with,
    so the timeline may use three hues — at the PC, entered, assisted — and nothing else in the
    console may. It is spent there because it buys something no word could at that size. Everywhere
    else, including the fleet grid, "entered" is a word and the accent stays for interaction.

24. **The Worker's five windows are the same design, three seconds at a time.** A worker sees a small
    white card, in the console's palette, saying one thing in plain words — never a wire term, never a
    choice they do not have. Two of the rules bite hardest here: good news is grey, so a verification
    sign that has been seen just says *changed 11:20* and a started task just says *Started*; and the
    accent is only ever on the one act they can take. The palette is written out in
    `worker_client/windows/qml/Window.qml` rather than imported, because that package does not depend
    on the Operator Client — so a token changed here has to be changed there as well.

25. **The level decides what the console is.** This is one codebase and two products.

    An **Admin** gets all fourteen areas: `hierarchy-system-design.md` puts "all features
    concentrated at this level", and calls the Admin "the source of all monitoring and control
    operations".

    A **Super User** gets eight — Overview, Departments, People, Tasks, Reports, Rollout, Record,
    Settings. Their focus is "reports, audit logs, system status, high-level summaries", and design
    principle 3 says in as many words that they *do not perform day-to-day operations*. Machines,
    Flows, Automation, Actions, Assistance and Resources are not theirs at their own level.

    They reach them by **traversing into an Admin**, and then the console *is* that Admin's console:
    the six areas appear, `viewThroughSession` goes on so the Engine re-answers reads as that Admin
    (`protocol/viewing.py`), and the red banner says **Super User in charge**. Step out and the shell
    is a governance shell again — and if they were on one of the Admin's pages, it lands back on
    Overview, because that page was never theirs.

    Two consequences worth stating: the Engine is deliberately more permissive than this (it lets a
    Super User create a flow directly), so the restraint is the console's, not the protocol's; and
    an Overview line about something only an Admin can fix still *appears* for the Super User —
    seeing it is oversight — but it stops pretending to be a link.

---

## Decided 1 October 2026, from the console concept

Each of these came from the user looking at the concept and saying what was wrong, or asking for it.
They take precedence over anything above that they contradict.

26. **It has to read as production software.** The first concept used gradients, glow, moving
    particles, rings, a pill-shaped session indicator and chat bubbles. The user: *"toyish … not
    something that a company would buy for production. The context is system monitoring."* The rework
    was approved (*"excellent work, bravo"*). It uses dense 13px type with aligned figures, hairline
    panels, real axes with units, crosshair tooltips, events marked on charts, filterable tables and
    master–detail pages. Ambition means analytical depth, never decoration.

27. **A figure nobody can explain is not shown.** A per-rule "success %" was rejected: *"what does a
    percentage bar expressing success even mean."* It mixed several actions' outcomes into one
    number. A rule shows its **last run in words** instead (*1 timed out, 1 failed, 20 succeeded*).
    Every chart says its scope in its title (*Runs per day · all rules · last 7 days · by outcome*),
    and a section whose meaning is not obvious says what it measures, as *How fast reports are dealt
    with* now does. Identifiers a person never sees elsewhere are not shown either: rules are
    referred to by name, never `R-3`, and runs have no IDs.

28. **A progress chart is one line toward a goal.** The stacked version-adoption area was *"not easy
    to understand"*. It became *Machines on 1.4.2*: one line from the approval to *9 of 11*, a dashed
    goal at 11, and the machines that make up the gap named beneath.

29. **Colour is spent only where someone has to act, and every view of a thing uses the same
    marks.** The fleet map's colours were *"a bit much … some are just playful."* There is now one
    vocabulary of five marks: grey (fine), grey with an amber dot (worth a look), red tint (high),
    solid red (critical), dashed outline (offline). Status, Version, Check-in and CPU all use it;
    CPU is put into bands (under 60 / 60–75 / 75–90 / 90 and over) rather than given a scale of its
    own. A tooltip speaks for the view it is in: on CPU it says the CPU band, and the machine's
    overall health drops to a grey line underneath.

30. **Health, not Status, and the reason sits with it.** The machines table went from eleven columns to
    seven because of *"possible eye strain"*. **Health** uses the fleet map's words: Healthy, Worth a
    look, High, Critical, Offline. The reason sits under the word, and the column header explains
    the five. The machine, its user and its department share one cell. Memory moved to the machine's
    own page.

31. **Every issue can be acted on, and its type decides how.** *"No way to address pings or any
    issue."*
    - **Types:** Restricted file, Help request, Deviation, Stuck update, Flow blocked.
    - **Resolutions:** each type supplies its own (move back / delete / allow with a reason; answer
      in a channel / enter / ask another department; and so on), and the issue's details fill them in.
    - **Situational options:** some appear only when the situation calls for them, such as *Assign
      an Admin* when the department has none, retry only once the machine is back if it is offline,
      or *tell the user* only when someone is signed in. A *why these options* line says so.
    - **Afterwards:** acting moves the issue to Waiting or Resolved, writes to its timeline, and
      resolved issues collect in *Done today*, where they can be reopened.
    - **The list:** one-line rows. The detail keeps its timeline, provenance and facts behind tabs.
      Selecting an issue is a selection, not navigation, so the page header stays.

32. **The Tasks page leads with the table; creating a task unfolds as it is needed.**
    - **The table:** tall and prominent, never short because it is sparse. A row opens the task's own
      page.
    - **The new-task area:** two panels of equal width and equal height. The user: *"two sections
      wrestle for attention"*, so two panels side by side must serve one purpose. The left takes
      the input, the right shows what will be created.
    - **Unfolding:** it starts as just the description. *Read it* unfolds *What the model read* and
      *Details* (grouped under small headings: *Who and when*, *What shows it is done*) and the
      summary beside them.
    - **Live matching while typing:**
      - **Underlines:** people, files, unambiguous dates and programs are underlined as they are
        typed. A picker opens on click, or once on a pause; `@` picks a person; files come from the
        file index, with *a new file* for checks that create one; programs come from what the
        assignee's machine has installed.
      - **Guards:** they are the reader's own. A bare day word is not a deadline, and a date inside
        a file name is never offered as one.
      - **Effect:** what is confirmed reaches the proposal as *You*, and the model is asked only
        about the rest.
    - **No checks:** *"No checks, I will verify it by hand"* is a full button beside *Add a check*.
      Choosing it is an explicit decision, so it is never a checkbox that is easy to miss.

33. **Creating a rule or a flow is a step wizard with room to breathe.**
    - **The steps:** *When → On → Do → Review* for rules; *Source → Along the way → Destinations →
      Check & create* for flows. The user: *"so each step has enough breathing room and space."* One
      step shows at a time; *Next* waits until the step is valid.
    - **Leaving:** **Cancel is at the top on every step**, and asks before discarding anything set.
    - **Rules:** *Edit* opens the wizard filled in, and *Start from* copies an existing rule.
    - **Flows:** the diagram is laid out automatically and nodes are not dragged; the only placement
      with meaning, before or after the split, is a choice in the step.
    - **A rule's page:** its setup drawn as *When → On → Do*, each action's outcomes and typical time
      against its limit, its firings with their runs, and its change history.

34. **Actions is its own page, and the one source for the rule builder.**
    - **The library:** Control, Monitoring and Custom, each with *Used by* (one rule named; several
      counted, with the names on hover) and *Run once*.
    - **Run once:** states what it will do to the people affected, skips offline machines rather
      than queueing, and shows each machine finish.
    - **Custom actions:** checked as they are typed (compiles; standard and Windows-native imports
      only), and the checker says it runs again on arrival and that nothing is sandboxed.
    - **The rule builder:** *Do* picks only from this library.

35. **Enabling a rule is a checkbox, not a switch.** The user's preference, and it keeps the control
    in step with every other yes/no in a table.

36. **Looking at a machine is not being in it.** A machine's page always offers **Enter session**,
    with a confirm that names the cost. A session already running there is shown on its own strip,
    with its own acts: *Return to it* / *Leave session* when it is yours, *End their session* when it
    is someone else's. The user: *"when a specific machine is clicked doesnt mean we are in that
    machine's session."*

37. **A short list inside a panel is rows, not a table.** A bordered table inside a panel looked like
    a box in a box. This applied to *How fast reports are dealt with* and the Overview's open issues.
    Tables stay for the long, sortable lists that are the page.

**Still open — shown in the concept, not yet decided:**

- **Green.** The concept uses it for completed outcomes (*Success*, *Ready*, *Within target*). The 29
  Sep rule says green is not used at all. Machines that are fine are grey either way.
- **Rule 12, two words per button.** The concept breaks it where a choice needs its phrase (*No
  checks, I will verify it by hand*, *Test on one machine*). Decide whether choice buttons are exempt.
- **Destinations per flow.** The concept warns past 8 and has no hard cap.
- **The CPU bands (60 / 75 / 90).** The top band matches the *Sustained high CPU* rule.
- **Which areas each level sees.** The concept shows every area at one level so it can be judged;
  rule 25 still decides what a Super User sees at their own level.
- **Deferred items the concept draws anyway.** It has a flow stage editor and a rule condition
  builder. The JSON shapes behind them, `condition_spec` and a flow stage's `config`, are still on
  the deferred list (spec §10). The concept shows how they might look; it decides nothing about them.
- **Engine work the concept assumes.**
  - **Live matching** wants the reader's patterns in shared code (`common/`, stdlib only), plus a
    lookup handler for the directory, file index and installed programs. Under the project's own
    rule that is an Engine handler and TUI command first.
  - **The rule backtest** ("if it had been on last week") needs enough stored metric history to
    replay.
  - **Typed issues** need one Engine read that gathers violations, pings, deviations, escalations and
    blocked flows into a single list.

---

## What stays custom

antd has no vocabulary for these, and they are the product:

| | What it draws | Built from |
|---|---|---|
| **Day timeline** | who held each machine, and when. Two switches: **Working hours · 24 hours** for the span. Working hours (06:00–18:00, adjustable) is the default, and a session outside the frame is named under the chart, never dropped. **Chart · Report** for how you read it | custom Shapes + `Table`, behind two `Segmented`s |
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
