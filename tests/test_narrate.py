"""The sentence layer: every dashboard sentence is generated here, so every one of them is tested
here. No Engine, no database, no Qt -- `operator_client.core.narrate` is pure functions over the
dicts the handlers already return.

What is being held to account: the twelve-word rule, the fallback to a plain fact when no condition
matches, and the distinction the design turns on -- a zero is a RESULT (state "ok"), an absence is
"empty", and too little to draw is "thin".
"""

from __future__ import annotations

import pytest

from operator_client.core import narrate as n

DEPT = {"department_id": 1, "name": "Operations", "admins": [{"account_id": 2}],
        "workers": [{"account_id": 3, "pc_id": 11}, {"account_id": 4, "pc_id": 12}]}
EMPTY_DEPT = {"department_id": 3, "name": "Logistics", "admins": [], "workers": [{"account_id": 9, "pc_id": 41}]}


def words(result) -> int:
    return len(result["sentence"].split())


# --- the rules every sentence obeys --------------------------------------------------------------

def test_every_sentence_is_twelve_words_or_fewer():
    """The limit is enforced in `_say`, so a violation is a raise, not a long line in the UI."""
    cases = [
        ("rollout", {"version": {"version_string": "1.4.2"}, "pc_count": 14,
                     "pcs_behind": [{"hostname": "OPS-06"}, {"hostname": "LOG-02", "escalated": True}]}),
        ("rollout", {"version": {"version_string": "1.4.2"}, "pc_count": 14, "pcs_behind": []}),
        ("rollout", {}),
        ("confirmations", {"points": [0, 3, 6, 8, 10, 12, 12]}),
        ("confirmations", {"points": [0, 3, 6, 8, 10, 10, 10]}),
        ("confirmations", {"points": []}),
        ("confirmations", {"points": [0, 1]}),
        ("dept_people", {"admins": [{"name": "R. Mensah"}, {"name": "A. Quaye"}],
                         "selected": {"name": "R. Mensah"}, "machines": 96}),
        ("dept_people", {"admins": [], "machines": 7}),
        ("fleet", {"pc_count": 14, "pcs_behind": [{"hostname": "OPS-06"}]}),
        ("fleet", {"pc_count": 14, "pcs_behind": []}),
        ("fleet", {"pc_count": 0}),
        ("rollout_departments", {"departments": [
            {"department_name": "Operations", "pcs": 7, "pending": 1, "escalated": 0},
            {"department_name": "Logistics", "pcs": 2, "pending": 0, "escalated": 1}]}),
        ("rollout_departments", {"departments": [
            {"department_name": "Operations", "pcs": 7, "pending": 1, "escalated": 0}]}),
        ("rollout_departments", {"departments": [
            {"department_name": "Operations", "pcs": 7, "pending": 0, "escalated": 0}]}),
        ("rollout_departments", {"departments": []}),
        ("blocking", {"version": {"version_string": "1.4.2"}, "pc_count": 11, "pcs_behind": [
            {"hostname": "OPS-06", "failures": 1},
            {"hostname": "LOG-02", "failures": 6, "escalated": True}]}),
        ("blocking", {"version": {"version_string": "1.4.2"}, "pc_count": 11,
                      "pcs_behind": [{"hostname": "OPS-06", "failures": 1}]}),
        ("blocking", {"version": {"version_string": "1.4.2"}, "pc_count": 11, "pcs_behind": []}),
        ("blocking", {"pc_count": 11}),
        ("needs_you", {"tree": [DEPT, EMPTY_DEPT], "pcs_behind": [{"hostname": "OPS-06"}],
                       "violations": [{"filename": "b.xlsx", "hostname": "OPS-07"}], "deviations": []}),
        ("needs_you", {"tree": [DEPT, EMPTY_DEPT], "pcs_behind": [], "violations": [], "deviations": []}),
        ("needs_you", {"tree": [DEPT], "pcs_behind": [], "violations": [], "deviations": []}),
        ("hierarchy", {"tree": [DEPT, EMPTY_DEPT]}),
        ("hierarchy", {"tree": [DEPT]}),
        ("hierarchy", {"tree": []}),
        ("assistance", {"pairs": [{"from_name": "Operations", "to_name": "Finance", "count": 2}]}),
        ("assistance", {"pairs": []}),
        ("routing", {"categories": ["a", "b", "c"], "routing": [{"category": "a"}]}),
        ("routing", {"categories": ["a"], "routing": [{"category": "a"}]}),
        ("routing", {"categories": []}),
        ("the_day", {"pc_count": 7, "quiet_pcs": 2, "sessions": [
            {"occupied_via": "native"}, {"occupied_via": "traversal", "occupant_role": "admin", "ended_at": "x"},
            {"occupied_via": "traversal", "occupant_role": "super_user", "hostname": "OPS-07", "ended_at": None}]}),
        ("the_day", {"pc_count": 7, "quiet_pcs": 7, "sessions": []}),
        ("the_day", {"pc_count": 0}),
        ("entries", {"sessions": [
            {"occupied_via": "traversal", "occupant_role": "admin", "occupant_name": "R. Mensah",
             "hostname": "OPS-03", "ended_at": "t"},
            {"occupied_via": "traversal", "occupant_role": "super_user", "occupant_name": "You",
             "hostname": "OPS-07", "ended_at": None}]}),
        ("entries", {"sessions": [{"occupied_via": "native"}]}),
        ("never_signed_in", {"quiet": ["OPS-02", "OPS-06"], "pc_count": 11}),
        ("never_signed_in", {"quiet": ["OPS-02"], "pc_count": 11}),
        ("never_signed_in", {"quiet": [], "pc_count": 11}),
        ("never_signed_in", {"quiet": [], "pc_count": 0}),
        ("violations", {"violations": [{"filename": "b.xlsx", "hostname": "OPS-07", "resource_tag": "restricted"}]}),
        ("violations", {"violations": [{"filename": "b.xlsx", "hostname": "OPS-07", "resource_tag": "restricted"},
                                       {"filename": "c.xlsx", "hostname": "OPS-01", "resource_tag": "admin"}]}),
        ("violations", {"violations": []}),
        ("deviations", {"deviations": [{"expectation": "hostname_mismatch"}]}),
        ("deviations", {"deviations": [{"expectation": "x", "resolved_at": "t"}]}),
        ("deviations", {"deviations": []}),
        ("work", {"tasks": [{}, {}], "flows": [{"status": "active"}], "overdue": 1}),
        ("work", {"tasks": [{}], "flows": [{"status": "paused"}], "overdue": 0}),
        ("work", {"tasks": [{}], "flows": [{"status": "active"}], "overdue": 0}),
        ("work", {"tasks": [], "flows": []}),
        ("out_of_place", {"violations": [{"filename": "b.xlsx", "hostname": "OPS-07", "resource_tag": "restricted"}],
                          "deviations": [{"expectation": "hostname_mismatch"}]}),
        ("out_of_place", {"violations": [], "deviations": []}),
        ("nonsense", {}),
    ]
    for topic, data in cases:
        r = n.narrate(topic, data)
        assert words(r) <= n.MAX_WORDS, (topic, r["sentence"])
        assert r["sentence"].endswith("."), (topic, r["sentence"])
        assert r["state"] in ("ok", "empty", "thin")
        # the brief shares a line with a cell's title on the Overview, so it must never wrap
        assert len(r["brief"].split()) <= 6, (topic, r["brief"])


