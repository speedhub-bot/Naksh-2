"""Minecraft Services capture: entitlements (license tier) + profile + capes."""

from __future__ import annotations

import logging
from typing import Optional

import requests

from ..config import SETTINGS

log = logging.getLogger(__name__)


def _classify(entitlements: dict) -> Optional[str]:
    items = entitlements.get("items", [])
    has_normal = has_xgp = has_xgpu = False
    for item in items:
        name = item.get("name", "")
        source = item.get("source", "")
        if name in ("game_minecraft", "product_minecraft") and source in (
            "PURCHASE", "MC_PURCHASE",
        ):
            has_normal = True
        if name == "product_game_pass_pc":
            has_xgp = True
        if name == "product_game_pass_ultimate":
            has_xgpu = True
    if has_normal and has_xgpu:
        return "Normal Minecraft (with Game Pass Ultimate)"
    if has_normal and has_xgp:
        return "Normal Minecraft (with Game Pass)"
    if has_normal:
        return "Normal Minecraft"
    if has_xgpu:
        return "Xbox Game Pass Ultimate"
    if has_xgp:
        return "Xbox Game Pass (PC)"
    return None


def fetch_minecraft_capture(
    session: requests.Session, mc_token: str,
) -> tuple[Optional[str], str, str, list[str]]:
    """Return ``(account_type, username, uuid, capes)``.

    ``account_type`` is None when the account has no Minecraft entitlement.
    """
    try:
        resp = session.get(
            "https://api.minecraftservices.com/entitlements/license",
            headers={"Authorization": f"Bearer {mc_token}"},
            timeout=SETTINGS.request_timeout,
        )
        if resp.status_code != 200:
            return None, "N/A", "N/A", []
        account_type = _classify(resp.json())
        if account_type is None:
            return None, "N/A", "N/A", []
    except requests.RequestException as e:
        log.debug("entitlements error: %s", e)
        return None, "N/A", "N/A", []

    username, uuid_str, capes = "N/A", "N/A", []
    try:
        prof = session.get(
            "https://api.minecraftservices.com/minecraft/profile",
            headers={"Authorization": f"Bearer {mc_token}"},
            timeout=SETTINGS.request_timeout,
        )
        if prof.status_code == 200:
            data = prof.json()
            username = data.get("name", "N/A")
            uuid_str = data.get("id", "N/A")
            for cape in data.get("capes", []):
                alias = cape.get("alias")
                if alias:
                    capes.append(alias)
    except requests.RequestException:
        pass
    return account_type, username, uuid_str, capes
