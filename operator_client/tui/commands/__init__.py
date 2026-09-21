"""Importing this package registers every command with `operator_client.tui.shell.registry`."""

from operator_client.tui.commands import (  # noqa: F401
    assistance,
    control,
    flow,
    hierarchy,
    reports,
    resource,
    system,
    task,
    updates,
)