def test_the_word_limit_is_a_raise_not_a_long_line():
    with pytest.raises(ValueError):
        n._say("one two three four five six seven eight nine ten eleven twelve thirteen")


# --- a zero is a result, not an absence -----------------------------------------------------------

def test_a_zero_is_a_result_and_an_absence_is_not():
    every = n.narrate("rollout", {"version": {"version_string": "1.4.2"}, "pc_count": 14, "pcs_behind": []})
    assert every["state"] == "ok" and "Every PC" in every["sentence"]

    none_yet = n.narrate("rollout", {"pc_count": 14})
    assert none_yet["state"] == "empty" and none_yet["note"] == "Nothing recorded yet"

    thin = n.narrate("confirmations", {"points": [0, 1]})
    assert thin["state"] == "thin" and "Not enough" in thin["note"]

    # no violations at all is a result too: it reports, it does not go blank
    clean = n.narrate("violations", {"violations": []})
    assert clean["state"] == "ok" and "Nothing is out of place" in clean["sentence"]

    quiet = n.narrate("needs_you", {"tree": [DEPT], "pcs_behind": [], "violations": [], "deviations": []})
    assert quiet["state"] == "ok" and quiet["facts"] == [] and quiet["action"] == ""


# --- the conditions pick the right template -------------------------------------------------------

def test_rollout_names_what_is_behind_and_offers_the_one_action():
    r = n.narrate("rollout", {"version": {"version_string": "1.4.2"}, "pc_count": 14,
                              "pcs_behind": [{"hostname": "OPS-06"}, {"hostname": "LOG-02", "escalated": True}]})
    assert r["sentence"] == "2 PCs are behind, so the next version stays blocked."
    labels = {f["label"]: f["value"] for f in r["facts"]}
    assert labels["Confirmed"] == "12 of 14"
    assert labels["Retrying"] == "OPS-06" and labels["Failing"] == "LOG-02"
    assert r["action"] == "Prompt their Admins"


