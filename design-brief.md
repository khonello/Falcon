# Falcon — UI design brief

This is the standard the Operator Client GUI (and later the Worker helper windows) must meet before
any more UI is built. It is written for a designer. It does not reference any other project or
codebase — earlier work looked at one for orientation; that is over. Judge the UI against this
document and the Falcon design docs, nothing else.

**Status: UI work is paused.** A functional GUI exists and is correct — every screen is wired to the
Engine and does what it should — but it is not designed to an acceptable standard. We do not
continue building UI until the design reaches "acceptable" as defined here. A proper designer is
expected to take this on.

## The one principle

**The system does not adapt to the UI. We mould the UI to what the system wants.** Every screen is
shaped by the Falcon concept it serves, not by what a toolkit hands you. When a stock control does
not express a concept exactly, the control is wrong — design the one that does.

## Three levels — name them honestly

- **Functional** — it works and is wired correctly, but looks assembled from default widgets.
  *This is where the current GUI is. Not acceptable.*
- **Acceptable** — the floor we must clear to resume. Deliberate use of space, a coherent visual
  language applied consistently, clear states, navigation that matches the roles, and components
  that read as made for this product rather than dropped in. Custom, not generic. **Acceptable is
  still not the target — it is the minimum to keep going.**
- **Finished / fine-tuned** — the target. Every element is customised to the system's own concepts
  and considered down to spacing, motion, hierarchy of attention, empty and error states, and how
  it feels to use. Nothing on screen is a generic widget standing in for a Falcon idea.

The only element judged acceptable so far is the **top-level tab navigation**. Everything else is
functional, not acceptable.

## What "moulded to the system" means, concept by concept

The designer should treat each of these as a thing to design, not a form to lay out. These are what
the system *is* (see the design docs for the full behaviour); the UI must make each one legible and
native.

- **Hierarchy & the two roles** — Super User and Admin are one client; the shape is
  Department → Admin → Client PC. The hierarchy is the context everything else acts on. Design how a
  person navigates it and always knows where they are and who they are.
- **Traversal & Session Blocking** — entering another PC's view is a *timed session* with an
  occupant and a deadline, evictions with rules (superiors block-or-end, peers refused, Super User
  un-evictable). A session is a control, not a row. Traversal changes the whole shell: a standing
  marker that the Super User is inside another view, the restricted-view state, the countdown.
- **Display Names** — private to the viewer, never propagating. The UI must never imply a name is
  shared.
- **Tasks** — the LLM *proposes* verification structure; a human reviews items, flags, collisions,
  splits and a deadline, and only manual verification by the assigner closes it. The task editor is
  a guided review with decisions to make, not a data-entry form.
- **Flows** — one-directional pipelines: Source → Branch/Transform/Categorize → Destinations, with
  consent, collision and cycle feedback. This is a graph. Design a graph editor, not a table of
  destinations.
- **Resource tiers & violations** — folders as access policy (admin/restricted/workers/common); a
  violation has a tier, a place, and a resolution. Show the tier and the location, not a flat list.
- **Assistance** — Ping → turn-based Message Channel → Listeners, and cross-department Assisted
  Access by consent (a separate state from traversal, with a narrowed ceiling). Channels read as a
  conversation; assisted access reads as its own distinct mode.
- **Control / Events / Monitoring & Actions** — Admin-authored automation; Actions run
  independently with their own timeout and are terminable; Custom Actions are validated scripts. The
  dashboard is an operational view; the action/event authoring is real editing.
- **Reports, Routing, Alerts, Updates** — reports written once and routed additively; alerts by
  audience; a version rollout with approval and escalation. Each is its own surface.
- **Indicators** — unaddressed pings, deadlines reached, task completed, flow failures, violations,
  offers. They persist until addressed and must be impossible to miss without being noise.
- **Worker-facing** — the Overlay (a blocked PC) and the Dialog (a notification) are the only
  surfaces a worker sees. They are designed here too, later.

## Non-negotiables for whoever designs it

- One visual language, defined once and applied everywhere — colours that mean things (and only
  things), a spacing scale, a type scale, consistent control shapes. Consistency is most of what
  reads as finished.
- Custom components fitted to the concepts above — not stock tables, buttons and group boxes.
- States are first-class: loading, empty, error, blocked, restricted, disconnected — each designed,
  not left to a default.
- The GUI opens full screen (work area), minimize and close only, no resize — behaviour already
  built; the design must assume that canvas.
- The QML stays a thin layer over the existing bridge (`FalconBridge`): the design changes the
  surface, never the ~12k lines of logic beneath. No business logic moves into the UI.

## When we resume

We resume UI work only once a design meeting "acceptable" (above) exists and is approved — ideally
from a proper designer. Until then, other phases may proceed, but the UI is frozen at its current
functional state.
