# Falcon — start here

Written 29 Sep 2026, to end a long design detour and put the work back on the only thing that
matters now: **a version a company can buy, install and run.**

Read this file first. It is the whole picture; everything else is reference.

---

## What Falcon is

Management, monitoring and automation for an organisation whose computers are arranged
**Super User → Department → Admin → Client PC**. One authority model, one audit trail, one file
index, five things it does:

| | What a buyer gets |
|---|---|
| **Hierarchy** | See and enter any machine you have authority over. One session per PC; a superior can take it, a peer cannot. Everything is logged against the person, not the seat. |
| **Task** | Give someone work, and have the system watch for the signs it was done — the files that should appear, the program that should have run. A person still decides it is finished. |
| **Flow** | One-directional sync pipelines between machines: a source folder, optional transforms, one or more destinations, with consent when a destination is not yours. |
| **Resource & Assistance** | Files carry a tier (admin / restricted / workers / common); anything in the wrong place is flagged. Ping → channel → listeners for asking for help. |
| **Control, Events, Monitoring, Actions** | Admin-authored automation in plain words: *when this happens, do that* — lock a screen, notify, close a program, run your own script. |

Three programs: the **Engine** (one server, PostgreSQL, owns everything), the **Operator Client**
(what a Super User or Admin uses — a GUI, and a TUI for scripting), and the **Worker Client** (a quiet
service on every staff machine, with small windows when it has something to say).

---

## Where it actually stands (29 Sep 2026)

**Built and working, against a real database, with tests:**

- **Engine** — 100 handlers, no stubs; 9 migrations; TLS with a pinned certificate, a master secret,
  per-client derived keys and a real challenge/response handshake; the file index, the audit trail, the
  scheduler and a local LLM for proposing task checks.
- **Operator Client** — a TUI that drives every handler from a script, and a GUI **being rebuilt**
  (see below).
- **Worker Client** — file watching with a polling fallback, idle detection, detached execution of 17
  built-in actions and custom scripts, flow relay, lockout, and five windows.
- **184 tests pass**, `ruff` clean. Integration tests run the real handshake over a real socket.

**What that means:** the product is real software, not a prototype. What it is not yet is a *product a
stranger can install*, and its console is mid-rebuild.

**The UI, as of 29 Sep 2026.** The bespoke design built through Phase 7 was judged to fail as a product
-- careful to look at, but not what a company recognises as the software it runs its IT on. It has been
deleted. The console is being rebuilt in the **Ant Design idiom** (light, dense, tables and forms,
familiar to anyone who has used an admin console), in the same PySide6/QML client over the same
`FalconBridge`. `docs/UI.md` says what we are building; `docs/UI-COMPONENTS.md` is the build list in
priority order. Until its first screen lands, `python -m operator_client --gui` says so and the **TUI
is the working surface** -- it reaches every handler.

---

## The three things that stand between here and a sale

In order. Nothing else matters until these are done.

### 1. It cannot be installed on a customer's machine (the big one)

Everything runs from source in virtual environments. There is no installer, no bundled Python, no
Windows service, no frozen Worker exes. A buyer cannot try it, and you cannot deploy it.

**Done means:** an Engine you can put on one Windows or Linux server with a single installer, and a
Worker package you can put on a staff PC that registers itself and starts at boot. Phase 9 in
`PHASES.md`.

### 2. No human has used it end to end

Only I have driven this software. A person doing a real day's work will hit things no test does.

**Done means:** you run a full day on three machines — register them, give a task, watch it verify,
set an automation, traverse into a PC, answer a ping — and the list of what went wrong is short and
fixed. Phase 8.

### 3. Some features are drawn but hollow

Fifteen specific gaps, in `docs/ENGINE-GAPS.md`. The ones that would embarrass a demo:

- the Worker sends no OS signals, so automations on "a USB drive is plugged in" or "someone signs in"
  can be created but never fire (item 1);
