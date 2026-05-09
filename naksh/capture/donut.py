"""DonutSMP stats capture.

Gated on ``DONUT_API_KEY`` — without a key the public API now returns 401, so
calling it just wastes time and pollutes logs. When no key is configured the
fetcher is a no-op.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests

from ..config import SETTINGS

log = logging.getLogger(__name__)
DONUT_API_URL = "https://api.donutsmp.net/v1/player/"


def is_enabled() -> bool:
    return bool(SETTINGS.donut_api_key)


def fetch_donut(username: str) -> Optional[dict[str, Any]]:
    if not username or username == "N/A":
        return None
    if not is_enabled():
        return None
    try:
        r = requests.get(
            DONUT_API_URL + username,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Authorization": f"Bearer {SETTINGS.donut_api_key}",
            },
            timeout=SETTINGS.request_timeout,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, dict) or "result" not in data:
            return None
        result = data["result"] if isinstance(data["result"], dict) else data
        return {
            "money": result.get("money"),
            "shards": result.get("shards"),
            "kills": result.get("kills"),
            "deaths": result.get("deaths"),
            "playtime": result.get("playtime"),
            "rank": result.get("rank"),
            "banned": bool(result.get("banned")),
        }
    except requests.RequestException as e:
        log.debug("donut fetch error: %s", e)
        return None
