"""The REAL local model, not a stand-in. Every other test scripts the model's answers, so on their own they cannot see the model itself stop
working: Detective's smoothing passed its tests while the real model handed back every paragraph unchanged (3 Nov 2026). These run whenever
the model file is on this machine, and skip with the reason where it is not. They are a floor, not a score: `scripts/llm_benchmark.py` is the
measurement. A failure here means the model, a prompt or llama.cpp changed in a way that matters.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.config import Settings
from engine.detective import labels, telling
from engine.llm import LocalLLM
from engine.task import llm_graph
from engine.task.llm_graph import FILE_INTENT_OPTIONS
from scripts.llm_benchmark import check
from scripts.llm_cases import TUNED
from scripts.llm_probe import PROBES

MODEL = Settings.llm_model_path or ""
try:
    import llama_cpp  # noqa: F401
    have_llama = True
except ImportError:
    have_llama = False

pytestmark = [pytest.mark.skipif(not Path(MODEL).is_file(), reason=f"the model is not here ({MODEL})"),
              pytest.mark.skipif(not have_llama, reason="llama-cpp-python is not installed")]


@pytest.fixture(scope="module")
def llm() -> LocalLLM:
    return LocalLLM("llamacpp", model_path=MODEL, timeout=120.0)


@pytest.mark.timeout(300)
async def test_the_model_tells_unmistakable_cases_apart_and_does_not_collapse(llm):
    right, said = 0, {"file": set(), "program": set()}
    for question, options, text, want in PROBES:
        got = await llm.choose(question, text, list(options))
        right += options.get(got) == want
        said["file" if options is FILE_INTENT_OPTIONS else "program"].add(got)
    assert right >= 7, f"{right}/8 on the probe (the 1.7B scores 8/8)"
    assert all(len(answers) > 1 for answers in said.values()), f"collapsed: {said}"        # one answer whatever the text: no signal at all


@pytest.mark.timeout(300)
async def test_the_task_graph_reads_tuned_cases_correctly_with_the_real_model(llm):
    for case in TUNED[:3]:
        structure = await llm_graph.populate(llm, case[0])
        assert check(case, structure) == [], case[0]


@pytest.mark.timeout(120)
async def test_detective_s_second_opinion_reads_a_plain_leak_as_something_not_nothing(llm):
    story = ["14:02  copied 212 files to E:/Backup", "14:03  plugged in a drive (E:)", "14:09  deleted archive.zip", "14:10  cleared the Security log"]
    assert await labels.second_opinion(llm, story) not in (None, "")


@pytest.mark.timeout(300)
async def test_smoothing_is_only_switched_on_when_the_model_really_rewrites(llm):
    """Off today: the 1.7B rewrote too little, too badly. Whoever switches LOCAL_SMOOTHING on must pass this with the model they chose."""
    if not telling.LOCAL_SMOOTHING:
        pytest.skip("the local model does not smooth")
    paragraphs = ["At [time1], [count2] files were copied to [folder3]. At [time4], a drive was plugged in ([drive5]).",
                  "At [time1], [program2] was started. At [time3], [program4] sent [amount5] out over the network.",
                  "At [time1], [file2] was renamed to [file3]. At [time4], who may open [file5] was changed."]
    rewritten = 0
    for p in paragraphs:
        said = await llm.rewrite(telling.INSTRUCTION, p, max_tokens=telling.SMOOTH_TOKENS)
        flat = " ".join((said or "").split())
        rewritten += flat != p and telling.checked(p, flat)
    assert rewritten >= 2, f"{rewritten}/3 paragraphs rewritten and checked"
