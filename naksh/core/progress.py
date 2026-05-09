"""Progress accounting + Telegram message renderer.

Supports a rich live dashboard:

* Per-tier counters (XGPU / XGP / Normal / MSA)
* Recent hits panel — last 3 hits with username + tier + key stat
* Running totals: highest MS Points captured, highest MS balance, total
  payment methods, total subscriptions, etc.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from ..utils.format import format_seconds, progress_bar


@dataclass
class Counters:
    total: int = 0
    checked: int = 0
    hits: int = 0
    bad: int = 0
    twofa: int = 0
    errors: int = 0
    xgpu: int = 0
    xgp: int = 0
    normal: int = 0
    msa: int = 0
    started_at: float = field(default_factory=time.time)

    # Running enrichment totals
    top_points: int = 0
    top_points_email: str = ""
    top_balance: float = 0.0
    top_balance_display: str = ""
    top_balance_email: str = ""
    payment_methods_total: int = 0
    subscriptions_total: int = 0
    redeem_codes_total: int = 0
    hypixel_bans: int = 0
    donut_bans: int = 0


class Progress:
    """Threadsafe wrapper with a Telegram-ready render method."""

    def __init__(self, total: int, recent_size: int = 3) -> None:
        self._lock = threading.Lock()
        self.c = Counters(total=total)
        self._recent: deque[str] = deque(maxlen=recent_size)
        self._current: Optional[str] = None  # last email being checked

    # --- workers report through these methods ---------------------------
    def begin_check(self, email: str) -> None:
        with self._lock:
            self._current = email

    def hit(self, account_type: str, *, label: str | None = None) -> None:
        with self._lock:
            self.c.hits += 1
            self.c.checked += 1
            upper = account_type.upper()
            if "ULTIMATE" in upper:
                self.c.xgpu += 1
            elif "GAME PASS" in upper:
                self.c.xgp += 1
            elif "NORMAL" in upper or "MINECRAFT" in upper:
                self.c.normal += 1
            elif "MSA" in upper:
                self.c.msa += 1
            if label:
                self._recent.appendleft(label)

    def bad(self) -> None:
        with self._lock:
            self.c.bad += 1
            self.c.checked += 1

    def twofa(self) -> None:
        with self._lock:
            self.c.twofa += 1
            self.c.checked += 1

    def error(self) -> None:
        with self._lock:
            self.c.errors += 1
            self.c.checked += 1

    def report_points(self, email: str, points: int) -> None:
        with self._lock:
            if points > self.c.top_points:
                self.c.top_points = points
                self.c.top_points_email = email

    def report_balance(self, email: str, value: float, display: str) -> None:
        with self._lock:
            if value > self.c.top_balance:
                self.c.top_balance = value
                self.c.top_balance_display = display
                self.c.top_balance_email = email

    def report_payment_methods(self, n: int) -> None:
        with self._lock:
            self.c.payment_methods_total += n

    def report_subscriptions(self, n: int) -> None:
        with self._lock:
            self.c.subscriptions_total += n

    def report_redeem_codes(self, n: int) -> None:
        with self._lock:
            self.c.redeem_codes_total += n

    def report_hypixel_ban(self) -> None:
        with self._lock:
            self.c.hypixel_bans += 1

    def report_donut_ban(self) -> None:
        with self._lock:
            self.c.donut_bans += 1

    # --- snapshot helpers ----------------------------------------------
    def snapshot(self) -> tuple[Counters, list[str]]:
        with self._lock:
            return Counters(**self.c.__dict__), list(self._recent)

    # --- renderers ------------------------------------------------------
    def render(self, *, prefix: str = "🚀 <b>Checking Progress</b>") -> str:
        snap, recent = self.snapshot()
        elapsed = max(1e-3, time.time() - snap.started_at)
        cpm = int((snap.checked / elapsed) * 60) if elapsed > 0 else 0
        pct = (snap.checked / snap.total * 100) if snap.total else 100.0
        bar = progress_bar(pct)

        lines = [
            f"{prefix}",
            "━━━━━━━━━━━━━━━━━━",
            f"📈 [{bar}] <b>{pct:.1f}%</b>",
            f"🔄 {snap.checked} / {snap.total}  •  ⚡ {cpm} CPM  •  ⏱ {format_seconds(elapsed)}",
            "",
            f"✅ <b>Hits {snap.hits}</b>  ❌ Bad {snap.bad}  ⚠️ 2FA {snap.twofa}  ⚡ Err {snap.errors}",
            f"   🎮 XGPU <b>{snap.xgpu}</b>  •  🟢 XGP <b>{snap.xgp}</b>  "
            f"•  💎 Normal <b>{snap.normal}</b>  •  🆔 MSA <b>{snap.msa}</b>",
        ]

        # Enrichment line — only show when something has been captured
        bits: list[str] = []
        if snap.top_points:
            bits.append(f"⭐ Top points <b>{snap.top_points}</b>")
        if snap.top_balance > 0:
            bits.append(f"💰 Top balance <b>{snap.top_balance_display}</b>")
        if snap.payment_methods_total:
            bits.append(f"💳 PM <b>{snap.payment_methods_total}</b>")
        if snap.subscriptions_total:
            bits.append(f"📦 Subs <b>{snap.subscriptions_total}</b>")
        if snap.redeem_codes_total:
            bits.append(f"🎁 Redeem <b>{snap.redeem_codes_total}</b>")
        if snap.hypixel_bans:
            bits.append(f"🚫 Hyp-bans <b>{snap.hypixel_bans}</b>")
        if snap.donut_bans:
            bits.append(f"🍩 Donut-bans <b>{snap.donut_bans}</b>")
        if bits:
            lines.append("   " + "  •  ".join(bits))

        if recent:
            lines.append("")
            lines.append("🆕 <b>Recent hits</b>")
            for r in recent:
                lines.append(f"   • <code>{_escape_html(r)}</code>")

        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("Credits: @akaza_isnt")
        return "\n".join(lines)

    def render_final(self) -> str:
        snap, recent = self.snapshot()
        elapsed = max(0.0, time.time() - snap.started_at)
        lines = [
            "🏁 <b>Check Completed!</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"✅ <b>Hits: {snap.hits}</b>",
            f"   🎮 XGPU {snap.xgpu}  •  🟢 XGP {snap.xgp}  "
            f"•  💎 Normal {snap.normal}  •  🆔 MSA {snap.msa}",
            f"❌ Bad {snap.bad}  •  ⚠️ 2FA {snap.twofa}  •  ⚡ Errors {snap.errors}",
            f"🔄 Total checked: {snap.checked}/{snap.total}",
            f"⏱ Took: {format_seconds(elapsed)}",
        ]
        if snap.top_points:
            lines.append(
                f"⭐ Top rewards: {snap.top_points} pts ({snap.top_points_email})"
            )
        if snap.top_balance > 0:
            lines.append(
                f"💰 Top balance: {snap.top_balance_display} "
                f"({snap.top_balance_email})"
            )
        if snap.payment_methods_total:
            lines.append(f"💳 Payment methods captured: {snap.payment_methods_total}")
        if snap.subscriptions_total:
            lines.append(f"📦 Subscriptions captured: {snap.subscriptions_total}")
        if snap.redeem_codes_total:
            lines.append(f"🎁 Redeem codes captured: {snap.redeem_codes_total}")
        if snap.hypixel_bans:
            lines.append(f"🚫 Hypixel bans found: {snap.hypixel_bans}")
        if snap.donut_bans:
            lines.append(f"🍩 DonutSMP bans found: {snap.donut_bans}")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("Credits: @akaza_isnt")
        return "\n".join(lines)


def _escape_html(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
