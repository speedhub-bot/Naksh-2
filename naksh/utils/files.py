"""Threadsafe file writers + zipping."""

from __future__ import annotations

import threading
import zipfile
from pathlib import Path
from typing import Iterable

_locks: dict[Path, threading.Lock] = {}
_master_lock = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    with _master_lock:
        lock = _locks.get(path)
        if lock is None:
            lock = threading.Lock()
            _locks[path] = lock
        return lock


def append_line(path: Path, line: str) -> None:
    """Append a single line to a file, creating it if needed.

    Uses a per-path lock so concurrent worker threads don't interleave writes.
    Caller is responsible for the trailing newline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        with open(path, "a", encoding="utf-8", buffering=1) as fh:
            fh.write(line if line.endswith("\n") else line + "\n")


def append_dedupe(path: Path, line: str) -> bool:
    """Append a line only if its trimmed form isn't already present.

    Returns True if the line was newly added.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    needle = line.strip()
    lock = _lock_for(path)
    with lock:
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                if needle and needle in fh.read():
                    return False
        with open(path, "a", encoding="utf-8", buffering=1) as fh:
            fh.write(line if line.endswith("\n") else line + "\n")
    return True


def zip_directory(src_dir: Path, zip_path: Path,
                  include_patterns: Iterable[str] = ("*.txt",)) -> Path:
    """Bundle every matching file in ``src_dir`` into ``zip_path``.

    Returns ``zip_path``.
    """
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pattern in include_patterns:
            for f in src_dir.rglob(pattern):
                if f.is_file():
                    zf.write(f, arcname=f.relative_to(src_dir))
    return zip_path
