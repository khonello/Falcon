"""Operator Client core: the connection/state layer both the TUI (first) and the GUI (later)
sit on. No UI dependencies -- asyncio + stdlib + `protocol` only.

    connection  EngineConnection: NDJSON over TCP/TLS, handshake, request/response, pushes,
                reconnect with backoff
    state       ClientState: identity, occupied session, red banner, pulsing indicators --
                updated from pushes and responses, observable by the UI
    config      LocalConfig: last Engine address, client id, cached lists (a JSON file)
"""

from operator_client.core.config import LocalConfig  # noqa: F401
from operator_client.core.connection import (  # noqa: F401
    ConnectionError_,
    EngineConnection,
    EngineError,
)
from operator_client.core.state import ClientState, Indicator  # noqa: F401
