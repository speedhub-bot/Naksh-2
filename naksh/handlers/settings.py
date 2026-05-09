"""Per-user configuration menu."""

from __future__ import annotations

from pyrogram import filters, types
from pyrogram.types import InlineKeyboardButton as Btn
from pyrogram.types import InlineKeyboardMarkup as Markup

from ..config import SETTINGS
from ._common import is_admin, main_keyboard, safe_edit


def _settings_keyboard(s) -> Markup:
    return Markup([
        [Btn(f"🔔 Notifications: {'ON' if s['hit_notifications'] else 'OFF'}",
             callback_data="cfg_toggle_notif")],
        [Btn(f"📄 Result type: {s['result_type'].upper()}",
             callback_data="cfg_toggle_result")],
        [Btn(f"📦 Format: {s['file_format'].upper()}",
             callback_data="cfg_toggle_format")],
        [Btn(f"🧵 Threads: {s['threads']}", callback_data="cfg_set_threads")],
        [Btn("🔙 Back", callback_data="back_to_main")],
    ])


def register(app) -> None:
    client = app.client
    db = app.db

    @client.on_callback_query(filters.regex(r"^configure$"))
    async def cb_configure(_, callback: types.CallbackQuery):
        s = db.get_settings(callback.from_user.id)
        if not s:
            await callback.answer("Send /start first.", show_alert=True)
            return
        await safe_edit(
            callback.message,
            "⚙️ <b>Bot Configuration</b>\nCustomise your checker below:",
            reply_markup=_settings_keyboard(s),
        )
        await callback.answer()

    @client.on_callback_query(filters.regex(r"^cfg_toggle_notif$"))
    async def cb_toggle_notif(_, callback: types.CallbackQuery):
        s = db.get_settings(callback.from_user.id)
        db.update_settings(callback.from_user.id,
                           hit_notifications=0 if s["hit_notifications"] else 1)
        await cb_configure(_, callback)

    @client.on_callback_query(filters.regex(r"^cfg_toggle_result$"))
    async def cb_toggle_result(_, callback: types.CallbackQuery):
        s = db.get_settings(callback.from_user.id)
        new = "all" if s["result_type"] == "hits" else "hits"
        db.update_settings(callback.from_user.id, result_type=new)
        await cb_configure(_, callback)

    @client.on_callback_query(filters.regex(r"^cfg_toggle_format$"))
    async def cb_toggle_format(_, callback: types.CallbackQuery):
        s = db.get_settings(callback.from_user.id)
        new = "txt" if s["file_format"] == "zip" else "zip"
        db.update_settings(callback.from_user.id, file_format=new)
        await cb_configure(_, callback)

    @client.on_callback_query(filters.regex(r"^cfg_set_threads$"))
    async def cb_set_threads(_, callback: types.CallbackQuery):
        max_t = SETTINGS.threads_max_admin if is_admin(callback.from_user.id) \
            else SETTINGS.threads_max_user
        await safe_edit(
            callback.message,
            f"🧵 <b>Set Threads</b>\nReply with a number between "
            f"<b>1</b> and <b>{max_t}</b>.\n\n"
            "Or press Cancel to keep the current value.",
            reply_markup=Markup([[Btn("❌ Cancel", callback_data="back_to_main")]]),
        )
        app.awaiting_threads.add(callback.from_user.id)
        await callback.answer()

    @client.on_message(
        filters.private & filters.text & ~filters.command(["start", "noproxy", "cancel"])
    )
    async def msg_dispatch(_, message: types.Message):
        if message.from_user.id not in app.awaiting_threads:
            return  # let other handlers take it
        app.awaiting_threads.discard(message.from_user.id)
        try:
            val = int(message.text.strip())
        except ValueError:
            await message.reply("⚠️ Not a number. Try /start to reopen the menu.")
            return
        max_t = (SETTINGS.threads_max_admin if is_admin(message.from_user.id)
                 else SETTINGS.threads_max_user)
        val = max(1, min(max_t, val))
        db.update_settings(message.from_user.id, threads=val)
        await message.reply(
            f"✅ Threads set to <b>{val}</b>.",
            reply_markup=main_keyboard(message.from_user.id),
        )
