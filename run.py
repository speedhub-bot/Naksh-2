#!/usr/bin/env python3
"""Entry point for the Naksh Minecraft checker bot."""

from __future__ import annotations

import asyncio
import logging
import sys

from naksh.bot import BotApp
from naksh.logging_setup import init_logging


async def amain() -> None:
    init_logging(level=logging.INFO)
    log = logging.getLogger("naksh")
    log.info("Booting Naksh bot...")
    app = BotApp()
    await app.run()


def main() -> int:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        print("\nInterrupted, shutting down.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
