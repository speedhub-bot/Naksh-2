"""Tuned ``requests.Session`` factory used by every checker."""

from __future__ import annotations

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def build_session(*, with_proxies: bool = False, pool_size: int = 4) -> requests.Session:
    """Return a Session with retries on 429/5xx, sane headers, and TLS off-verify."""
    session = requests.Session()
    session.verify = False
    session.headers.update(DEFAULT_HEADERS)

    retry = Retry(
        total=3 if with_proxies else 2,
        connect=3 if with_proxies else 2,
        read=3 if with_proxies else 2,
        backoff_factor=0.5,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET", "POST")),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(
        pool_connections=pool_size, pool_maxsize=pool_size, max_retries=retry,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
