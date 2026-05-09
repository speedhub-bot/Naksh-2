"""Hypixel / SkyBlock capture via soopy.dev (best-effort, never fatal)."""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Optional

import requests

from ..config import SETTINGS
from ..utils.format import clean_name, format_number

log = logging.getLogger(__name__)


def _skill_average(member: dict) -> float:
    skills = member.get("skills", {})
    names = ("alchemy", "carpentry", "combat", "enchanting", "farming",
             "fishing", "foraging", "mining", "taming")
    total, count = 0.0, 0
    for n in names:
        s = skills.get(n)
        if s and "levelWithProgress" in s:
            total += s["levelWithProgress"]
            count += 1
    return total / count if count else 0.0


def _best_member(skyblock_data: dict, uuid_clean: str) -> Optional[dict]:
    profiles = skyblock_data.get("data", {}).get("profiles", {})
    best, best_score = None, -1
    for _, profile in profiles.items():
        member = profile.get("members", {}).get(uuid_clean)
        if not member:
            continue
        nw = (member.get("nwDetailed") or {}).get("networth", 0)
        score = nw / 1_000_000 * 100 + _skill_average(member) * 100 \
            + member.get("skyblock_level", 0) * 10
        if score > best_score:
            best_score, best = score, member
    return best


def fetch_hypixel(username: str, uuid: str | None = None,
                  timeout: int | None = None) -> Optional[dict[str, Any]]:
    """Fetch Hypixel + SkyBlock stats for a Minecraft username.

    Returns a dictionary of useful fields, or ``None`` if Hypixel has no record
    of this player or the public mirror failed.
    """
    timeout = timeout or SETTINGS.request_timeout
    if not username or username == "N/A":
        return None
    try:
        player_url = f"https://api.soopy.dev/player/{username}"
        sb_data = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_player = ex.submit(requests.get, player_url, timeout=timeout)
            f_sb = None
            if uuid:
                clean_uuid = uuid.replace("-", "")
                sb_url = (
                    f"https://soopy.dev/api/v2/player_skyblock/"
                    f"{clean_uuid}?networth=true"
                )
                f_sb = ex.submit(requests.get, sb_url, timeout=timeout)
            try:
                pr = f_player.result()
                p_data = pr.json() if pr.status_code == 200 else None
            except Exception:
                p_data = None
            if f_sb is not None:
                try:
                    sr = f_sb.result()
                    sb_data = sr.json() if sr.status_code == 200 else None
                except Exception:
                    sb_data = None
        if not p_data or not p_data.get("success") or "data" not in p_data:
            return None

        data = p_data["data"]
        result: dict[str, Any] = {
            "username": clean_name(data.get("displayname")) or username,
            "level": float(data.get("networkExp", 0) or 0) ** 0.5 / 100 if data.get("networkExp") else None,
            "first_login": data.get("firstLogin"),
            "last_login": data.get("lastLogin"),
            "achievements": data.get("achievements", {}),
        }
        ach = data.get("achievements", {}) or {}
        result["bedwars_stars"] = ach.get("bedwars_level")
        result["skywars_stars"] = ach.get("skywars_you_re_a_star")

        if sb_data and uuid:
            member = _best_member(sb_data, uuid.replace("-", ""))
            if member:
                nw = (member.get("nwDetailed") or {}).get("networth", 0)
                result["skyblock_networth"] = format_number(nw)
                result["skyblock_coins"] = format_number(
                    member.get("coin_purse", 0)
                )
                result["skyblock_level"] = member.get("skyblock_level")
        return result
    except Exception as e:
        log.debug("hypixel fetch error for %s: %s", username, e)
        return None
