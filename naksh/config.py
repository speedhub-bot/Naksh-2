"""Centralised configuration with safe public defaults.

Every value can be overridden by an environment variable of the same name.
The defaults are the public Telegram Desktop ``api_id`` / ``api_hash`` plus the
existing bot token, so the project runs without an .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # Telegram
    bot_token: str = _env("BOT_TOKEN", "8459126546:AAHN9oT3OzcM74yHPINr7mjJWHTyYbvkn_g")
    api_id: int = _env_int("API_ID", 2040)
    api_hash: str = _env("API_HASH", "b18441a1ff607e10a989891a5462e627")
    admin_id: int = _env_int("ADMIN_ID", 5944410248)

    # Optional third-party keys (None = the relevant capture is skipped)
    donut_api_key: str = _env("DONUT_API_KEY", "")
    hypixel_api_key: str = _env("HYPIXEL_API_KEY", "")

    # Feature toggles
    hypixel_ban_check: bool = _env("HYPIXEL_BAN_CHECK", "1") not in ("0", "false", "no")

    # Concurrency & limits
    max_concurrent_jobs: int = _env_int("MAX_CONCURRENT_JOBS", 2)
    threads_default: int = _env_int("THREADS_DEFAULT", 25)
    threads_max_user: int = _env_int("THREADS_MAX_USER", 25)
    threads_max_admin: int = _env_int("THREADS_MAX_ADMIN", 50)
    max_combo_size_mb: int = _env_int("MAX_COMBO_SIZE_MB", 256)
    request_timeout: int = _env_int("REQUEST_TIMEOUT", 10)
    max_retries: int = _env_int("MAX_RETRIES", 3)
    progress_edit_interval: float = float(_env("PROGRESS_EDIT_INTERVAL", "5"))

    # Storage
    base_dir: Path = Path(_env("BASE_DIR", str(Path.cwd())))
    db_path: Path = Path(_env("DB_PATH", "naksh_bot.db"))
    results_dir: Path = Path(_env("RESULTS_DIR", "results"))
    sessions_dir: Path = Path(_env("SESSIONS_DIR", "sessions"))


SETTINGS = Settings()
SETTINGS.results_dir.mkdir(parents=True, exist_ok=True)
SETTINGS.sessions_dir.mkdir(parents=True, exist_ok=True)
