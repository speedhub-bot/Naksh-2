"""Shared helpers for handler modules."""

from __future__ import annotations

from pyrogram import types
from pyrogram.types import InlineKeyboardButton as Btn
from pyrogram.types import InlineKeyboardMarkup as Markup

from ..config import SETTINGS


def is_admin(user_id: int) -> bool:
    return user_id == SETTINGS.admin_id


def main_keyboard(user_id: int) -> Markup:
    rows = [
        [Btn("⚙️ Configure", callback_data="configure")],
        [Btn("📊 My Stats", callback_data="my_stats")],
        [Btn("👤 Profile", callback_data="profile")],
    ]
    if is_admin(user_id):
        rows.append([Btn("👑 Admin Panel", callback_data="admin_panel")])
    return Markup(rows)


async def safe_edit(message: types.Message, text: str, **kw) -> None:
    """Edit a message, swallowing the 'message is not modified' / FloodWait noise."""
    try:
        await message.edit_text(text, **kw)
    except Exception:
        pass


async def reply_unauthorized(message: types.Message, role: str) -> None:
    if role == "pending":
        await message.reply("⏳ Your access is still pending admin approval.")
    elif role == "banned":
        await message.reply("🚫 You are banned from using this bot.")
    else:
        await message.reply("🚫 You are not authorized to use the checker.")
