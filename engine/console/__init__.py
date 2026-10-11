"""Read models for the console (docs/ENGINE-CONCEPT-NEEDS.md).

The console's pages are not lists of tables: they show a machine's health, a day's events, a ticket with what to do about
it. Each module here assembles one such view from what the combos record, scoped to the caller (the Super User sees the
organisation, an Admin their own department) and named the way the caller names people. Nothing here decides anything;
what the console can *do* goes through the combo's own handlers.

    feed      -- the audit trail as events: a kind, a plain sentence, the machine, the person; counts; export; live push
    machines  -- the fleet with each machine's health, and one machine's page
    issues    -- the tickets an Admin works: raised from what the system records, resolved when the cause goes
    plays     -- what can be done about an issue (the options, and doing them)
"""

from engine.console import feed, issues, machines  # noqa: F401
