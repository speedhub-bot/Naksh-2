"""Logging configuration. One init call from ``run.py``."""

from __future__ import annotations

import logging
import sys


def init_logging(level: int = logging.INFO) -> None:
    fmt = "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet noisy libraries
    for name in ("pyrogram", "pyrogram.session", "pyrogram.connection",
                 "pyrogram.dispatcher", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)
