"""Read models for the console (docs/ENGINE-CONCEPT-NEEDS.md).

The console's pages are not lists of tables: they show a machine's health, a day's events, a ticket with what to do about
it. Each module here assembles one such view from what the combos record, scoped to the caller (the Super User sees the
organisation, an Admin their own department) and named the way the caller names people. Nothing here decides anything;
what the console can *do* goes through the combo's own handlers.

    feed      -- the audit trail as events: a kind, a plain sentence, the machine, the person; counts; export; live push
    machines  -- the fleet with each machine's health, and one machine's page
    rules     -- the standard: built-in locked rules and the Super User's patterns (never / follow / limit)
    automation -- the Automation and Actions pages: rules with how often they fired and how their runs ended, runs per day, a test on one machine
    deviations -- departures from a rule, with context, evidence and an outcome a person gives
    accountability -- recording them: triggers from the combos, watches on follow rules, limit counts
    marks     -- restricted marks: a file or folder marked where it is, kept to the machine or to its place
    issues    -- the tickets an Admin works: raised from what the system records, resolved when the cause goes
    plays     -- what can be done about an issue (the options, and doing them)
    overview  -- the Overviews' figures, the reports board, and the Super User's decisions
    registry  -- accounts, refused connections and blocked addresses, and a department's page
    rollout   -- the gate to the next version: who holds it back, who was left out, adoption, retrying
"""

from engine.console import (  # noqa: F401
    accountability,
    automation,
    deviations,
    feed,
    issues,
    machines,
    marks,
    overview,
    registry,
    rollout,
    rules,
)
