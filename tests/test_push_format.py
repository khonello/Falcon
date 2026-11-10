"""What a live push reads as, in the TUI and on the console's Live activity (operator_client/tui/push_format.py). The user saw object dumps on Overview, 10 Nov 2026."""

from __future__ import annotations

from operator_client.tui.push_format import describe_push


def test_a_recorded_event_reads_as_its_sentence_with_who_did_it():
    p = {"id": 3221, "at": "2026-11-05T17:15:27+00:00", "kind": "system", "action_type": "auth.connected", "actor": "ADM-01-Operations-5",
         "what": "signed in", "host": "ADM-01"}
    assert describe_push("audit.event", p) == ("ADM-01-Operations-5: signed in (on ADM-01)", False)
    assert describe_push("audit.event", {**p, "what": "ADM-01 was entered"}) == ("ADM-01-Operations-5: ADM-01 was entered", False)
    assert describe_push("audit.event", {**p, "actor": None}) == ("System: signed in (on ADM-01)", False)
    assert describe_push("audit.event", {"kind": "system"})[0] == ""


def test_a_look_again_signal_is_not_shown():
    for t in ("pc.presence", "machines.changed", "todo.changed", "control.interest_changed"):
        assert describe_push(t, {"pc_id": 5, "online": True}) == ("", False)


def test_nothing_is_ever_shown_as_a_raw_payload():
    text, _ = describe_push("something.new_kind", {"secret": "x", "id": 4})
    assert text == "something new kind" and "{" not in text and "secret" not in text
