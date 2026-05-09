"""Advanced Microsoft account captures.

Each function takes the authenticated ``requests.Session`` from the auth flow
plus a token (the Xbox/MSA bearer) and returns a small structured result, or
``None`` when the data isn't available. Errors are swallowed — this is purely
best-effort enrichment, never part of the hit/bad classification.
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

# Public client ids used by various MS web/desktop apps. They're not secrets —
# they're what every browser sees in the OAuth ?client_id= query parameter.
ACCOUNT_MS_CLIENT_ID = "81feaced-5ddd-41e7-8bef-3e20a2689bb7"
ACCOUNT_MS_REDIRECT = "https://account.microsoft.com/auth/complete-silent-auth"
ACCOUNT_MS_SCOPE = "openid+profile"

XBOX_LIVE_CLIENT_ID = "0000000048093EE3"


# ----------------------------------------------------------------------------
# Xbox Live profile (gamertag, country, age band, gamer score)
# ----------------------------------------------------------------------------
def fetch_xbox_profile(
    session: requests.Session, xbl_token: str | None, uhs: str | None,
) -> Optional[dict]:
    """Fetch the Xbox Live profile for the authenticated user."""
    if not xbl_token or not uhs:
        return None
    try:
        # XSTS for xboxlive.com (different RelyingParty than Minecraft's)
        xsts = session.post(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            json={
                "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                "RelyingParty": "http://xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=SETTINGS.request_timeout,
        )
        if xsts.status_code != 200:
            return None
        xsts_token = xsts.json().get("Token")
        xuid = (xsts.json().get("DisplayClaims", {}).get("xui", [{}])[0]
                .get("xid"))
        if not xsts_token:
            return None

        prof = session.get(
            "https://profile.xboxlive.com/users/me/profile/settings"
            "?settings=GameDisplayName,Gamerscore,Gamertag,AccountTier,"
            "XboxOneRep,PreferredColor,RealName,Bio,Location,TenureLevel",
            headers={
                "Authorization": f"XBL3.0 x={uhs};{xsts_token}",
                "x-xbl-contract-version": "3",
                "Accept": "application/json",
                "Accept-Language": "en-US",
            },
            timeout=SETTINGS.request_timeout,
        )
        if prof.status_code != 200:
            return None
        data = prof.json()
        if not data.get("profileUsers"):
            return None
        settings = data["profileUsers"][0].get("settings", [])
        out = {"xuid": xuid}
        for s in settings:
            out[s.get("id", "").lower()] = s.get("value")
        return out
    except (requests.RequestException, ValueError) as e:
        log.debug("xbox profile error: %s", e)
        return None


# ----------------------------------------------------------------------------
# Microsoft account profile (country, age, DOB, region)
# ----------------------------------------------------------------------------
def fetch_ms_profile(session: requests.Session) -> Optional[dict]:
    """Scrape MS account profile data from account.microsoft.com.

    Returns a small dict with country, region, age group, sign-in name. The
    page is HTML, not JSON, so we use targeted regexes.
    """
    try:
        r = session.get("https://account.microsoft.com/profile",
                        timeout=SETTINGS.request_timeout + 5,
                        allow_redirects=True)
        if r.status_code != 200:
            return None
        text = r.text
        out: dict[str, str] = {}
        for key, pat in (
            ("country", r'"country":\s*"([^"]+)"'),
            ("country_code", r'"countryCode":\s*"([^"]+)"'),
            ("region", r'"region":\s*"([^"]+)"'),
            ("ageGroup", r'"ageGroup":\s*"([^"]+)"'),
            ("primaryAlias", r'"primaryAlias":\s*"([^"]+)"'),
            ("firstName", r'"firstName":\s*"([^"]+)"'),
            ("lastName", r'"lastName":\s*"([^"]+)"'),
            ("dateOfBirth", r'"dateOfBirth":\s*"([^"]+)"'),
        ):
            m = re.search(pat, text)
            if m:
                out[key] = m.group(1)
        return out or None
    except requests.RequestException as e:
        log.debug("ms profile error: %s", e)
        return None


# ----------------------------------------------------------------------------
# Subscriptions: Game Pass, Xbox Live Gold, Microsoft 365, etc.
# ----------------------------------------------------------------------------
def fetch_subscriptions(session: requests.Session) -> list[str]:
    """Return a list of human-readable active subscriptions."""
    try:
        r = session.get(
            "https://account.microsoft.com/services/api/get-services",
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=SETTINGS.request_timeout + 5,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        subs: list[str] = []
        for svc in (data.get("services") or []):
            name = svc.get("name") or svc.get("productName")
            status = svc.get("status") or svc.get("subscriptionStatus")
            renews = svc.get("renewalDate") or svc.get("nextChargeDate")
            if not name:
                continue
            label = name
            if status:
                label += f" ({status})"
            if renews:
                label += f", renews {renews[:10]}"
            subs.append(label)
        return subs
    except (requests.RequestException, ValueError) as e:
        log.debug("subscriptions error: %s", e)
        return []


# ----------------------------------------------------------------------------
# Gift / redeem code history (codes the user has redeemed on this account)
# ----------------------------------------------------------------------------
def fetch_redeem_history(session: requests.Session) -> list[str]:
    """Return a list of redeem-code descriptions for this account."""
    try:
        r = session.get(
            "https://account.microsoft.com/billing/orders/api/orders/get-orders",
            params={"size": 50, "type": "redeem"},
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=SETTINGS.request_timeout + 5,
        )
        if r.status_code != 200:
            return []
        data = r.json() or {}
        orders = data.get("orders") or data.get("orderHistory") or []
        out: list[str] = []
        for o in orders:
            descr = (o.get("description") or o.get("productName")
                     or o.get("subject"))
            date = (o.get("orderDate") or o.get("redemptionDate") or "")[:10]
            if descr:
                out.append(f"[{date}] {descr}")
        return out
    except (requests.RequestException, ValueError) as e:
        log.debug("redeem history error: %s", e)
        return []


# ----------------------------------------------------------------------------
# Recent orders (purchases on the MS Store)
# ----------------------------------------------------------------------------
def fetch_orders(session: requests.Session) -> list[str]:
    try:
        r = session.get(
            "https://account.microsoft.com/billing/orders/api/orders/get-orders",
            params={"size": 25},
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=SETTINGS.request_timeout + 5,
        )
        if r.status_code != 200:
            return []
        data = r.json() or {}
        orders = data.get("orders") or data.get("orderHistory") or []
        out: list[str] = []
        for o in orders[:25]:
            descr = o.get("description") or o.get("productName")
            total = o.get("totalAmount") or o.get("total") or ""
            cur = o.get("currency") or ""
            date = (o.get("orderDate") or "")[:10]
            if descr:
                out.append(f"[{date}] {descr} — {total} {cur}".strip())
        return out
    except (requests.RequestException, ValueError) as e:
        log.debug("orders error: %s", e)
        return []
