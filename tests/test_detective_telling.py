"""A case told in words (ENGINE-GAPS #15, way (a) and a smoothing pass): every fact comes from the case; the model may only change the words
between them, and its paragraph is used only when the check finds every fact still there and nothing added (engine/detective/telling.py)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from common.detective import Sig, sig_to_dict
from engine.detective import telling
from engine.detective.telling import Fact, checked, compose
from tests.conftest import requires_db
from tests.test_detective_engine import _leak

SKELETON = "At [time1], [count2] files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet."


def test_a_rewrite_is_used_only_when_every_fact_is_kept_with_its_own_and_nothing_is_added():
    assert checked(SKELETON, "At [time1], [count2] files were copied to [folder3]. Then at [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")
    # inside a sentence, facts of different kinds may change places; sentences may be merged
    assert checked(SKELETON, "[count2] files were copied to [folder3] at [time1]. A drive ([drive5]) was plugged in at [time4]. It has not left the machine yet.")
    assert checked(SKELETON, "[count2] files were copied to [folder3] at [time1], and at [time4] a drive was plugged in ([drive5]). It has not left the machine yet.")
    # a time moved to the other event, or the events told out of their order: refused
    assert not checked(SKELETON, "At [time4], [count2] files were copied to [folder3]. At [time1], a drive was plugged in ([drive5]). It has not left the machine yet.")
    assert not checked(SKELETON, "A drive was plugged in ([drive5]) at [time4], after [count2] files were copied to [folder3] at [time1]. It has not left the machine yet.")
    two = "At [time1], [file2] was copied to [folder3] and [file4] was copied to [folder5]."
    assert checked(two, "At [time1], [file2] went to [folder3] and [file4] went to [folder5].")
    assert not checked(two, "At [time1], [file2] was copied to [folder5] and [file4] was copied to [folder3].")             # two folders swapped
    assert not checked(SKELETON, "At [time1], [count2] files were copied. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")       # a fact dropped
    assert not checked(SKELETON, "At [time1], [count2] files were copied to [folder3] and [folder3]. At [time4], a drive ([drive5]). It has not left the machine yet.")       # one said twice
    assert not checked(SKELETON, "At [time1], 40 of [count2] files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")   # a number
    assert not checked(SKELETON, "At [time1], Kojo copied [count2] files to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")       # a name
    assert not checked(SKELETON, "At [time1], [count2] files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has left the machine.")              # "not" lost
    assert not checked(SKELETON, "At [time1], [count2] files were deliberately copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")
    assert not checked(SKELETON, "At [time1], [count2] files were copied to [folder3] in order to take them. At [time4], a drive was plugged in ([drive5]). It has not left yet.")
    assert not checked(SKELETON, "At [time1], [count2] files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet. " * 3)  # too long
    assert not checked(SKELETON, "At [file1], [count2] files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")  # a fact's kind changed
    assert not checked(SKELETON, "At [time1] **[count2]** files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]). It has not left the machine yet.")    # markup


def test_the_account_is_built_from_the_case_and_names_people_the_way_the_viewer_does():
    t0 = datetime(2026, 11, 2, 14, 2, tzinfo=timezone.utc)
    ev = [Sig(t0.timestamp() + i, 7, "copied", f"E:\\Out\\p{i}.xlsx", tags=frozenset({"restricted"})) for i in range(5)]
    ev.append(Sig(t0.timestamp() + 400, 7, "deleted", "C:\\Staging\\q3.zip"))
    findings = [{"graph": "bulk_copy", "behaviour": "exfiltration", "weight": 0.7, "at": t0, "summary": "5 restricted files went to a drive",
                 "innocent": "a backup the person was asked to make", "evidence": [sig_to_dict(e) for e in ev]}]
    case = {"pc_id": 7, "intent": "Taking data out", "not_yet": "Nothing has been erased yet.", "first_at": t0, "last_at": t0 + timedelta(seconds=400)}
    sessions = [{"occupant_account_id": 41, "occupied_via": "native"}, {"occupant_account_id": 9, "occupied_via": "traversal"}]
    t = compose(case, findings, sessions, "FIN-01")
    facts = [p for para in t.paragraphs for p in para if isinstance(p, Fact)]
    kinds = {(f.kind, f.text) for f in facts}
    assert ("machine", "FIN-01") in kinds and ("count", "5") in kinds and ("folder", "E:/Out") in kinds and ("file", "q3.zip") in kinds
    assert ("duration", "7 minutes") in kinds and ("intent", "Taking data out") in kinds and ("reason", "Nothing has been erased yet.") in kinds
    assert ("reason", "5 restricted files went to a drive") in kinds and ("reason", "a backup the person was asked to make") in kinds
    view = t.view({41: "Kojo", 9: "IT-01"})
    assert view["text"].startswith("Kojo was signed in on FIN-01 when this began") and "IT-01 had entered it from the console." in view["text"]
    assert "5 files were copied to E:/Out" in view["text"]
    assert t.skeletons()[1].startswith("At [time1], [count2] files were copied to [folder3], [tag4].")
    assert "[" not in view["text"] and view["smoothed"] is False and view["note"] == telling.NOTE
    marked = [p for p in view["paragraphs"][0] if p.get("kind") == "person"]
    assert [(p["text"], p["value"]) for p in marked] == [("Kojo", 41), ("IT-01", 9)]
    # another viewer, another name for the same person: the same account, their name
    assert t.view({41: "K. Mensah"})["text"].startswith("K. Mensah was signed in")
    # the fingerprint follows the case, not the viewer
    assert t.fingerprint() == compose(case, findings, sessions, "FIN-01").fingerprint()
    assert t.fingerprint() != compose({**case, "intent": "Gathering"}, findings, sessions, "FIN-01").fingerprint()


class Smoother:
    """A model that smooths the account: well on what happened, and adds a guess at a reason to the paragraph that says why it matters."""

    available = True

    def __init__(self) -> None:
        self.asked: list[str] = []

    async def choose(self, question, text, options):
        return None

    async def rewrite(self, instruction, text, *, max_tokens=320):
        self.asked.append(text)
        if text.startswith("Detective reads"):
            return text + " It was clearly done on purpose."
        return text.replace(". At ", ". Then at ")


@requires_db
async def test_the_case_is_told_in_words_and_the_model_may_change_only_the_words_between_the_facts(engine, org, connect):
    su = await connect("cid-su")

    class Away:
        available = False

    engine.llm = Away()                                                         # (not the real model, if this machine has one: it is slow)
    await _leak(engine, org["w1_pc"])
    (c,) = (await su.ok("detective.cases", {}))["cases"]
    told = (await su.ok("detective.case", {"case_id": c["id"]}))["telling"]
    assert told["smoothed"] is False and "telling" not in c
    assert told["text"].startswith("Nobody was signed in on FIN-01") and "were copied to" in told["text"] and "Detective reads this as Taking data out" in told["text"]
    assert any(p.get("kind") == "count" and p["text"] == "12" for para in told["paragraphs"] for p in para)

    engine.llm = Smoother()
    await su.ok("detective.case", {"case_id": c["id"]})                       # the account is not smoothed yet: the model is asked, in the background
    for _ in range(80):
        told = (await su.ok("detective.case", {"case_id": c["id"]}))["telling"]
        if told["smoothed"]:
            break
        await asyncio.sleep(0.1)
    assert told["smoothed"] is True and "Then at " in told["text"]
    assert "on purpose" not in told["text"] and "Detective reads this as Taking data out" in told["text"]     # that paragraph failed the check: the Engine's own
    assert any(p.get("kind") == "machine" and p["text"] == "FIN-01" for para in told["paragraphs"] for p in para)
    asked = len(engine.llm.asked)
    await su.ok("detective.case", {"case_id": c["id"]})
    await asyncio.sleep(0.2)
    assert len(engine.llm.asked) == asked                                       # kept: not asked again while the case is the same