- `notify` prints to a log instead of showing the person a message, and `lock_session` ignores how long
  to lock for (item 4) — two of the five Worker windows therefore never open (item 14);
- "close a program" is typed in rather than picked from what is running (item 5);
- a machine that is switched off looks like any other when you try to enter it (item 12).

**Done means:** a demo where every button does what it says.

---

## The next move

**Build the demo path before anything else.** One Engine, two Worker machines, one Operator Client,
installed the way a customer would install them, doing the five things in the table above. Everything
that blocks that path is worth doing; everything else waits.

Concretely, in this order:

1. **Freeze and install.** `python -m engine setup` already prepares a machine from a clone; turn that
   into an installer, freeze the Worker (service + its two windows), and prove it on a clean machine.
2. **Close the hollow features that the demo touches** — ENGINE-GAPS items 1, 4, 5, 12, 14.
3. **Run the day yourself**, write down what went wrong, fix that list.
4. Then hardening and the rest of `docs/ENGINE-GAPS.md`.

The console rebuild (`docs/UI.md`) runs alongside 1 and 2: the demo needs a window, and the first slice
-- the shell and the Record page -- is what proves the new idiom before the other pages follow.

---

## The rabbit hole, named so we do not fall back in

Phase 7 (the UI) ran long: 164 design boards, four rounds of mood boards, three rewrites of the same
screens, and a documentation trail about the documentation. It produced a careful bespoke design, and
on 29 Sep 2026 that design was judged to fail at the only thing that mattered -- looking like software
a company runs its IT on. **It is deleted, and the lesson is the point:** we were designing a product
identity when we needed a familiar tool.

From here:

- **No bespoke design passes, no boards, no mood boards.** The console is built to an existing,
  published design language (Ant Design), so the question "what should this look like" has an answer
  we look up rather than invent.
- **The old UI, its rulebook and its process record are deleted** -- 64 QML files, the design boards,
  PATTERNS.md, the brief. All of it is in git history (commit `a91cca4` has the tree intact) if a
  drawing is ever wanted again.
- **`design/` is gone.** What survived moved: `docs/ENGINE-GAPS.md` (the fifteen real gaps) and
  `scripts/shot_worker.py` (photographs the Worker's windows).

---

## The documents that matter

| File | What it is for |
|---|---|
| `START-HERE.md` | this file: state, blockers, next move |
| `PHASES.md` | the road to shippable, phase by phase |
| `docs/GETTING-STARTED.md` | setting up a machine or a network, step by step |
| `hierarchy-system-design.md` | the origin document — the authority model everything hangs off |
| `task-natural-combo.md`, `flow-natural-combo.md`, `resource-assistance-combo.md`, `control-events-monitoring-actions-combo.md` | what each feature area does; authoritative on behaviour |
| `implementation-spec.md` | how it is built; authoritative on architecture and security |
| `database-schema.md` | every table and column, traced to the rule that demands it |
| `system-ecosystem-synthesis.md` | one page a buyer can read |
| `docs/design/super-user-reference.md`, `admin-reference.md`, `client-reference.md` | what each role can see and do, in one place — the source for what belongs on each page |
| `docs/UI.md` | what the console is being rebuilt into, and the rules that govern it |
| `docs/UI-COMPONENTS.md` | the component build list, in priority order |
| `docs/ENGINE-GAPS.md` | the 15 known gaps between what the UI offers and what the Engine does |

`CLAUDE.md` is instructions for the coding agent, not documentation.

---

## Running it today

```powershell
environ-engine\Scripts\Activate.ps1
python -m engine setup          # .env, certificate, databases, schema, first Super User
python -m engine                # run it

environ-operator\Scripts\Activate.ps1
python -m operator_client --connect                      # the TUI -- the working surface today
python -m operator_client --connect --script "tree; tasks"   # scripted, no terminal UI
```

Full detail, including a real network: `docs/GETTING-STARTED.md`.
