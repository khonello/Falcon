"""Resource & Assistance (resource-assistance-combo.md; spec 7.4).

The resource folder structure IS the access policy, grounded in the Global File Index.

    journey    -- a file's journey: where its content has been and what was done about it, in order
    resource   -- tiers, access tags, restricted-file tracking by hash, violation reporting
    assistance -- Assistance file search, Ping, Message Channel (one-message-per-turn, superior
                  closes), Listeners (asymmetric awareness, full audit)
"""

from engine.resource import assistance, journey, resource  # noqa: F401
