"""Asyncio job queue with a fixed-size worker pool.

The bot owns one :class:`JobQueue` per process. Each job runs the synchronous
:class:`CheckEngine.start` in a thread executor while a parallel coroutine
periodically edits the user-facing progress message. Jobs queue up if more are
submitted than can run concurrently.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from ..config import SETTINGS

log = logging.getLogger(__name__)


@dataclass
class Job:
    user_id: int
    coro: Callable[[], Awaitable[None]]
    label: str = ""


class JobQueue:
    def __init__(self, concurrency: int | None = None) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._concurrency = concurrency or SETTINGS.max_concurrent_jobs
        self._tasks: list[asyncio.Task] = []
        self._running: int = 0
        self._stopped = asyncio.Event()
        self.started_at = time.time()

    @property
    def waiting(self) -> int:
        return self._queue.qsize()

    @property
    def running(self) -> int:
        return self._running

    async def submit(self, job: Job) -> int:
        """Enqueue a job and return its (estimated) queue position."""
        await self._queue.put(job)
        return self._queue.qsize() + self._running

    async def start(self) -> None:
        for i in range(self._concurrency):
            self._tasks.append(asyncio.create_task(self._worker(i)))
        log.info("Queue started with %s workers", self._concurrency)

    async def stop(self) -> None:
        self._stopped.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    async def _worker(self, idx: int) -> None:
        while not self._stopped.is_set():
            try:
                job: Job = await self._queue.get()
            except asyncio.CancelledError:
                return
            self._running += 1
            try:
                await job.coro()
            except Exception:
                log.exception("Job %s crashed", job.label or job.user_id)
            finally:
                self._running -= 1
                self._queue.task_done()
