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
- **Operator Client** — the full GUI (every page in the design, on one component kit) plus a TUI that
  can drive the same handlers from a script.
- **Worker Client** — file watching with a polling fallback, idle detection, detached execution of 17
  built-in actions and custom scripts, flow relay, lockout, and five windows.
- **184 tests pass**, `ruff` clean. Integration tests run the real handshake over a real socket.

**What that means:** the product is real software, not a prototype. What it is not yet is a *product a
stranger can install*.

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

Fifteen specific gaps, in `design/ENGINE-WORK.md`. The ones that would embarrass a demo:

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
2. **Close the hollow features that the demo touches** — ENGINE-WORK items 1, 4, 5, 12, 14.
3. **Run the day yourself**, write down what went wrong, fix that list.
4. Then hardening and the rest of `ENGINE-WORK.md`.

---

## The rabbit hole, named so we do not fall back in

Phase 7 (the UI) ran long: 164 design boards, four rounds of mood boards, three rewrites of the same
screens, and a documentation trail about the documentation. The design was approved on 27 Sep 2026 and
every page was rebuilt to it on 28 Sep. **It is finished.**

From here:

- **No new design passes, no new boards, no mood boards.** The UI changes only when a real person hits
  a real problem, and then only that screen.
- **The board generators and the design-process record are deleted** (they are in git history if ever
  needed: commit `1985766` and earlier). What survives is `design/PATTERNS.md` — the measured rules any
  fixed screen must still follow — and `design/ENGINE-WORK.md`, which is a work list, not a design.
- **`design/run_gui.py`** opens the app with sample data and no Engine, for looking at it;
  `design/shot_gui.py` and `design/shot_worker.py` do the same offscreen for screenshots. That is all
  that is left of the design tooling, and it is enough.

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
| `design/PATTERNS.md` | the UI rules, for fixing a screen |
| `design/ENGINE-WORK.md` | the 15 known gaps between what the UI offers and what the Engine does |

`CLAUDE.md` is instructions for the coding agent, not documentation.

---

## Running it today

```powershell
environ-engine\Scripts\Activate.ps1
python -m engine setup          # .env, certificate, databases, schema, first Super User
python -m engine                # run it

environ-operator\Scripts\python.exe design\run_gui.py super_user   # the GUI, sample data, no Engine
python -m operator_client --gui                                     # the GUI against a real Engine
```

Full detail, including a real network: `docs/GETTING-STARTED.md`.
