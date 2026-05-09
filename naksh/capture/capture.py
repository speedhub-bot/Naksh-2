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

    # ---- Minecraft ------------------------------------------------------
    mc_username: str = "N/A"
    uuid: str = "N/A"
    capes: list[str] = field(default_factory=list)
    account_type: str = "Unknown"  # Normal Minecraft / Game Pass / MSA-only / etc.

    # ---- Hypixel --------------------------------------------------------
    hypixel_level: float | None = None
    hypixel_first_login: str | None = None
    hypixel_last_login: str | None = None
    bedwars_stars: int | None = None
    skywars_stars: int | None = None
    skyblock_coins: str | None = None
    skyblock_networth: str | None = None
    skyblock_level: float | None = None

    # ---- DonutSMP -------------------------------------------------------
    donut_money: str | None = None
    donut_kills: int | None = None
    donut_playtime: str | None = None
    donut_banned: bool | None = None
    donut_ban_reason: str | None = None
    donut_ban_time_left: str | None = None
    donut_ban_id: str | None = None

    # ---- Microsoft basic ------------------------------------------------
    ms_balance: str | None = None
    ms_balance_value: float = 0.0           # numeric, for sorting
    ms_balance_currency: str = ""
    ms_rewards: str | None = None
    ms_rewards_value: int = 0               # numeric, for sorting
    ms_payment_methods: list[str] = field(default_factory=list)

    # ---- Microsoft advanced --------------------------------------------
    ms_country: str | None = None
    ms_country_code: str | None = None
    ms_region: str | None = None
    ms_age_group: str | None = None
    ms_first_name: str | None = None
    ms_last_name: str | None = None
    ms_date_of_birth: str | None = None
    ms_subscriptions: list[str] = field(default_factory=list)
    ms_redeem_history: list[str] = field(default_factory=list)
    ms_orders: list[str] = field(default_factory=list)

    # ---- Xbox -----------------------------------------------------------
    xbox_gamertag: str | None = None
    xbox_xuid: str | None = None
    xbox_gamerscore: str | None = None
    xbox_account_tier: str | None = None
    xbox_tenure_level: str | None = None

    extras: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def is_msa_only(self) -> bool:
        return "MSA" in self.account_type.upper() or self.account_type == "MSA Only"

    def builder(self, *, mask: bool = False) -> str:
        tags: list[str] = []
        atype = self.account_type.upper()
        if "ULTIMATE" in atype:
            tags.append("[XGPU]")
        elif "GAME PASS" in atype:
            tags.append("[XGP]")
        if "MINECRAFT" in atype or "NORMAL" in atype:
            tags.append("[MC]")
        if self.is_msa_only():
            tags.append("[MSA]")
        if self.capes:
            tags.append(f"[Capes:{','.join(self.capes)}]")
        if self.xbox_gamertag:
            tags.append(f"[GT:{self.xbox_gamertag}]")

        stats: list[str] = []
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
        if self.donut_banned:
            tag = "Donut_Banned"
            if self.donut_ban_id:
                tag += f"#{self.donut_ban_id}"
            stats.append(tag)
        if self.ms_balance:
            stats.append(f"MS_Bal: {self.ms_balance}")
        if self.ms_rewards:
            stats.append(f"MS_Pts: {self.ms_rewards}")
        if self.ms_payment_methods:
            stats.append(f"PM: {len(self.ms_payment_methods)}")
        if self.ms_subscriptions:
            stats.append(f"Subs: {len(self.ms_subscriptions)}")
        if self.ms_redeem_history:
            stats.append(f"Redeem: {len(self.ms_redeem_history)}")
        if self.ms_country:
            stats.append(f"Cty: {self.ms_country_code or self.ms_country}")
        if self.xbox_gamerscore:
            stats.append(f"GS: {self.xbox_gamerscore}")

        level_tag = ""
        if self.hypixel_level:
            level_tag = f"[Lvl:{self.hypixel_level:.0f}]"

        username = clean_name(self.mc_username) if self.mc_username != "N/A" else (
            self.xbox_gamertag or "Unknown"
        )
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

    def short_label(self) -> str:
        """Short identifier used in the live dashboard's recent-hits panel."""
        atype = self.account_type.upper()
        if "ULTIMATE" in atype:
            tier = "XGPU"
        elif "GAME PASS" in atype:
            tier = "XGP"
        elif "NORMAL" in atype or "MINECRAFT" in atype:
            tier = "MC"
        elif self.is_msa_only():
            tier = "MSA"
        else:
            tier = "?"
        username = (clean_name(self.mc_username)
                    if self.mc_username != "N/A" else self.xbox_gamertag) or "Unknown"
        bits = [tier, username]
        if self.ms_balance:
            bits.append(f"${self.ms_balance.split()[0]}")
        elif self.ms_rewards:
            bits.append(f"{self.ms_rewards}pts")
        elif self.skyblock_networth:
            bits.append(f"SB:{self.skyblock_networth}")
        return " · ".join(bits)
