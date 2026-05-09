"""Pyrogram client bootstrap and handler wiring."""

from __future__ import annotations

import asyncio
import logging

from pyrogram import Client
from pyrogram.enums import ParseMode

from .config import SETTINGS
from .core.queue import JobQueue
from .db import Database

log = logging.getLogger(__name__)


def build_client() -> Client:
    return Client(
        name="naksh-bot",
        api_id=SETTINGS.api_id,
        api_hash=SETTINGS.api_hash,
        bot_token=SETTINGS.bot_token,
        parse_mode=ParseMode.HTML,
        workdir=str(SETTINGS.sessions_dir),
        in_memory=False,
    )


class BotApp:
    """Holds every long-lived bot-process singleton."""

    def __init__(self) -> None:
        self.client = build_client()
        self.db = Database()
        self.queue = JobQueue()
        # Maps user_id -> list of pending combos waiting for proxy/no-proxy
        self.pending_combos: dict[int, list[str]] = {}
        # Set of user_ids currently in "type a number of threads" prompt
        self.awaiting_threads: set[int] = set()

    async def run(self) -> None:
        await self.queue.start()
        try:
            from .handlers import register_all
            register_all(self)
            log.info("Starting Pyrogram client...")
            await self.client.start()
            log.info("Bot is online. Admin id=%s", SETTINGS.admin_id)
            await self._make_admin()
            # Keep alive until cancelled
            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except asyncio.CancelledError:
                pass
        finally:
            log.info("Shutting down...")
            try:
                await self.client.stop()
            except Exception:
                pass
            await self.queue.stop()

    async def _make_admin(self) -> None:
        admin_id = SETTINGS.admin_id
        user = self.db.get_user(admin_id)
        if not user:
            self.db.add_user(admin_id, None, "admin", role="admin")
        elif user["role"] != "admin":
            self.db.update_user_role(admin_id, "admin")
