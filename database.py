import sqlite3
import threading

class Database:
    def __init__(self, db_name='bot_database.db'):
        self.db_name = db_name
        self.lock = threading.Lock()
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'pending',
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    user_id INTEGER PRIMARY KEY,
                    hit_notifications INTEGER DEFAULT 1,
                    result_type TEXT DEFAULT 'all',
                    file_format TEXT DEFAULT 'txt',
                    threads INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    user_id INTEGER PRIMARY KEY,
                    total_checked INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0,
                    bad INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Global stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_stats (
                    id INTEGER PRIMARY KEY CHECK (id = 0),
                    total_checked INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0,
                    bad INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0
                )
            ''')

            # Initialize global stats if not exists
            cursor.execute('INSERT OR IGNORE INTO global_stats (id) VALUES (0)')

            conn.commit()
            conn.close()

    def get_user(self, user_id):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            return user

    def add_user(self, user_id, username, full_name, role='pending'):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (user_id, username, full_name, role) VALUES (?, ?, ?, ?)',
                           (user_id, username, full_name, role))
            cursor.execute('INSERT OR IGNORE INTO settings (user_id) VALUES (?)', (user_id,))
            cursor.execute('INSERT OR IGNORE INTO stats (user_id) VALUES (?)', (user_id,))
            conn.commit()
            conn.close()

    def update_user_role(self, user_id, role):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
            conn.commit()
            conn.close()

    def get_settings(self, user_id):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO settings (user_id) VALUES (?)', (user_id,))
            conn.commit()
            cursor.execute('SELECT * FROM settings WHERE user_id = ?', (user_id,))
            settings = cursor.fetchone()
            conn.close()
            return settings

    def update_settings(self, user_id, **kwargs):
        allowed_keys = {'hit_notifications', 'result_type', 'file_format', 'threads'}
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            for key, value in kwargs.items():
                if key in allowed_keys:
                    cursor.execute(f'UPDATE settings SET {key} = ? WHERE user_id = ?', (value, user_id))
            conn.commit()
            conn.close()

    def update_stats(self, user_id, hits=0, bad=0, errors=0):
        total = hits + bad + errors
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE stats
                SET total_checked = total_checked + ?,
                    hits = hits + ?,
                    bad = bad + ?,
                    errors = errors + ?
                WHERE user_id = ?
            ''', (total, hits, bad, errors, user_id))

            cursor.execute('''
                UPDATE global_stats
                SET total_checked = total_checked + ?,
                    hits = hits + ?,
                    bad = bad + ?,
                    errors = errors + ?
                WHERE id = 0
            ''', (total, hits, bad, errors))

            conn.commit()
            conn.close()

    def get_user_stats(self, user_id):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO stats (user_id) VALUES (?)', (user_id,))
            conn.commit()
            cursor.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,))
            stats = cursor.fetchone()
            conn.close()
            return stats

    def get_global_stats(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM global_stats WHERE id = 0')
            stats = cursor.fetchone()
            conn.close()
            return stats

    def get_all_users(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, role FROM users')
            users = cursor.fetchall()
            conn.close()
            return users
