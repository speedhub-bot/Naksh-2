"""Pyrogram handler registration."""

from __future__ import annotations

from . import admin, dashboard, settings, start, upload


def register_all(app) -> None:
    """Wire every handler module to the shared :class:`BotApp` instance."""
    start.register(app)
    settings.register(app)
    upload.register(app)
    admin.register(app)
    dashboard.register(app)
