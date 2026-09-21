"""Flow (flow-natural-combo.md; spec 7.3).

A one-directional sync pipeline: Source -> stages (Branch / Transformation / Categorization)
-> Destination(s). Never conflicts because it never flows back.

    flows -- creation (consent, pre-flight collision check, cycle prevention), edit, pause,
             resume, status, failure suggestions
    sync  -- change detection from the Global File Index event stream (polling fallback),
             write attribution, conflict handling (-modified rename), propagation
"""

from engine.flow import flows, sync  # noqa: F401
