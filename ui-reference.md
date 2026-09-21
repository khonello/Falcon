# UI reference for Phase 7 — the predecessor's console is the bar for "acceptable"

The user's instruction: before Phase 7, study the Admin desktop and Client UIs in
`github.com/khonello/SystemMonitoring` (`admin/qml/`, `client/ui/`) — *the colours, the
organisation, the tabs, the structure* — that is what "acceptable" means. This file distils that
system so Phase 7 starts from it rather than from the current stock-Fusion GUI. (The predecessor
is otherwise still a last resort for implementation questions; this is a deliberate exception.)

## The idiom

A **monitoring console**: near-black canvas, raised surfaces with hairline borders, the data is the
only bright thing on screen. Accent is used sparingly and means *selected / active* — never
decoration. Colour vocabulary is deliberately tiny so an operator learns it in one glance.

## Design tokens (`admin/qml/Theme.qml`, a `pragma Singleton`)

| Group | Token | Value | Use |
|---|---|---|---|
| Surfaces (back → front) | `canvas` | `#0d1014` | the window |
| | `surface` | `#141920` | panels sitting on it |
| | `surfaceHigh` | `#1b212a` | inputs, hovered rows |
| | `overlay` | `#232b36` | dialogs, menus |
| Lines | `border` | `#242c37` | hairlines between things |
| | `borderStrong` | `#333d4b` | focused, or worth noticing |
| Text | `text` | `#e6ebf2` | |
| | `textDim` | `#94a1b2` | secondary, units, hints |
| | `textFaint` | `#5d6b7c` | placeholders, disabled |
| Meaning | `accent` | `#4c8dff` | selected / active |
| | `accentDim` | `#1e3a63` | |
| | `ok` | `#3fb950` | online, applied, success |
| | `warn` | `#d29922` | paused, capped, careful |
| | `danger` | `#f04747` | blocked, terminate, acts-on-everything |
| Geometry | `radius` / `radiusLarge` | 4 / 6 | one small radius — no pills |
| | `space1..5` | 4 / 8 / 12 / 16 / 24 | a 4px scale; everything is a multiple |
| | `controlHeight` / `rowHeight` | 30 / 34 | controls share one height so rows line up |
| Type | `fontTiny..fontHuge` | 10 / 11 / 12 / 13 / 15 / 20 | |
| | `mono` | Consolas, Cascadia Mono | numbers that change, ids, paths |

Client-side helper windows (`client/ui/Theme.qml`, instantiated per window, not a singleton):
scrim `#cc0b0f14`, surface `#161b22`, edge `#30363d`, raised `#1f262e`, text `#e6edf3` /
`#8b949e` / `#6e7681`, accent `#58a6ff`, warning `#d29922` on wash `#2d2113`, radius 14, panel
padding 34, one easing everywhere (`OutCubic`, 140 / 240 ms).

## Structure (`admin/qml/main.qml`)

- **Material style, dark**, set in exactly one place (`admin/style.py`) before any QML loads;
  `Material.roundedScale: Material.SmallScale` so controls get the 4px corner. Fusion + a
  hand-built palette is what the current Falcon GUI does — switch to this.
- **Maximized, always** (title bar and taskbar stay; not kiosk full-screen); minimums 1024×700 so
  the layout holds on a projector; everything anchored/proportional, no fixed coordinates.
- **Header (52px)**: identity block left (accent bar + letterspaced uppercase product name), a
  hairline divider, **primary navigation as underlined tabs in the header**, connection controls
  right (collapse to one mono line once connected). Navigation lives in the header so a page's own
  controls are never a second row of tabs under the first.
- **Left rail** (`ClientList`, 300px, min 220, in a `SplitView`): the fleet, always visible, so
  selection never becomes a hidden mode — every other panel is about the selected row. Dense,
  quiet rows; a state dot per row; an accent edge on the selected row; a count badge in the
  uppercase section title; hover instead of zebra striping.
- **Content** (`StackLayout` driven by the header tabs) with a **command/output panel** pinned at
  the bottom, proportional and capped (`min(300, 34% of height)`).
- **Footer (26px)**: a pulsing dot (the only animation — "the link is up" vs "this froze"), a
  status line, and "watching <x>" in accent mono.
- **Banners**: consequence-bearing notices (a pause about to lapse) are a full-width amber bar at
  the top with Extend / Dismiss — never a status-line message that scrolls past.
- **Dialogs** for things that need reading (validation failure detail in mono; a screen capture
  with its selectable path).

## Component set (`admin/qml/*.qml`)

- `Section` — titled panel: hairline border, small radius, quiet uppercase letterspaced dim title,
  optional one-line hint, optional 2px colour strip on the top edge for sections that carry a
  consequence. Replaces `GroupBox`.
- `SegmentedControl` — choice *within* a page: recessed track, active segment tinted and
  underlined in its own colour, optional counts (`Applications (52)`); a segment may declare its
  tint (a dangerous mode comes up amber). Never the same shape as the header tabs.
- `StatePill` — a state in words, in its own colour, with a filled dot; muted when it is the
  normal case. Never clickable, so it cannot be confused with the button that changes the state.
- `StatTile` — one large mono number, uppercase label, unit, a 2px tint strip on the left edge;
  116×56; a strip of them answers "alive, busy, or quiet?" from across the room.
- `DataList` — three-column rows (label, sub-label, trailing value) with accessor functions per
  view, hover highlight, an empty state with title + hint.
- `ListEditor`, `CommandPanel` (toolbar strip of one-row-height controls, then the output).

## What this means for Falcon's Phase 7

1. Port the token set into `operator_client/gui/qml/Theme.qml` (singleton) and switch the style to
   Material dark with `SmallScale`, set once in `gui/app.py`.
2. Rebuild the shell to the same skeleton: header with identity + primary tabs (Hierarchy, Tasks,
   Flows, Automation, Assistance, Reports) + connection; a **left rail that is the hierarchy tree**
   (departments → Admins → Client PCs with state dots and session pills) so the selected PC/account
   is the context every page works on; content with `SegmentedControl` for in-page choices; the
   push feed as the pinned bottom panel; footer with the pulsing link dot and session text.
3. Falcon's persistent surfaces map onto the reference's: the RED BANNER / BLOCKED become the
   full-width banner (danger tint); indicators become `StatePill`s in the header; session and
   deadline become a `StatTile` strip on the Hierarchy page.
4. Worker Overlay/Dialog: reuse the client Theme and the scrim + centred panel with the OutCubic
   appear animation; frameless, stays on top, draggable dialog.
5. Then the Falcon-specific pieces the reference does not have: the Flow node-graph editor, the
   guided Task proposal review, the automation dashboard — built from the same tokens.
