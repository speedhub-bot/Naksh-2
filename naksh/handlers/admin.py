"""Admin-only commands and panel."""

from __future__ import annotations

from pyrogram import filters, types
from pyrogram.types import InlineKeyboardButton as Btn
from pyrogram.types import InlineKeyboardMarkup as Markup

from ..config import SETTINGS
from ._common import is_admin, main_keyboard, safe_edit


def register(app) -> None:
    client = app.client
    db = app.db

    @client.on_callback_query(filters.regex(r"^admin_panel$"))
    async def cb_admin_panel(_, callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("Admins only.", show_alert=True)
            return
        gs = db.get_global_stats()
        users = db.list_users()
        pending = [u for u in users if u["role"] == "pending"]
        text = (
            "👑 <b>Admin Control Panel</b>\n"
            "━━━━━━━━━━━━━━\n"
            "🌍 <b>Global Stats:</b>\n"
            f"🔄 Total: {gs['total_checked']}\n"
            f"✅ Hits: {gs['hits']}\n"
            f"❌ Bad: {gs['bad']}\n"
            f"⚠️ 2FA: {gs['twofa']}\n"
            f"⚡ Errors: {gs['errors']}\n\n"
            f"👥 Users: <b>{len(users)}</b>  ⏳ Pending: <b>{len(pending)}</b>\n"
            "━━━━━━━━━━━━━━"
        )
        kb = Markup([
            [Btn("⏳ Manage Pending", callback_data="admin_pending")],
            [Btn("🚫 Ban a User", callback_data="admin_ban_menu")],
            [Btn("🔙 Back", callback_data="back_to_main")],
        ])
        await safe_edit(callback.message, text, reply_markup=kb)
        await callback.answer()

    @client.on_callback_query(filters.regex(r"^admin_pending$"))
    async def cb_admin_pending(_, callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("Admins only.", show_alert=True)
            return
        pending = [u for u in db.list_users() if u["role"] == "pending"]
        if not pending:
            await callback.answer("No pending requests.", show_alert=True)
            return
        rows = [[Btn(f"✅ {u['username'] or '—'} ({u['user_id']})",
                     callback_data=f"admin_authz:{u['user_id']}")]
                for u in pending]
        rows.append([Btn("🔙 Back", callback_data="admin_panel")])
        await safe_edit(
            callback.message,
            "⏳ <b>Pending Authorization Requests</b>\nClick a user to authorize.",
            reply_markup=Markup(rows),
        )
        await callback.answer()

    @client.on_callback_query(filters.regex(r"^admin_authz:(\d+)$"))
    async def cb_admin_authz(_, callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("Admins only.", show_alert=True)
            return
        target = int(callback.matches[0].group(1))
        db.update_user_role(target, "authorized")
        try:
            await client.send_message(
                target,
                "✅ Your access has been authorized! Send /start to begin.",
            )
        except Exception:
            pass
        await callback.answer(f"User {target} authorized.")
        await cb_admin_pending(_, callback)

    @client.on_message(filters.command("ban") & filters.private)
    async def cmd_ban(_, message: types.Message):
        if not is_admin(message.from_user.id):
            return
        parts = (message.text or "").split()
        if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
            await message.reply("Usage: <code>/ban &lt;user_id&gt;</code>")
            return
        target = int(parts[1])
        db.update_user_role(target, "banned")
        await message.reply(f"🚫 User <code>{target}</code> banned.")

    @client.on_message(filters.command("unban") & filters.private)
    async def cmd_unban(_, message: types.Message):
        if not is_admin(message.from_user.id):
            return
        parts = (message.text or "").split()
        if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
            await message.reply("Usage: <code>/unban &lt;user_id&gt;</code>")
            return
        target = int(parts[1])
        db.update_user_role(target, "authorized")
        await message.reply(f"✅ User <code>{target}</code> unbanned.")

    @client.on_callback_query(filters.regex(r"^admin_ban_menu$"))
    async def cb_admin_ban(_, callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("Admins only.", show_alert=True)
            return
        await callback.answer(
            "Use /ban <user_id> in chat to ban a user.\n"
            "Use /unban <user_id> to undo.",
            show_alert=True,
        )

    @client.on_message(filters.command("broadcast") & filters.private)
    async def cmd_broadcast(_, message: types.Message):
        if not is_admin(message.from_user.id):
            return
        if not message.reply_to_message:
            await message.reply(
                "Reply to the message you want to broadcast with /broadcast"
            )
            return
        users = db.list_users()
        ok = bad = 0
        for u in users:
            if u["role"] == "banned":
                continue
            try:
                await message.reply_to_message.copy(u["user_id"])
                ok += 1
            except Exception:
                bad += 1
        await message.reply(f"📣 Broadcast: {ok} delivered, {bad} failed.")
