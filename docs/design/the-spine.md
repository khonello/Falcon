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

## What is on the spine now / what is next
Now: every file event (all ops), every OS signal; the facts `entry`, `hash`, `restricted`, `own_scope`, `flow_wrote`; the marked index; the stage order; hot-first marking.
Next, one at a time with joint scenarios (all four features acting on one story):
* `task.assigned`, `flow.created`/`flow.synced`, `mark.created`/`mark.changed`, `case.raised`/`case.reviewed` as events, so features react to each other instead of polling:
  * **Task as expected movement**: Detective expects what a task asks for (today by its own cache; becomes a `task_expects` fact).
  * **Flows as legitimate routes**: a file appearing at a flow's destination by another route is a bypass.
  * **Detective proposes**: a folder that outsiders keep reading → "mark it?"; an urgent exfiltration case on a flow's source machine → "pause the flow?"; a reviewed case → "follow-up task?".
  * **Restricted tells the others**: marking a folder pauses the flows through it at once (done: `guard.sweep`), and tells the tasks that name its files.
* A priority queue with a bound, so a backlog of cold events (a catch-up) never stands in front of a hot one (`index.catchup` already takes hot files first).
