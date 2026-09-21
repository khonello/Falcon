"""Entry point: `python -m engine`."""

import asyncio
import logging

from engine.config import Settings
from engine.server import Engine


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    asyncio.run(Engine(settings).run())


if __name__ == "__main__":
    main()
