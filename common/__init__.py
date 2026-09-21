"""Code bundled by more than one deployable package (Engine, Operator Client, Worker Client).

Stdlib only. Anything here must behave identically wherever it runs -- e.g. Custom Action
validation, which the Operator Client runs before sending and the Engine and Worker Client run
again on arrival.
"""
