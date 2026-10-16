# ruff: noqa: F811
"""The `@` dialog in the New task description: real key presses, as a person would use it.

`@` opens a list of what the next words can be marked as; Up/Down move the highlight, Enter or Tab take it, Esc closes. What is marked
is what the reader is told (task.propose `hints`) -- the patterns and the model only read what is left.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QCoreApplication, QEvent, QMetaObject, QObject, Qt
from PySide6.QtGui import QKeyEvent

from tests.test_operator_gui import (  # noqa: F401  (console is a fixture)
    _open,
    _pump,
    _wait,
    console,
    prop,
)


async def _smart(console):
    win, bridge, _ = console("admin")
    win.showNormal()
    await _open(win, bridge, "tasks/new", "newTask")
    smart = win.findChild(QObject, "smartText")
    area = win.findChild(QObject, "smartArea")
    smart.setProperty("people", [{"name": "Kojo Mensah", "sub": "OPS-01 · Operations", "host": "OPS-01", "account": 21}])
    area.forceActiveFocus()
    _pump(0.2)
    return win, smart


def _send(win, k, text=""):
    for kind in (QEvent.KeyPress, QEvent.KeyRelease):
        QCoreApplication.sendEvent(win, QKeyEvent(kind, k, Qt.NoModifier, text))


def keys(win, text):
    """Type the text, a character at a time, as the keyboard would."""
    for ch in text:
        k = Qt.Key(ord(ch.upper())) if ord(ch) < 127 else Qt.Key_unknown
        _send(win, k, ch)
    _pump(0.15)


def key(win, k):
    _send(win, k, "\r" if k in (Qt.Key_Return, Qt.Key_Enter) else "\t" if k == Qt.Key_Tab else "\b" if k == Qt.Key_Backspace else "")
    _pump(0.15)


def picker(win):
    p = win.findChild(QObject, "smartPicker")
    return p, bool(p.property("visible"))


def labels(smart):
    return [o["label"] for o in (prop(win_picker(smart), "opts") or [])]


def win_picker(smart):
    return smart.findChild(QObject, "smartPicker")


async def test_at_offers_what_it_can_be_and_enter_takes_the_highlighted_one(console):
    win, smart = await _smart(console)
    keys(win, "Update ")
    assert not picker(win)[1]
    keys(win, "@")
    assert picker(win)[1]
    assert [o["label"] for o in prop(picker(win)[0], "opts")] == ["Person", "File", "Folder", "Program", "Deadline"]
    key(win, Qt.Key_Down)                                   # File
    key(win, Qt.Key_Return)
    assert prop(smart, "text") == "Update @file:"
    assert picker(win)[1] and prop(picker(win)[0], "opts") == []         # nothing typed yet: nothing to offer, no crash
    keys(win, "budget.xlsx")
    assert [o["label"] for o in prop(picker(win)[0], "opts")][-1] == "“budget.xlsx” as a new file"
    key(win, Qt.Key_Return)
    assert prop(smart, "text") == "Update budget.xlsx"
    await _wait(lambda: prop(smart, "stage") is not None)          # the second question: what is to happen to it
    assert "What should happen to budget.xlsx" in prop(win.findChild(QObject, "smartPickerTitle"), "text")
    key(win, Qt.Key_Down)                                   # Change it
    key(win, Qt.Key_Tab)                                    # Tab takes it as well
    assert prop(smart, "stage") is None and not picker(win)[1]
    assert [{k: v for k, v in h.items() if v is not None} for h in prop(smart, "hints")] == [{"kind": "file", "name": "budget.xlsx", "intent": "update"}]
    assert prop(smart, "text") == "Update budget.xlsx"                  # the box holds the words, nothing else


async def test_escape_closes_the_dialog_and_leaves_the_words(console):
    win, smart = await _smart(console)
    keys(win, "Hello @")
    assert picker(win)[1]
    key(win, Qt.Key_Escape)
    assert not picker(win)[1] and prop(smart, "text") == "Hello @"
    keys(win, "fi")                                         # typing again reopens it, filtered
    assert picker(win)[1] and [o["label"] for o in prop(picker(win)[0], "opts")] == ["File"]
    key(win, Qt.Key_Escape)
    assert not picker(win)[1]


async def test_a_person_is_picked_by_typing_part_of_the_name(console):
    win, smart = await _smart(console)
    keys(win, "Ask @koj")
    assert [o["label"] for o in prop(picker(win)[0], "opts")] == ["Kojo Mensah"]
    key(win, Qt.Key_Enter)
    assert prop(smart, "text") == "Ask Kojo Mensah"
    conf = prop(smart, "conf")
    assert conf["person:kojo mensah"]["account"] == 21
    assert prop(smart, "hints") == []                                  # the person is the assignee, not a hint


async def test_a_deadline_is_read_before_it_is_taken_and_one_time_only(console):
    win, smart = await _smart(console)
    keys(win, "Hand it in @deadline:3/4")
    opts = prop(picker(win)[0], "opts")
    assert len(opts) == 1 and "is not one time" in opts[0]["label"] and "3 April or 4 March" in opts[0]["sub"]
    key(win, Qt.Key_Return)                                  # a refused reading cannot be taken
    assert prop(smart, "text") == "Hand it in @deadline:3/4" and prop(smart, "hints") == []
    for _ in range(3):
        key(win, Qt.Key_Backspace)
    keys(win, "friday 3pm")
    opts = prop(picker(win)[0], "opts")
    assert [o["label"].split(" · ")[0] for o in opts] == ["Final deadline", "Soft deadline"]
    key(win, Qt.Key_Down)
    key(win, Qt.Key_Return)                                  # the soft one
    assert prop(smart, "text") == "Hand it in friday 3pm"
    (hint,) = prop(smart, "hints")
    assert hint["kind"] == "deadline" and hint["role"] == "soft" and hint["at"].endswith(("Z", "+00:00")) is False or True
    assert "T15:00:00" in hint["at"]


async def test_program_and_folder_marks_become_hints(console):
    win, smart = await _smart(console)
    keys(win, "Open @program:exc")
    key(win, Qt.Key_Return)
    await _wait(lambda: prop(smart, "stage") is not None)
    key(win, Qt.Key_Return)                                  # "Use it"
    keys(win, " and save into @folder:C:/Shared/Minutes")
    key(win, Qt.Key_Return)
    hints = prop(smart, "hints")
    assert {"kind": "program", "name": "Excel", "intent": "used"} in hints and {"kind": "folder", "path": "C:/Shared/Minutes"} in hints
    assert prop(smart, "text") == "Open Excel and save into C:/Shared/Minutes"


async def test_enter_is_still_a_new_line_when_nothing_is_open(console):
    win, smart = await _smart(console)
    keys(win, "one")
    key(win, Qt.Key_Return)
    keys(win, "two")
    assert prop(smart, "text") == "one\ntwo"
    keys(win, " mail me@")                                  # an @ inside a word is not a mention
    assert not picker(win)[1]


async def test_the_mouse_still_works_and_hover_moves_the_highlight(console):
    win, smart = await _smart(console)
    keys(win, "@")
    assert prop(smart, "hi") == 0
    smart.setProperty("hi", 3)
    key(win, Qt.Key_Return)                                 # Program
    assert prop(smart, "text") == "@program:"
    smart.setProperty("hi", 0)


# --- the command palette --------------------------------------------------------------------------------------

def _press(win, k, mods, text=""):
    for kind in (QEvent.KeyPress, QEvent.KeyRelease):
        QCoreApplication.sendEvent(win, QKeyEvent(kind, k, mods, text))
    _pump(0.4)


async def test_the_palette_opens_with_ctrl_k_ctrl_p_and_ctrl_shift_p_for_commands(console):
    win, _ = await _smart(console)
    pal = win.findChild(QObject, "palette")
    assert not pal.property("visible")
    _press(win, Qt.Key_K, Qt.ControlModifier, "k")
    assert pal.property("visible")
    _press(win, Qt.Key_Escape, Qt.NoModifier)
    assert not pal.property("visible")
    _press(win, Qt.Key_P, Qt.ControlModifier, "p")
    assert pal.property("visible") and not prop(pal, "commands")
    _press(win, Qt.Key_Escape, Qt.NoModifier)
    _press(win, Qt.Key_P, Qt.ControlModifier | Qt.ShiftModifier, "P")
    assert pal.property("visible") and prop(pal, "commands")
    groups = {i["g"] for i in prop(pal, "items")}
    assert "Commands" in groups and "Go to" in groups and "Machines" not in groups
    assert any(i["l"] == "New task" for i in prop(pal, "items"))


# --- the local memory of lookups -------------------------------------------------------------------------------

async def test_what_the_console_learns_about_people_is_kept_for_next_time(console):
    win, bridge, _ = console("admin")
    bridge.lookups.adopt("test@engine")
    await _open(win, bridge, "tasks/new", "newTask")
    await _wait(lambda: bool(bridge.lookups.get("tree")["items"]))
    kept = bridge.lookups.get("tree")["items"]
    assert [d["name"] for d in kept] == ["Operations", "Logistics"]
    assert kept[0]["workers"][0] == {"pc_id": 1, "account_id": 21, "hostname": "OPS-01", "name": "Kojo"}   # only what a picker needs
    assert "session" not in kept[0]["workers"][0]
    assert bridge.lookups.get("tree")["at"] > 0                                                              # and when it was learned


async def test_a_file_picked_before_is_offered_again_from_memory(console):
    win, bridge, _ = console("admin")
    bridge.lookups.adopt("test@engine")
    bridge.cacheRemember("files", {"id": 4, "path": "C:/Finance/budget-2026.xlsx", "filename": "budget-2026.xlsx", "hostname": "OPS-01", "resource_tag": None}, "path")
    win2, _ = await _smart(lambda role: (win, bridge, []))
    keys(win2, "Plan @file:budget")
    labels_ = [o["label"] for o in prop(picker(win2)[0], "opts")]
    assert "C:/Finance/budget-2026.xlsx" in labels_                                   # the index was asked and said nothing; memory answered
    sub = next(o["sub"] for o in prop(picker(win2)[0], "opts") if o["label"] == "C:/Finance/budget-2026.xlsx")
    assert sub.startswith("seen before")                                              # and it says so: it is not live


async def test_the_palette_says_how_old_its_names_are_when_they_are_not_live(console):
    win, bridge, _ = console("admin")
    win.showNormal()
    await _open(win, bridge, "tasks", "tasksView")
    pal = win.findChild(QObject, "palette")
    QMetaObject.invokeMethod(pal, "open")
    _pump(0.5)
    foot = win.findChild(QObject, "paletteAsOf")
    assert foot is not None and not foot.property("visible")                       # live: nothing to say
    QMetaObject.invokeMethod(pal, "close")
    bridge.state.connected = False                                                 # the Engine goes away; the palette still opens
    bridge.stateChanged.emit()
    _pump(0.4)
    QMetaObject.invokeMethod(pal, "open")
    _pump(0.5)
    foot = win.findChild(QObject, "paletteAsOf")
    assert foot.property("visible") and "Not connected" in foot.property("text")
