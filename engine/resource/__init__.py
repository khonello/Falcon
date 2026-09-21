"""Resource & Assistance (resource-assistance-combo.md; spec 7.4).

The resource folder structure IS the access policy, grounded in the Global File Index.

    resource   -- tiers, access tags, restricted-file tracking by hash, violation reporting
    assistance -- Assistance file search, Ping, Message Channel (one-message-per-turn, superior
                  closes), Listeners (asymmetric awareness, full audit)
"""

from engine.resource import assistance, resource  # noqa: F401
