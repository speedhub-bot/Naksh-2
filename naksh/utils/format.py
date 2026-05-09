"""Tiny formatting helpers used across the bot."""

from __future__ import annotations

import re

_DECORATIVE_SYMBOLS_RE = re.compile(
    "[✪✿✦⚚➎★☆◆◇■□●○◎☀☁☂☃☄☾☽♛♕♚♔♤♡♢♧♠♥♦♣⚜⚡✨❖⬥⬦⬧⬨⬩⭐🌟🟊]+"
)


def clean_name(name: str | None) -> str:
    if not name:
        return ""
    return _DECORATIVE_SYMBOLS_RE.sub("", str(name)).strip()


def format_number(num: float | int | str | None) -> str:
    try:
        n = float(num) if num is not None else 0.0
    except (TypeError, ValueError):
        return "0"
    if n < 0:
        return "0"
    for thresh, suffix, prec in ((1e9, "B", 2), (1e6, "M", 2), (1e3, "K", 1)):
        if n >= thresh:
            return f"{n / thresh:.{prec}f}{suffix}"
    return str(int(n))


def format_seconds(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def progress_bar(percent: float, width: int = 15) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int(width * percent / 100)
    return "🟩" * filled + "⬜" * (width - filled)


def mask_password(password: str) -> str:
    if len(password) > 4:
        return password[:2] + "*" * (len(password) - 4) + password[-2:]
    return "*" * len(password)