def test_confirmations_notices_a_stall_before_it_reports_progress():
    assert n.narrate("confirmations", {"points": [0, 3, 6, 9, 9, 9, 9]})["sentence"] == \
        "Nothing has confirmed for 3 days."
    assert n.narrate("confirmations", {"points": [0, 3, 6, 8, 10, 11, 12]})["sentence"] == \
        "12 PCs confirmed this week."


def test_the_opened_rollout_names_the_machines_the_gate_rests_on():
    """Approving N+1 is refused while any PC is behind on N, so the reading panel is about the
    machines holding the gate -- what is failing first, because that is what has to be dealt with."""
    r = n.narrate("blocking", {"version": {"version_string": "1.4.2"}, "pc_count": 11, "pcs_behind": [
        {"hostname": "OPS-06", "failures": 1},
        {"hostname": "LOG-02", "failures": 6, "escalated": True}]})
    assert r["sentence"] == "The next version stays blocked until 2 PCs confirm."
    assert r["facts"][0] == {"label": "Failing", "value": "LOG-02, 6 attempts", "tone": "danger"}
    assert r["facts"][1]["value"] == "OPS-06" and r["action"] == "Prompt their Admins"

    one = n.narrate("blocking", {"version": {"version_string": "1.4.2"}, "pc_count": 11,
                                 "pcs_behind": [{"hostname": "OPS-06", "failures": 1}]})
    assert one["sentence"].endswith("until 1 PC confirms.")

    clear = n.narrate("blocking", {"version": {"version_string": "1.4.2"}, "pc_count": 11, "pcs_behind": []})
    assert clear["state"] == "ok" and clear["tone"] == "ok"


def test_by_department_names_the_one_holding_the_fleet_up():
    r = n.narrate("rollout_departments", {"departments": [
        {"department_name": "Operations", "pcs": 7, "pending": 1, "escalated": 0},
        {"department_name": "Logistics", "pcs": 2, "pending": 0, "escalated": 1}]})
    assert r["sentence"] == "Logistics is the only one failing." and r["tone"] == "danger"

    retrying = n.narrate("rollout_departments", {"departments": [
        {"department_name": "Operations", "pcs": 7, "pending": 1, "escalated": 0}]})
    assert retrying["tone"] == "warn" and "none past the threshold" in retrying["sentence"]

    done = n.narrate("rollout_departments", {"departments": [
        {"department_name": "Operations", "pcs": 7, "pending": 0, "escalated": 0}]})
    assert done["sentence"] == "Every department is fully confirmed." and done["tone"] == "ok"


def test_an_empty_department_outranks_a_rollout_in_what_needs_you():
    r = n.narrate("needs_you", {"tree": [DEPT, EMPTY_DEPT], "pcs_behind": [], "violations": [], "deviations": []})
    assert r["sentence"] == "Logistics has no Admin governing it."
    assert r["action"] == "Assign an Admin"
    assert {"label": "No Admin", "value": "Logistics", "tone": "danger"} in r["facts"]


def test_hierarchy_counts_the_ungoverned_pcs_not_just_the_departments():
    r = n.narrate("hierarchy", {"tree": [DEPT, EMPTY_DEPT]})
    labels = {f["label"]: f["value"] for f in r["facts"]}
    assert labels["Ungoverned PCs"] == "1"
    assert n.narrate("hierarchy", {"tree": [DEPT]})["sentence"] == "Every department has an Admin."


def test_the_day_separates_your_own_traversal_from_everyone_else_s():
    mine = n.narrate("the_day", {"pc_count": 7, "quiet_pcs": 2, "sessions": [
        {"occupied_via": "traversal", "occupant_role": "super_user", "hostname": "OPS-07", "ended_at": "t"}]})
    assert "one of them yours" in mine["sentence"]
    theirs = n.narrate("the_day", {"pc_count": 7, "quiet_pcs": 0, "sessions": [
        {"occupied_via": "traversal", "occupant_role": "admin", "ended_at": "t"}]})
    assert "none of them yours" in theirs["sentence"]
    nobody = n.narrate("the_day", {"pc_count": 7, "quiet_pcs": 7, "sessions": []})
    assert nobody["sentence"] == "Nobody signed in anywhere today." and nobody["state"] == "ok"


