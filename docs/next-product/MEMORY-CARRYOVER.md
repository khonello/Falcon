# Memory to carry into the new product

A session's memory belongs to its folder, so Falcon's does not follow the fork. The first session in the new product's folder saves each
entry below as its own memory (one fact per file, with **Why** and **How to apply**), then tells the user. Most rules are also in the
fork's `CLAUDE.md`; memory is what makes them stick between sessions. Written 15 Nov 2026 from Falcon's memory.

## How the user works (feedback)

- **Commit as you work**: each finished, tested piece, only your own files; pushing needs asking.
- **Don't wait on obvious steps** of agreed work; ask only for real decisions; check a problem before raising it.
- **Ask before downloads or new dependencies**: what and how big; put the question in the final message.
- **Final messages are self-contained**: the user often reads remotely; results and questions go in the last message.
- **Send screenshots** of any board or UI when asking for picks or approval, never just a link.
- **Tests in batches** (`scripts/test_batches.py`), never one big run; no DB tests beside a running suite on the same test database.
- **Engine session never touches UI**; UI needs go to `docs/UI-WORK-FROM-ENGINE.md`. A UI session tells the user before any Engine change.
- **Power settings in the TUI only**; client ids and keys are never shown on a page.
- **The company chooses features** (screenshots, camera evidence): no legal gates or lectures; state facts, list collections.
- **Resolve design conflicts yourself** where the rules settle them; bring only real choices.

## UI rules settled in Falcon (for the new concept, unless the user changes them)

- Match the concept by measure (port its CSS/markup and compare side by side; an eyeballed port was rated 2/10).
- A list click selects; the item shows beside the list; drawers only for creating. Buttons do what they say (confirm first); only Look navigates.
- Every growing list pages in place, four a page; a list has a set size; an opened card holds fixed details only, never a growing list.
- Side-by-side cards share the tallest one's height. Paths are cut in the middle; subtitles are a few words.
- Calm colour on marks (no rainbow), avatar-led cards, trees for branching, no left-edge accents, no tables in pages.

## The product (project)

- **One product, not an umbrella** (15 Nov 2026): cases and what matters (marks) are one job; see `docs/next-product/START-HERE.md`.
- **Its name is not chosen**; work under the codename; rename the brand once, in one pass, before anything ships.
- **Pricing**: yearly seat grants; Admin and Worker seats priced apart (suggested, not settled: Worker ~$40/yr, Admin ~$400/yr).
- **Containment** (the escalation ladder an Admin switches on knowingly; rungs: files Private, exits narrowed, machine closed, the blocker
  as last resort, session locked; the blocker is calm, never shows how long it lasts, one Report now button) is in the proposal document.
- **Seats and setups** follow `docs/SEATS-AND-SETUP.md` (knocking, seats, store-signed grants and claims, private PostgreSQL on both platforms).
