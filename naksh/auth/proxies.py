"""Proxy parsing and rotation.

Supports the formats encountered in real combo dumps:

* ``host:port``
* ``host:port:user:pass``
* ``user:pass:host:port``
* ``user:pass@host:port``
* ``scheme://host:port`` (with or without auth)
* ``host port user pass`` (whitespace or pipe separated)
"""

from __future__ import annotations

import random
import re
import threading
from typing import Iterable, Optional

ProxyDict = dict[str, str]

_SCHEMES = ("http", "https", "socks4", "socks5")
_SEP = re.compile(r"[:|@\s]+")


def parse_proxy(raw: str) -> Optional[ProxyDict]:
    """Parse one proxy string into a ``requests``-compatible mapping."""
    s = raw.strip()
    if not s:
        return None

    scheme = "http"
    if "://" in s:
        head, s = s.split("://", 1)
        for sch in _SCHEMES:
            if sch in head.lower():
                scheme = sch
                break

    if "@" in s:
        creds, addr = s.rsplit("@", 1)
        cred_parts = [p for p in _SEP.split(creds) if p]
        addr_parts = [p for p in _SEP.split(addr) if p]
        if len(cred_parts) >= 2 and len(addr_parts) >= 2:
            user, password = cred_parts[0], cred_parts[1]
            host, port = addr_parts[0], addr_parts[1]
            url = f"{scheme}://{user}:{password}@{host}:{port}"
            return {"http": url, "https": url}

    parts = [p for p in _SEP.split(s) if p]
    if len(parts) == 2 and parts[1].isdigit():
        url = f"{scheme}://{parts[0]}:{parts[1]}"
        return {"http": url, "https": url}
    if len(parts) == 4:
        # heuristic: numeric segment is the port
        if parts[1].isdigit() and not parts[3].isdigit():
            host, port, user, password = parts
        elif parts[3].isdigit() and not parts[1].isdigit():
            user, password, host, port = parts
        else:
            host, port, user, password = parts
        url = f"{scheme}://{user}:{password}@{host}:{port}"
        return {"http": url, "https": url}
    return None


class ProxyPool:
    """Thread-safe proxy rotator with per-proxy ban tracking."""

    def __init__(self, proxies: Iterable[str]):
        parsed = [p for p in (parse_proxy(line) for line in proxies) if p]
        self._proxies: list[ProxyDict] = parsed
        self._banned: set[str] = set()
        self._lock = threading.Lock()

    def __bool__(self) -> bool:
        return bool(self._proxies)

    def __len__(self) -> int:
        with self._lock:
            return len([p for p in self._proxies if p["http"] not in self._banned])

    def get(self) -> Optional[ProxyDict]:
        with self._lock:
            available = [p for p in self._proxies if p["http"] not in self._banned]
            if not available:
                self._banned.clear()  # reset all once exhausted
                available = self._proxies
            return random.choice(available) if available else None

    def ban(self, proxy: ProxyDict | None) -> None:
        if not proxy:
            return
        with self._lock:
            self._banned.add(proxy["http"])
