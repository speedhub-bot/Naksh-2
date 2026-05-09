"""Progress accounting + Telegram message renderer."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

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
    started_at: float = field(default_factory=time.time)

    def add_hit(self, account_type: str) -> None:
        self.hits += 1
        upper = account_type.upper()
        if "ULTIMATE" in upper:
            self.xgpu += 1
        elif "GAME PASS" in upper:
            self.xgp += 1
        elif "NORMAL" in upper:
            self.normal += 1


class Progress:
    """Threadsafe wrapper around :class:`Counters` with a render method."""

    def __init__(self, total: int) -> None:
        self._lock = threading.Lock()
        self.c = Counters(total=total)

    def update(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.c, k):
                    setattr(self.c, k, getattr(self.c, k) + v)

    def hit(self, account_type: str) -> None:
        with self._lock:
            self.c.add_hit(account_type)
            self.c.checked += 1

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

    def snapshot(self) -> Counters:
        with self._lock:
            return Counters(**self.c.__dict__)

    def render(self, *, prefix: str = "🚀 <b>Checking Progress</b>") -> str:
        snap = self.snapshot()
        elapsed = max(1e-3, time.time() - snap.started_at)
        cpm = int((snap.checked / elapsed) * 60) if elapsed > 0 else 0
        pct = (snap.checked / snap.total * 100) if snap.total else 100.0
        bar = progress_bar(pct)
        return (
            f"{prefix}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"✅ Hits: {snap.hits}  "
            f"(XGPU {snap.xgpu} / XGP {snap.xgp} / Normal {snap.normal})\n"
            f"❌ Bad: {snap.bad}\n"
            f"⚠️ 2FA: {snap.twofa}\n"
            f"⚡ Errors: {snap.errors}\n"
            f"🔄 Checked: {snap.checked}/{snap.total}\n"
            f"📈 [{bar}] {pct:.1f}%\n"
            f"⚡ CPM: {cpm}\n"
            f"⏱ Elapsed: {format_seconds(elapsed)}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Credits: @akaza_isnt"
        )

    def render_final(self) -> str:
        snap = self.snapshot()
        elapsed = max(0.0, time.time() - snap.started_at)
        return (
            "🏁 <b>Check Completed!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"✅ Hits: {snap.hits}  "
            f"(XGPU {snap.xgpu} / XGP {snap.xgp} / Normal {snap.normal})\n"
            f"❌ Bad: {snap.bad}\n"
            f"⚠️ 2FA: {snap.twofa}\n"
            f"⚡ Errors: {snap.errors}\n"
            f"🔄 Total checked: {snap.checked}/{snap.total}\n"
            f"⏱ Took: {format_seconds(elapsed)}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Credits: @akaza_isnt"
        )
