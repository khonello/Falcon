"""Resource & Assistance (resource-assistance-combo.md; spec 7.4).

The resource folder structure IS the access policy, grounded in the Global File Index.

    journey    -- a file's journey: where its content has been and what was done about it, in order
    resource   -- tiers, access tags, restricted-file tracking by hash, violation reporting
    conversations -- an Admin's conversations in version 1: two people, or every Admin; no request first
    assistance -- Assistance file search, Ping, Message Channel (one-message-per-turn, superior
                  closes)
"""

from engine.resource import (  # noqa: F401
    assistance,
    chatfiles,
    conversations,
    journey,
    private,
    resource,
)
