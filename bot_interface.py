import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", ""))
except ValueError as exc:
    raise RuntimeError("ADMIN_ID environment variable must be an integer") from exc

if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID environment variable is required")

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

def get_main_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⚙️ Configure", callback_data="configure"))
    builder.row(types.InlineKeyboardButton(text="📊 My Stats", callback_data="my_stats"))
    builder.row(types.InlineKeyboardButton(text="👤 Profile", callback_data="profile"))
    if user_id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel"))
    return builder.as_markup()

async def require_authorized(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or user[3] not in {'authorized', 'admin'}:
        await callback.answer("You are not authorized to use this bot.", show_alert=True)
        return None
    return user

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        db.add_user(user_id, message.from_user.username, message.from_user.full_name)
        if user_id != ADMIN_ID:
            await bot.send_message(ADMIN_ID, f"🆕 New authorization request from @{message.from_user.username} ({user_id})")
            await message.reply("👋 Welcome! Your access is pending admin approval. Please wait for the admin to authorize you.")
            return
        else:
            db.update_user_role(user_id, 'admin')

    user = db.get_user(user_id)
    if user[3] == 'pending' and user_id != ADMIN_ID:
        await message.reply("⏳ Your access is still pending admin approval.")
        return
    if user[3] == 'banned':
        await message.reply("🚫 You are banned from using this bot.")
        return

    await message.reply(
        f"🚀 <b>Ultimate Minecraft Bot</b>\n\n"
        f"Welcome back, {message.from_user.first_name}!\n"
        f"Use the buttons below to manage your settings or start checking.\n\n"
        f"Credits: @akaza_isnt",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(user_id)
    )

@dp.callback_query(F.data == "profile")
async def process_profile(callback: types.CallbackQuery):
    user = await require_authorized(callback)
    if not user:
        return
    stats = db.get_user_stats(callback.from_user.id)
    text = (
        f"👤 <b>Your Profile</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"📛 Name: {user[2]}\n"
        f"👤 Username: @{user[1]}\n"
        f"🎖 Role: {user[3].capitalize()}\n"
        f"📅 Joined: {user[4]}\n\n"
        f"📊 <b>Lifetime Stats:</b>\n"
        f"✅ Hits: {stats[2]}\n"
        f"❌ Bad: {stats[3]}\n"
        f"⚠️ Errors: {stats[4]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Credits: @akaza_isnt"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard(callback.from_user.id))

@dp.callback_query(F.data == "my_stats")
async def process_my_stats(callback: types.CallbackQuery):
    if not await require_authorized(callback):
        return
    stats = db.get_user_stats(callback.from_user.id)
    text = (
        f"📊 <b>Your Statistics</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔄 Total Checked: {stats[1]}\n"
        f"✅ Hits: {stats[2]}\n"
        f"❌ Bad: {stats[3]}\n"
        f"⚠️ Errors: {stats[4]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Credits: @akaza_isnt"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard(callback.from_user.id))

@dp.callback_query(F.data == "configure")
async def process_configure(callback: types.CallbackQuery):
    user = await require_authorized(callback)
    if not user:
        return
    settings = db.get_settings(callback.from_user.id)
    max_threads = 5 if user[3] == 'admin' else 3
    threads = min(settings[4], max_threads)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"🔔 Notifications: {'ON' if settings[1] else 'OFF'}", callback_data="toggle_notif"))
    builder.row(types.InlineKeyboardButton(text=f"📄 Results: {settings[2].upper()}", callback_data="toggle_res_type"))
    builder.row(types.InlineKeyboardButton(text=f"📦 Format: {settings[3].upper()}", callback_data="toggle_format"))
    builder.row(types.InlineKeyboardButton(text=f"🧵 Threads: {threads}", callback_data="set_threads"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))

    await callback.message.edit_text("⚙️ <b>Bot Configuration</b>\nCustomize your experience below:", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "toggle_notif")
async def toggle_notif(callback: types.CallbackQuery):
    if not await require_authorized(callback):
        return
    settings = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, hit_notifications=1 if not settings[1] else 0)
    await process_configure(callback)

@dp.callback_query(F.data == "toggle_res_type")
async def toggle_res_type(callback: types.CallbackQuery):
    if not await require_authorized(callback):
        return
    settings = db.get_settings(callback.from_user.id)
    new_type = "hits" if settings[2] == "all" else "all"
    db.update_settings(callback.from_user.id, result_type=new_type)
    await process_configure(callback)

@dp.callback_query(F.data == "toggle_format")
async def toggle_format(callback: types.CallbackQuery):
    if not await require_authorized(callback):
        return
    settings = db.get_settings(callback.from_user.id)
    new_format = "zip" if settings[3] == "txt" else "txt"
    db.update_settings(callback.from_user.id, file_format=new_format)
    await process_configure(callback)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    if not await require_authorized(callback):
        return
    await callback.message.edit_text(
        f"🚀 <b>Ultimate Minecraft Bot</b>\n\nWelcome back, {callback.from_user.first_name}!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Admin access required.", show_alert=True)
        return

    global_stats = db.get_global_stats()
    users = db.get_all_users()
    pending = [u for u in users if u[2] == 'pending']

    text = (
        f"👑 <b>Admin Control Panel</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌍 <b>Global Stats:</b>\n"
        f"🔄 Total: {global_stats[1]}\n"
        f"✅ Hits: {global_stats[2]}\n"
        f"❌ Bad: {global_stats[3]}\n"
        f"⚠️ Errors: {global_stats[4]}\n\n"
        f"👥 <b>Users:</b> {len(users)}\n"
        f"⏳ Pending: {len(pending)}\n"
        f"━━━━━━━━━━━━━━\n"
    )

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⏳ Manage Pending", callback_data="manage_pending"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "manage_pending")
async def manage_pending(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Admin access required.", show_alert=True)
        return
    users = db.get_all_users()
    pending = [u for u in users if u[2] == 'pending']

    if not pending:
        await callback.answer("No pending requests.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for u in pending:
        builder.row(types.InlineKeyboardButton(text=f"✅ {u[1]} ({u[0]})", callback_data=f"auth_{u[0]}"))

    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel"))
    await callback.message.edit_text("⏳ <b>Pending Authorization Requests</b>\nClick a user to authorize them:", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("auth_"))
async def authorize_user(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Admin access required.", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    db.update_user_role(user_id, 'authorized')
    try:
        await bot.send_message(user_id, "✅ Your access has been authorized by the admin! /start to begin.")
    except:
        pass
    await callback.answer(f"User {user_id} authorized.")
    await manage_pending(callback)
