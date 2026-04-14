import os
import asyncio
import threading
from aiogram import types, F
from aiogram.filters import Command
from database import Database
from checker_engine import CheckerEngine
from bot_interface import dp, bot, ADMIN_ID, get_main_keyboard

db = Database()
queue = asyncio.Queue()
running_checks = 0
MAX_CONCURRENT = 3
queue_lock = asyncio.Lock()
temp_combos = {}
waiting_for_threads = set()

class CheckTask:
    def __init__(self, user_id, combo_data, proxy_data, message):
        self.user_id = user_id
        self.combo_data = combo_data
        self.proxy_data = proxy_data
        self.message = message

async def worker():
    global running_checks
    while True:
        task = await queue.get()
        async with queue_lock:
            running_checks += 1

        try:
            await run_checker(task)
        except Exception as e:
            print(f"Error in worker: {e}")
        finally:
            async with queue_lock:
                running_checks -= 1
            queue.task_done()

async def run_checker(task):
    user_settings = db.get_settings(task.user_id)
    user = db.get_user(task.user_id)
    is_admin = user[3] == 'admin'
    max_threads = 50 if is_admin else 25
    threads = min(user_settings[4], max_threads)

    loop = asyncio.get_event_loop()
    engine = CheckerEngine(
        task.user_id,
        task.combo_data.copy(),
        task.proxy_data,
        threads,
        user_settings,
        db,
        bot,
        loop
    )

    ui_task = asyncio.create_task(engine.update_ui(task.message))
    await loop.run_in_executor(None, engine.start)
    engine.is_running = False
    await ui_task

    final_text = (
        f"🏁 <b>Check Completed!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Hits: {engine.hits}\n"
        f"❌ Bad: {engine.bad}\n"
        f"⚠️ Errors: {engine.errors}\n"
        f"🔄 Total: {engine.total}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Credits: @akaza_isnt"
    )

    await task.message.edit_text(final_text, parse_mode="HTML")

    if user_settings[3] == 'zip':
        zip_path = engine.get_results_zip()
        await bot.send_document(task.user_id, types.FSInputFile(zip_path), caption="📦 Your results (ZIP)")
    else:
        # Respect "hits" or "all" result types
        hits_file = f"{engine.results_dir}/hits.txt"
        if os.path.exists(hits_file) and os.path.getsize(hits_file) > 0:
            await bot.send_document(task.user_id, types.FSInputFile(hits_file), caption="✅ Hits found")

        if user_settings[2] == 'all':
            bad_file = f"{engine.results_dir}/bad.txt"
            if os.path.exists(bad_file) and os.path.getsize(bad_file) > 0:
                await bot.send_document(task.user_id, types.FSInputFile(bad_file), caption="❌ Bad accounts")

            err_file = f"{engine.results_dir}/errors.txt"
            if os.path.exists(err_file) and os.path.getsize(err_file) > 0:
                await bot.send_document(task.user_id, types.FSInputFile(err_file), caption="⚠️ Errors")

@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user or user[3] not in ['authorized', 'admin']:
        await message.reply("🚫 You are not authorized to use the checker.")
        return

    file_name = message.document.file_name.lower()

    if "proxy" in file_name or (message.caption and "proxy" in message.caption.lower()):
        if user_id not in temp_combos:
            await message.reply("⚠️ Please upload combos first.")
            return

        file = await bot.get_file(message.document.file_id)
        content = (await bot.download_file(file.file_path)).read().decode('utf-8', errors='ignore').splitlines()
        proxies = [p.strip() for p in content if p.strip()]

        combos = temp_combos.pop(user_id)
        await add_to_queue(user_id, combos, proxies, message)
    else:
        if not file_name.endswith('.txt'):
            await message.reply("⚠️ Please upload a .txt file containing combos (email:pass).")
            return

        file = await bot.get_file(message.document.file_id)
        content = (await bot.download_file(file.file_path)).read().decode('utf-8', errors='ignore').splitlines()
        combos = [c.strip() for c in content if ":" in c]

        if not combos:
            await message.reply("⚠️ No valid combos found in the file.")
            return

        temp_combos[user_id] = combos
        await message.reply("🔗 Send your proxy file (.txt) or type /noproxy to continue without proxies.")

@dp.message(Command("noproxy"))
async def no_proxy(message: types.Message):
    user_id = message.from_user.id
    if user_id not in temp_combos:
        await message.reply("⚠️ Please upload combos first.")
        return

    combos = temp_combos.pop(user_id)
    await add_to_queue(user_id, combos, [], message)

async def add_to_queue(user_id, combos, proxies, message):
    status_msg = await message.reply(f"⌛ Added to queue. Position: {queue.qsize() + 1}")
    task = CheckTask(user_id, combos, proxies, status_msg)
    await queue.put(task)

@dp.callback_query(F.data == "set_threads")
async def set_threads_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text("🧵 <b>Set Threads</b>\nPlease type the number of threads you want to use (Max 50 for Admin, 25 for others).", parse_mode="HTML")
    waiting_for_threads.add(callback.from_user.id)

@dp.message(lambda message: message.from_user.id in waiting_for_threads)
async def handle_set_threads(message: types.Message):
    user_id = message.from_user.id
    waiting_for_threads.remove(user_id)
    try:
        val = int(message.text)
        if val < 1: val = 1
        user = db.get_user(user_id)
        max_val = 50 if user[3] == 'admin' else 25
        if val > max_val: val = max_val

        db.update_settings(user_id, threads=val)
        await message.reply(f"✅ Threads set to {val}.", reply_markup=get_main_keyboard(user_id))
    except ValueError:
        await message.reply("⚠️ Invalid number. Please try again.")

async def main():
    for _ in range(MAX_CONCURRENT):
        asyncio.create_task(worker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
