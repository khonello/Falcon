# The spine: one event stream, four features that share what they know (the owner, 18 Oct 2026)

Task, Flow, Restricted and Detective are meant to work as one system, not four programs that happen to read the same tables. The way to make that true on purpose is to build the
system **around events**: an OS event (a file moved, a drive plugged in, a program started, a log cleared, a picture on the clipboard) and a system event (a task assigned, a flow
synced, a mark made, a case raised) are the same kind of thing, flow through the same place in the same order, and **carry what each feature finds out to the next**.

## The model (`engine/bus.py`)
```
event ──► heat ──► guard ──► act ──► judge ──► tell
```
| Stage | Question | Who is there today |
|---|---|---|
| **heat** | what did this happen to? mark it hot, so it and the work waiting for it go first | the Engine (`common/heat.py`) |
| **guard** | what is it? restricted? a copy of something marked? where is it allowed? | Resource compliance, Restricted marks, the *facts* handler |
| **act** | what must be done? | Task (expectations), Flow (propagation), automations, issues |
| **judge** | what does it mean? | Detective |
| **tell** | who must hear? | (reports and notices: next) |

* **The order is stated, not accidental.** Resource used to judge a file before Flow acted only because it was installed first. Now each handler registers *at a stage*, and every event
  passes the stages in order whatever the install order.
* **Facts travel with the event.** `event.facts` is what the stages found out: the index entry, whether the file is restricted and why, whether it is simply the machine's own department's
  work, whether a flow wrote it. Detective reads these instead of asking each feature's tables itself. This is the sharing: the context is the event.
* **Hot first.** The first stage marks the subject hot; the guard stage answers "is this marked?" from memory in one lookup (`engine/marked.py`: the marked places and every marked hash);
  catch-ups and healing take hot things first. The authority is still the database wherever something acts on the answer (a Flow checks every step itself).
* **OS and system events are one stream.** File events and `os.signal` (a drive, a program, a cleared log, a picture on the clipboard, an upload) both go through `engine.bus.publish`;
  automations hear them at "act", Detective at "judge". A handler can publish a further event with the one it is handling as its `cause`: the chain is kept, and one longer than
  `MAX_DEPTH` (6) is dropped, so two features that answer each other cannot loop.
* **A handler that fails is logged, and the event carries on** to the others: one feature's bug is never another feature's missed event. A handler slower than two seconds is said so.

## Rules that keep it safe
1. **One owner per fact.** Restricted status is Restricted's; "a flow wrote this" is Flow's; "a task asked for this" is Task's; what it means is Detective's. Others read, never recompute.
2. **A feature may weigh another's facts; it may not change another's state without a person.** A later stage can lower or raise a weight (Detective lowering a finding because a task asked
   for the file). Anything that changes what another feature holds (marking a folder, pausing a flow, creating a task) is a *proposal* to a human: "propose, never silently resolve".
3. **Everything that influences is explainable** (the "because" lists) **and reversible.**
4. **Influence runs one way per decision.** Guard informs act, act informs judge; judge never feeds back into the same event's guard.
5. **Privacy invariants hold across the spine** (Display Names never propagate across layers; Admins see their own department).
6. **Worst cases are clamped** (`docs/design/worst-cases.md`): a bounded bus, bounded memory index, bounded chains.

## What is on the spine now
**Events.** Every file event (all ops); every OS signal (`os.signal`); and Falcon's own: `task.created`, `flow.created` / `flow.paused` / `flow.synced` / `flow.failed` / `flow.restricted_granted` /
`flow.restricted_declined`, `mark.created` / `mark.removed`, `case.raised` / `case.reviewed`.

**Facts on a file event**, each written by the feature that owns it and read by the ones after:
| Fact | Written by (stage) | Read by |
|---|---|---|
| `entry`, `hash`, `restricted` (and why), `own_scope` | Restricted (guard) | Detective |
| `flow_wrote` | Flow (act) | Detective |
| `flow_route` (the flows that read from / write to this folder) | Flow (act) | Detective |
| `flow_bypass` (what a flow delivers here, put here by hand) | Flow (act) | Detective (a finding of its own, `flow_bypass`) |
| `task_expects` (an open task asks for exactly this content) | Task (act) | Detective (lowers the finding, "a task asks for exactly this") |

**Features hear each other by event, not by call.** A mark is made (`mark.created`) and Flow, which listens, holds every flow through it and asks the owner; a task is created (`task.created`)
and Task drops what it expected and Detective drops its copy; a flow changes and Flow forgets which folders it reads and writes; a case is raised or reviewed and the proposals (below) listen.

**Proposals** (`engine/proposals.py`, `proposals.list` / `proposals.decide`, `proposals` in the shell): Detective may not change another feature's state, but it may say what it would do.
On `case.raised` it can propose "pause flow #n" (an urgent exfiltration case on a flow's source machine) and "mark this folder" (files from an unrestricted folder keep turning up in a case);
on `case.reviewed` as escalated, a follow-up task for the department's Admin. Nothing happens until a person accepts; accepting a pause is the person's audited act; marking and tasks are made by the
person on their own pages. The same suggestion is not made twice while open; there are at most 500 open.

**Still to do on the spine:** a priority queue with a bound so a backlog of cold events never stands in front of a hot one (catch-ups already take hot files first); the "tell" stage for
reports and notices; more proposals as more cross-feature insights appear.
