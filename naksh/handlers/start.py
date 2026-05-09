"""/start, profile and stats commands."""

from __future__ import annotations

from pyrogram import filters, types

from ..config import SETTINGS
from ._common import is_admin, main_keyboard, safe_edit


def register(app) -> None:
    client = app.client
    db = app.db

    @client.on_message(filters.command("start") & filters.private)
    async def cmd_start(_, message: types.Message):
        user = message.from_user
        existing = db.get_user(user.id)
        if not existing:
            db.add_user(
                user.id, user.username,
                user.full_name or (user.first_name or "User"),
                role="admin" if is_admin(user.id) else "pending",
            )
            if not is_admin(user.id):
                try:
                    await client.send_message(
                        SETTINGS.admin_id,
                        f"🆕 New authorization request from "
                        f"@{user.username or '—'} ({user.id})",
                    )
                except Exception:
                    pass
                await message.reply(
                    "👋 <b>Welcome!</b>\n\n"
                    "Your access is pending admin approval. "
                    "Please wait for the admin to authorize you."
                )
                return

        existing = db.get_user(user.id)
        role = existing["role"]
        if role == "pending" and not is_admin(user.id):
            await message.reply("⏳ Your access is still pending admin approval.")
            return
        if role == "banned":
            await message.reply("🚫 You are banned from using this bot.")
            return

        await message.reply(
            "🚀 <b>Naksh Minecraft Checker</b>\n\n"
            f"Welcome back, <b>{user.first_name}</b>!\n\n"
            "📥 Drop a <code>.txt</code> combo file (email:pass per line) to start.\n"
            "🔌 Optional: send a proxy <code>.txt</code> right after — "
            "or send /noproxy to run without proxies.\n\n"
            "Use the buttons below to manage your settings.\n\n"
            "Credits: @akaza_isnt",
            reply_markup=main_keyboard(user.id),
        )

    @client.on_callback_query(filters.regex(r"^profile$"))
    async def cb_profile(_, callback: types.CallbackQuery):
        u = db.get_user(callback.from_user.id)
        s = db.get_user_stats(callback.from_user.id)
        if not u or not s:
            await callback.answer("No profile yet — send /start first.", show_alert=True)
            return
        text = (
            "👤 <b>Your Profile</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>{u['user_id']}</code>\n"
            f"📛 Name: {u['full_name']}\n"
            f"👤 Username: @{u['username'] or '—'}\n"
            f"🎖 Role: {u['role'].capitalize()}\n"
            f"📅 Joined: {u['joined_at']}\n\n"
            "📊 <b>Lifetime Stats:</b>\n"
            f"✅ Hits: {s['hits']}\n"
            f"❌ Bad: {s['bad']}\n"
            f"⚠️ 2FA: {s['twofa']}\n"
            f"⚡ Errors: {s['errors']}\n"
            "━━━━━━━━━━━━━━\n"
            "Credits: @akaza_isnt"
        )
        await safe_edit(callback.message, text,
                        reply_markup=main_keyboard(callback.from_user.id))
        await callback.answer()

    @client.on_callback_query(filters.regex(r"^my_stats$"))
    async def cb_stats(_, callback: types.CallbackQuery):
        s = db.get_user_stats(callback.from_user.id)
        if not s:
            await callback.answer("No stats yet — send /start first.", show_alert=True)
            return
        text = (
            "📊 <b>Your Statistics</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"🔄 Total Checked: {s['total_checked']}\n"
            f"✅ Hits: {s['hits']}\n"
            f"❌ Bad: {s['bad']}\n"
            f"⚠️ 2FA: {s['twofa']}\n"
            f"⚡ Errors: {s['errors']}\n"
            "━━━━━━━━━━━━━━\n"
            "Credits: @akaza_isnt"
        )
        await safe_edit(callback.message, text,
                        reply_markup=main_keyboard(callback.from_user.id))
        await callback.answer()

    @client.on_callback_query(filters.regex(r"^back_to_main$"))
    async def cb_back(_, callback: types.CallbackQuery):
        await safe_edit(
            callback.message,
            "🚀 <b>Naksh Minecraft Checker</b>\n\n"
            f"Welcome back, <b>{callback.from_user.first_name}</b>!",
            reply_markup=main_keyboard(callback.from_user.id),
        )
        await callback.answer()
