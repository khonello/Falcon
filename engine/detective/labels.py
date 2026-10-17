"""The local model, used the way Falcon uses it everywhere: narrow pick-from-a-list questions, never an open-ended verdict.

What is used, and what was measured and left out:

  * A SECOND OPINION on a case (used). Given the case as the story it tells, the model says which of a few descriptions fits best. It is shown beside the rules'
    own conclusion, labelled as the model's, and never changes a weight or a level.

  * LABELLING a rename as a disguise (measured, not used): see `looks_disguised`.

The second opinion is advisory, runs in the background so a person's file operation never waits for the model, is bounded (one at a time, a short queue, answers
cached by the model layer) and says nothing when the model is away. An unclear answer is "no opinion", never a guess. `scripts/detective_model_bench.py` measures
what each is worth with and without the model: that is how the rename labelling came out.
"""

from __future__ import annotations

from typing import Any

from common.detective import name_of

OPINION = {
    "taking data out": "Taking data out",
    "covering up": "Covering up",
    "hiding": "Hiding something",
    "gathering": "Gathering",
    "spying": "Spying",
    "wrecking": "Wrecking things",
    "nothing odd": "",
}


async def looks_disguised(llm: Any, old: str, new: str) -> bool | None:
    """Is the new name a picture, music, video or program name given to what was a document? Measured (scripts/detective_model_bench.py) and NOT used: once the
    rule knows the classes of file (document, picture, song, archive, system), it is right on every rename in the corpus; the model is right on fewer
    (6 of 8 held out) and adds false alarms. It stays here only so that measurement can be repeated with a bigger model."""
    if llm is None or not getattr(llm, "available", False) or not old or not new:
        return None
    return await llm.yes_no("A spreadsheet or document was renamed. Is the new file name a picture, music, video or program file name instead of a document name?",
                            f"Old name: {name_of(old)}\nNew name: {name_of(new)}")


FACTS = ("Pick the description that fits best. taking data out: files were gathered and copied off the computer. covering up: evidence was deleted or logs were cleared. "
         "hiding: files were made hard to find. wrecking: many files were destroyed or scrambled. spying: someone looked through things that are not part of their work. "
         "nothing odd: ordinary computer use.")


async def second_opinion(llm: Any, story: list[str]) -> str | None:
    """Which description fits what this case's evidence shows? Returns the model's reading in the rules' own words ("Taking data out"), "" for "nothing odd",
    or None when it has no opinion."""
    if llm is None or not getattr(llm, "available", False) or not story:
        return None
    text = "\n".join(story[:30])
    answer = await llm.choose(FACTS + " These things happened on one computer, in this order.", text, list(OPINION))
    return None if answer is None else OPINION[answer]