def test_the_opened_day_separates_who_entered_from_what_was_never_touched():
    """Two panels, two questions. Neither is the timeline's own sentence: the lead says how the day
    went, these say who was where they do not belong, and which machines nobody touched at all."""
    r = n.narrate("entries", {"sessions": [
        {"occupied_via": "traversal", "occupant_role": "admin", "occupant_name": "R. Mensah",
         "hostname": "OPS-03", "ended_at": "t"},
        {"occupied_via": "traversal", "occupant_role": "super_user", "occupant_name": "You",
         "hostname": "OPS-07", "ended_at": None}]})
    assert r["sentence"] == "2 entries today, 1 still open." and r["tone"] == "danger"
    assert r["facts"][1] == {"label": "You", "value": "OPS-07", "tone": "danger"}

    none = n.narrate("entries", {"sessions": [{"occupied_via": "native"}]})
    assert none["sentence"] == "Nobody entered another machine today." and none["tone"] == "ok"

    quiet = n.narrate("never_signed_in", {"quiet": ["OPS-02", "OPS-06"], "pc_count": 11})
    assert quiet["sentence"] == "2 machines were never signed in today." and quiet["brief"] == "2 of 11"
    one = n.narrate("never_signed_in", {"quiet": ["OPS-02"], "pc_count": 11})
    assert one["sentence"] == "1 machine was never signed in today."
    # every machine used is a result, drawn normally, not an empty panel
    every = n.narrate("never_signed_in", {"quiet": [], "pc_count": 11})
    assert every["state"] == "ok" and every["tone"] == "ok"


def test_an_unknown_topic_is_an_empty_panel_not_an_exception():
    r = n.narrate("does_not_exist", {})
    assert r["state"] == "empty" and r["facts"] == []


# --- who governs a department --------------------------------------------------------------------

def test_an_admin_never_owns_a_subset_of_the_departments_machines():
    """The boards group machines under an Admin; the system has no such relationship. `accounts`
    carries a department and never a supervising Admin, and report routing resolves to every Admin
    in the department by design. So the sentence says all of them govern all of it, and no fact ever
    claims an Admin "answers for" a number of machines."""
    at_work = {"name": "R. Mensah", "session": {"occupied_via": "native"}}
    also = {"name": "A. Quaye", "session": {"occupied_via": "native"}}
    r = n.narrate("dept_people", {"admins": [at_work, also], "selected": at_work, "machines": 96})
    assert r["sentence"] == "All 2 Admins here govern all 96 machines."
    labels = [f["label"] for f in r["facts"]]
    assert "Admins here" in labels and "Client PCs" in labels
    assert not any("answers" in lbl.lower() for lbl in labels)


def test_one_admin_governing_alone_is_said_in_the_singular():
    alone = {"name": "E. Owusu", "session": {"occupied_via": "native"}}
    r = n.narrate("dept_people", {"admins": [alone], "selected": alone, "machines": 7})
    assert r["sentence"] == "E. Owusu governs all 7 machines here."


def test_a_department_with_no_admin_is_a_danger_not_an_empty_panel():
    """Ungoverned is a RESULT: it is drawn normally, in the danger tone, with something to do about
    it -- never the "nothing recorded yet" overlay."""
    r = n.narrate("dept_people", {"admins": [], "machines": 7})
    assert r["state"] == "ok"
    assert r["tone"] == "danger"
    assert r["action"] == "Assign an Admin"
    assert "Nobody governs" in r["sentence"]


def test_the_selected_admin_is_what_the_sentence_is_about():
    """Whoever the cell draws is whoever is selected, so selecting someone away helping changes the
    sentence rather than only the picture."""
    away = {"name": "A. Quaye", "session": {"occupied_via": "assisted_access"}}
    r = n.narrate("dept_people", {"admins": [{"name": "R. Mensah", "session": {"occupied_via": "native"}}, away],
                                  "selected": away, "machines": 96})
    assert r["sentence"] == "A. Quaye is helping another department right now."
    assert r["tone"] == "accent"


def test_the_fallback_count_agrees_with_its_verb():
    """"2 things needs addressing" reached a screenshot before anyone noticed. A generated sentence
    is still a sentence."""
    one = n.narrate("needs_you", {"tree": [], "violations": [{"filename": "a.xlsx", "hostname": "OPS-07"}],
                                  "deviations": [], "pcs_behind": []})
    assert one["sentence"] == "1 thing needs addressing."
    two = n.narrate("needs_you", {"tree": [],
                                  "violations": [{"filename": "a.xlsx", "hostname": "OPS-07"}],
                                  "deviations": [{"expectation": "hostname_match"}], "pcs_behind": []})
    assert two["sentence"] == "2 things need addressing."
