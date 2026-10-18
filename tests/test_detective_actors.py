"""People, not scripts: regular, careless and smart actors, each run several times with the dice rolled differently.

The regular ones must never be told to anyone; the ones with a purpose must be seen; and the evasions we know Detective cannot see are pinned so that a change
that starts to see them (or stops seeing something it did) is noticed rather than slipping through.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import detective_actors as da

RUNS = 6
ACTORS = {a.name: a for a in da.ACTORS}

# people doing their ordinary work (or something harmless): nobody is told, ever
HARMLESS = [a.name for a in da.ACTORS if not a.bad and a.name not in ("contractor_wrap_up",)]
# a person taking their own project documents to a drive on the way out is a judgement call the system cannot make: it may be said ("case") but never "urgent"
JUDGEMENT = ["contractor_wrap_up"]
# the ones with a purpose that must be seen and told
MUST_ALERT = ["clumsy_thief", "careless_deleter", "printscreen_fan", "ransomware_clicker", "patient_dripper", "disguiser", "task_cover", "leak_then_tidy",
              "disgruntled_wrecker", "tmp_then_zip_then_drive", "resentful_leaver", "vindictive_folder_delete"]
# seen but not alerted: noted
MUST_NOTE = ["open_snoop", "slow_poison", "curious_it", "drip_under_the_line"]
# known blind spots, written down: by design or by what we can see today (see docs/design/detective-actors.md)
BLIND = ["outside_the_roots", "flow_misuse", "one_file_by_email", "trusted_drive_abuser", "browser_drip"]


def levels(name: str) -> list[int]:
    return [da.run(ACTORS[name], 1000 + i)[0] for i in range(RUNS)]


@pytest.mark.parametrize("name", HARMLESS)
def test_ordinary_people_are_never_told_about(name):
    assert max(levels(name)) < da.LEVEL["case"], name


@pytest.mark.parametrize("name", JUDGEMENT)
def test_a_judgement_call_may_be_said_but_is_never_urgent(name):
    assert max(levels(name)) < da.LEVEL["urgent"], name


@pytest.mark.parametrize("name", MUST_ALERT)
def test_people_with_a_purpose_are_seen_and_told_about(name):
    got = levels(name)
    assert min(got) >= da.LEVEL["noted"] and sum(1 for x in got if x >= da.LEVEL["case"]) >= RUNS * 0.7, (name, got)


@pytest.mark.parametrize("name", MUST_NOTE)
def test_some_are_seen_and_put_on_the_record_without_alerting(name):
    got = levels(name)
    assert min(got) >= da.LEVEL["noted"], (name, got)


@pytest.mark.parametrize("name", BLIND)
def test_the_known_blind_spots_stay_what_they_are_until_someone_decides_otherwise(name):
    assert max(levels(name)) <= da.LEVEL["noted"], name
