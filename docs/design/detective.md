# Detective

What a person seems to be trying to do, read from several small things happening together on a machine. Not "this event, so do that": a model of
human intent. Built 16 Oct 2026 from the owner's brief; `common/detective.py` is the matcher, `engine/detective/` keeps and routes what it concludes,
`scripts/detective_scenarios.py` plays scripted people against it.

## Decisions (the owner, 16 Oct 2026)
- **Who sees what:** coverage of Admin machines goes to the Super User; coverage of department machines goes to that department's Admin (and the Super User).
  An Admin never sees their own machine's cases.
- **Automatic, not triggered**, and the person at the machine is **not told**. (Live screen viewing is a separate feature and still tells the person.)
- **Windows-first** (the signals come from Windows; the Engine is the part that runs on Linux).
- No legal constraint was stated on window titles and file names appearing in evidence.
- Eight behaviours from the start, Reach included.

## The model
- **Behaviours** (human words): concealment, collection, exfiltration (taking out), capture, erasure, evasion, sabotage, reach.
- **Mini-graphs**: each behaviour owns a few small patterns. A pattern has one **spark** (the event that starts it) and, only when it appears, looks back and
  forward over a window for supporting steps -- so it is cheap. Built so far: hidden, disguised name, buried (concealment); archived, gathering (collection);
  to a drive, drive after staging (exfiltration); removed after taking, mass removal, history cleared (erasure); outside role (reach). Capture, evasion and
  sabotage have vocabulary but no graphs yet (they need signals the Worker does not send yet).
- **Case**: findings about the same machine and files, collected under one **intent** ("Taking data out", "Covering up", "Gathering", "Looking where they should
  not", "Hiding something", "Wrecking things"), with the **stage** reached out of five (Reaching, Gathering, Hiding, Taking out, Covering up), the step that has
  not happened yet ("It has not left the machine yet") and what usually comes next. The verdict is the case's, never one graph's.
- **Thread**: findings join a case when they share a file (identity/content survives rename and copy, an archive carries its sources), or fall in the same sitting
  (2 h), or continue the same arc on the same machine within 7 days (the patient actor).
- **Weight**: independent hints combine (1 - the chance every one is nothing) with a small bonus per further kind of behaviour. Levels: noted (0.35, kept quietly),
  case (0.60, raised: Super User and Admin told), urgent (0.85).
- **Context** lowers or raises a finding: Falcon's own work is ignored entirely; a task for that file, a flow that wrote it, a recorded allowance, a drive this
  machine uses all the time, and programs that move files for a living all lower it; a drive never seen before raises it; time of day only nudges, never starts anything.
- **Provenance** (`Sig.by`: hand / started / alone / falcon / unknown) is a weight, never a verdict. Today the Engine marks Falcon's own writes and leaves the rest
  "unknown"; the Worker's witness layer (process for each change, whether input just happened, foreground program) fills it in.
- **Voice**: a pattern and its evidence, never an accusation or a cause; every finding says what would make it innocent. Review uses the deviation outcomes
  (explained / accepted / dismissed / escalated) and is audited.

## Where it runs
The matcher runs in the Engine over the file events and drive signals it already receives (control.signal interest now always includes usb.inserted/removed).
It is stdlib-only so it can move to the Worker later (raw activity then never leaves the machine; only findings do) without changing what the Engine keeps.

## Not built yet (in order)
1. Witness signals on the Worker: process and parent for a file change (ETW), whether input just happened, USB drive serial/label, log clearing, screenshot-tool and
   clipboard-image signals, which attribute changed beyond hidden. 2. Graphs for capture, evasion (including a machine going silent) and sabotage.
3. A demo-scenario generator for showing it (the page itself is built). 4. The model (Qwen3-1.7B) as a labeller of names/paths/
titles (is this a disguise? a webmail window?) and a second opinion on a case -- measured with and without, never the verdict. 5. Moving the matcher to the Worker.
