"""Sqlite-backed persistence layer.

All access goes through :class:`Database`. Every read returns
``sqlite3.Row`` objects so callers use ``row["column"]`` instead of fragile
positional indexing. A single :class:`threading.Lock` serialises writers since
the bot is mostly I/O-bound and the workload is light.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import SETTINGS


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    role        TEXT NOT NULL DEFAULT 'pending'  -- pending|authorized|admin|banned
                CHECK (role IN ('pending','authorized','admin','banned')),
    joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    user_id           INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    hit_notifications INTEGER NOT NULL DEFAULT 1,
    result_type       TEXT    NOT NULL DEFAULT 'hits' CHECK (result_type IN ('hits','all')),
    file_format       TEXT    NOT NULL DEFAULT 'zip'  CHECK (file_format IN ('txt','zip')),
    threads           INTEGER NOT NULL DEFAULT 25
);

CREATE TABLE IF NOT EXISTS stats (
    user_id       INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    total_checked INTEGER NOT NULL DEFAULT 0,
    hits          INTEGER NOT NULL DEFAULT 0,
    bad           INTEGER NOT NULL DEFAULT 0,
    twofa         INTEGER NOT NULL DEFAULT 0,
    errors        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS global_stats (
    id            INTEGER PRIMARY KEY CHECK (id = 0),
    total_checked INTEGER NOT NULL DEFAULT 0,
    hits          INTEGER NOT NULL DEFAULT 0,
    bad           INTEGER NOT NULL DEFAULT 0,
    twofa         INTEGER NOT NULL DEFAULT 0,
    errors        INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO global_stats (id) VALUES (0);
"""


class Database:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or SETTINGS.db_path)
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = sqlite3.connect(self.path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    # ---- users ----------------------------------------------------------
    def get_user(self, user_id: int) -> sqlite3.Row | None:
        with self._conn() as c:
            return c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def add_user(self, user_id: int, username: str | None, full_name: str,
                 role: str = "pending") -> None:
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, role) "
                      "VALUES (?,?,?,?)", (user_id, username, full_name, role))
            c.execute("INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (user_id,))
            c.execute("INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))

    def update_user_role(self, user_id: int, role: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))

    def list_users(self) -> list[sqlite3.Row]:
        with self._conn() as c:
            return list(c.execute("SELECT user_id, username, role FROM users"))

    # ---- settings -------------------------------------------------------
    def get_settings(self, user_id: int) -> sqlite3.Row | None:
        with self._conn() as c:
            return c.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,)).fetchone()

    def update_settings(self, user_id: int, **fields) -> None:
        if not fields:
            return
        allowed = {"hit_notifications", "result_type", "file_format", "threads"}
        cols = [k for k in fields if k in allowed]
        if not cols:
            return
        sets = ", ".join(f"{k} = ?" for k in cols)
        params = [fields[k] for k in cols] + [user_id]
        with self._conn() as c:
            c.execute(f"UPDATE settings SET {sets} WHERE user_id = ?", params)

    # ---- stats ----------------------------------------------------------
    def add_stats(self, user_id: int, *, hits: int = 0, bad: int = 0,
                  twofa: int = 0, errors: int = 0) -> None:
        total = hits + bad + twofa + errors
        with self._conn() as c:
            c.execute(
                "UPDATE stats SET total_checked = total_checked + ?, "
                "hits = hits + ?, bad = bad + ?, twofa = twofa + ?, errors = errors + ? "
                "WHERE user_id = ?",
                (total, hits, bad, twofa, errors, user_id),
            )
            c.execute(
                "UPDATE global_stats SET total_checked = total_checked + ?, "
                "hits = hits + ?, bad = bad + ?, twofa = twofa + ?, errors = errors + ? "
                "WHERE id = 0",
                (total, hits, bad, twofa, errors),
            )

    def get_user_stats(self, user_id: int) -> sqlite3.Row | None:
        with self._conn() as c:
            return c.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,)).fetchone()

    def get_global_stats(self) -> sqlite3.Row | None:
        with self._conn() as c:
            return c.execute("SELECT * FROM global_stats WHERE id = 0").fetchone()
