# design/ — the Operator Client design, as code

The GUI's visual design is generated here and published to a design canvas, so a change to the look is a
change to a file, reviewable like any other.

**Canvas:** <https://claude.ai/artifact/71rNVLEqFPPwJ2mPoD7Vpw> ("Falcon Operator Design").

```powershell
environ-engine\Scripts\python.exe design\gen.py          # writes design/boards/*.dc.html
```

Each board is one self-contained HTML page at 1440x900 — the same canvas the real window gets. Screenshot
one with headless Edge:

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 `
        "--screenshot=design\shots\Main.png" "file:///$PWD/design/boards/Main.dc.html"
```

## The files

| File | What it holds |
|---|---|
| `gen.py` | tokens (`T`), icons, the layout helpers every board uses, and the board list |
| `v4.py` | **the kit**: the chosen components — pills, card rows, the detail card, tiles, the lane, the shell pieces |
| `v5.py` | the Admin screens (home, traversing, occupied, assisted, tasks, flows, automation, assistance, resources, reports) |
| `v6.py` | the lane: the detail card filled and with nothing selected |
| `v7.py` | events, the actions library, the live dashboard |
| `v8.py` | the Super User surfaces |
| `v2.py`, `v3.py` | earlier passes kept for the states, worker surfaces and dialogs they still own |
| `mood.py` | the component mood board (M01–M15): every component in three or four approaches |
| `su_mood.py` | the Super User mood board (S01–S04): shape, figures, authority, descent |
| `shot_gui.py` | renders the **real QML app** offscreen with a stubbed bridge, for before/after screenshots |

`boards/` is generated output and is not committed.

## How a change travels

1. Edit the module, re-run `gen.py`, screenshot the board.
2. Publish the changed `boards/*.dc.html` to the canvas (as `project/<name>.dc.html`).
3. Carry it into `operator_client/gui/qml/` — tokens to `Theme.qml`, components to the kit files, screens
   to `<Name>View.qml`.
4. Screenshot the running app with `shot_gui.py <out-dir> <admin|super_user> [rail-index]` and check the
   two match.

The design rules these boards encode (one gradient frame, four toned meanings, one-line rows, the detail
card that never closes, no tables, no left-edge accents) are written on the `Tokens` board.
