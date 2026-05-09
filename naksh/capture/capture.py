"""Capture model.

Holds everything we collected for one hit and renders the human-friendly line
that goes into ``Capture.txt``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..utils.format import clean_name, mask_password


@dataclass
class Capture:
    email: str
    password: str
    mc_username: str = "N/A"
    uuid: str = "N/A"
    capes: list[str] = field(default_factory=list)
    account_type: str = "Unknown"  # Normal Minecraft / Game Pass / etc.

    # Hypixel
    hypixel_level: float | None = None
    hypixel_first_login: str | None = None
    hypixel_last_login: str | None = None
    bedwars_stars: int | None = None
    skywars_stars: int | None = None
    skyblock_coins: str | None = None
    skyblock_networth: str | None = None
    skyblock_level: float | None = None

    # Donut
    donut_money: str | None = None
    donut_kills: int | None = None
    donut_playtime: str | None = None
    donut_banned: bool | None = None

    # Microsoft extras
    ms_balance: str | None = None
    ms_rewards: str | None = None
    ms_payment_methods: list[str] = field(default_factory=list)
    ms_addresses: list[str] = field(default_factory=list)

    extras: dict[str, Any] = field(default_factory=dict)

    def builder(self, *, mask: bool = False) -> str:
        tags: list[str] = []
        atype = self.account_type.upper()
        if "ULTIMATE" in atype:
            tags.append("[XGPU]")
        elif "GAME PASS" in atype:
            tags.append("[XGP]")
        if "MINECRAFT" in atype or "NORMAL" in atype:
            tags.append("[MC]")
        if self.capes:
            tags.append(f"[Capes:{','.join(self.capes)}]")
        stats = []
        if self.bedwars_stars:
            stats.append(f"BW: {self.bedwars_stars}★")
        if self.skywars_stars:
            stats.append(f"SW: {self.skywars_stars}★")
        if self.skyblock_networth:
            stats.append(f"SB_NW: {self.skyblock_networth}")
        if self.skyblock_coins:
            stats.append(f"SB_Coins: {self.skyblock_coins}")
        if self.donut_money:
            stats.append(f"Donut$: {self.donut_money}")
        if self.ms_balance:
            stats.append(f"MS_Bal: {self.ms_balance}")
        if self.ms_rewards:
            stats.append(f"MS_Pts: {self.ms_rewards}")
        if self.ms_payment_methods:
            stats.append(f"PM: {len(self.ms_payment_methods)}")

        level_tag = ""
        if self.hypixel_level:
            level_tag = f"[Lvl:{self.hypixel_level:.0f}]"

        username = clean_name(self.mc_username) or "Unknown"
        password_display = mask_password(self.password) if mask else self.password

        parts = [f"[{username}]"]
        parts += tags
        if level_tag:
            parts.append(level_tag)
        parts.append(f"{self.email}:{password_display}")
        line = " ".join(parts)
        if stats:
            line += f"  ::  {' | '.join(stats)}"
        return line
