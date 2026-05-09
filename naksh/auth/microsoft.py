"""Microsoft Live → Xbox Live → XSTS → Minecraft Services authentication.

Single public entrypoint :func:`authenticate(email, password, proxy)` returns an
:class:`AuthResult` describing the outcome.

Modeled after the proven flow in ``meow.py`` — including the legacy MSI client
id used by Mojang launchers, the ``cancel?mkt`` redirect branch, and detection
of 2FA / wrong-password / lockout response signatures.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

from ..config import SETTINGS
from .proxies import ProxyDict, ProxyPool
from .session import build_session

log = logging.getLogger(__name__)

OAUTH_URL = (
    "https://login.live.com/oauth20_authorize.srf"
    "?client_id=00000000402b5328&response_type=token"
    "&scope=service::user.auth.xboxlive.com::MBI_SSL"
    "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
)

# Multi-flavour regexes — Microsoft frequently rewrites their HTML
RE_SFTTAG = re.compile(
    r'value=\\"(.+?)\\"|value="(.+?)"|sFTTag:\'(.+?)\'|sFTTag:"(.+?)"'
    r'|name=\\"PPFT\\".*?value=\\"(.+?)\\"',
    re.S,
)
RE_URLPOST = re.compile(
    r'"urlPost":"(.+?)"|urlPost:\'(.+?)\'|urlPost:"(.+?)"|<form.*?action=\\"(.+?)\\"',
    re.S,
)
RE_IPT = re.compile(r'(?<="ipt" value=").+?(?=")')
RE_PPRID = re.compile(r'(?<="pprid" value=").+?(?=")')
RE_UAID = re.compile(r'(?<="uaid" value=").+?(?=")')
RE_ACTION_FMHF = re.compile(r'(?<=id="fmHF" action=").+?(?=")')
RE_RETURN_URL = re.compile(r'(?<="recoveryCancel":\{"returnUrl":").+?(?=",)')

TWOFA_SIGNATURES = (
    "recover?mkt",
    "account.live.com/identity/confirm",
    "Email/Confirm",
    "/Abuse?mkt=",
)
HARD_FAIL_SIGNATURES = (
    "password is incorrect",
    "account doesn't exist",
    "tried to sign in too many times",
    "help us protect your account",
)


@dataclass
class AuthResult:
    status: str  # "hit" | "bad" | "2fa" | "error"
    detail: str = ""
    mc_token: Optional[str] = None
    xbox_token: Optional[str] = None
    uhs: Optional[str] = None
    session: Optional[requests.Session] = None


def _first(match: re.Match) -> Optional[str]:
    return next((g for g in match.groups() if g), None)


def _get_ppft(session: requests.Session) -> tuple[Optional[str], Optional[str]]:
    """Fetch the OAuth login page and pull out PPFT + the form post URL."""
    try:
        r = session.get(OAUTH_URL, timeout=SETTINGS.request_timeout)
    except requests.RequestException as e:
        log.debug("ppft fetch error: %s", e)
        return None, None
    text = r.text
    sft_m = RE_SFTTAG.search(text)
    url_m = RE_URLPOST.search(text)
    if not sft_m or not url_m:
        return None, None
    sft = _first(sft_m)
    urlpost = _first(url_m)
    if not sft or not urlpost:
        return None, None
    return urlpost.replace("&amp;", "&"), sft


def _submit_credentials(
    session: requests.Session, email: str, password: str, urlpost: str, sft: str,
) -> tuple[str, Optional[str]]:
    """POST credentials. Returns ``(status, token)`` where status is one of
    ``hit`` / ``bad`` / ``2fa`` / ``retry``."""
    try:
        r = session.post(
            urlpost,
            data={"login": email, "loginfmt": email, "passwd": password, "PPFT": sft},
            allow_redirects=True,
            timeout=SETTINGS.request_timeout,
        )
    except requests.RequestException:
        return "retry", None

    text = r.text
    text_lc = text.lower()

    # Token in fragment of redirect URL → success
    if "#" in r.url and r.url != OAUTH_URL:
        token = parse_qs(urlparse(r.url).fragment).get("access_token", [None])[0]
        if token:
            return "hit", token

    # cancel?mkt path: a soft-bounce that needs a follow-up POST + GET
    if "cancel?mkt=" in text:
        try:
            ipt = RE_IPT.search(text).group()
            pprid = RE_PPRID.search(text).group()
            uaid = RE_UAID.search(text).group()
            action_url = RE_ACTION_FMHF.search(text).group()
            ret = session.post(
                action_url,
                data={"ipt": ipt, "pprid": pprid, "uaid": uaid},
                allow_redirects=True,
                timeout=SETTINGS.request_timeout,
            )
            return_url = RE_RETURN_URL.search(ret.text).group()
            fin = session.get(return_url, allow_redirects=True,
                              timeout=SETTINGS.request_timeout)
            token = parse_qs(urlparse(fin.url).fragment).get("access_token", [None])[0]
            if token:
                return "hit", token
        except Exception:
            pass

    if any(sig in text for sig in TWOFA_SIGNATURES):
        return "2fa", None
    if any(sig in text_lc for sig in HARD_FAIL_SIGNATURES):
        return "bad", None
    return "retry", None


def _xbox_xsts_minecraft(session: requests.Session, msa_token: str) -> tuple[
    Optional[str], Optional[str], Optional[str]
]:
    """Exchange MSA token → Xbox → XSTS → Minecraft access token.

    Returns ``(xbl_token, xsts_uhs, minecraft_token)``. Any element may be None
    on failure of that stage.
    """
    try:
        xbl = session.post(
            "https://user.auth.xboxlive.com/user/authenticate",
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": msa_token,
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=SETTINGS.request_timeout,
        )
        if xbl.status_code != 200:
            return None, None, None
        xbl_data = xbl.json()
        xbl_token = xbl_data.get("Token")
        uhs = xbl_data.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs")
        if not xbl_token:
            return None, None, None

        xsts = session.post(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            json={
                "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=SETTINGS.request_timeout,
        )
        if xsts.status_code != 200:
            return xbl_token, uhs, None
        xsts_token = xsts.json().get("Token")
        if not xsts_token:
            return xbl_token, uhs, None

        mc = session.post(
            "https://api.minecraftservices.com/authentication/login_with_xbox",
            json={"identityToken": f"XBL3.0 x={uhs};{xsts_token}"},
            headers={"Content-Type": "application/json"},
            timeout=SETTINGS.request_timeout,
        )
        if mc.status_code != 200:
            return xbl_token, uhs, None
        return xbl_token, uhs, mc.json().get("access_token")
    except requests.RequestException as e:
        log.debug("xbox/xsts/mc error: %s", e)
        return None, None, None


def authenticate(
    email: str, password: str,
    proxy: ProxyDict | None = None, *,
    pool: ProxyPool | None = None,
) -> AuthResult:
    """Run the full Microsoft → Minecraft auth flow.

    A small inline retry loop rotates proxies on transient failures. The caller
    receives a single :class:`AuthResult`.
    """
    last_detail = ""
    for attempt in range(SETTINGS.max_retries):
        session = build_session(with_proxies=bool(proxy or pool))
        if proxy:
            session.proxies = proxy
        elif pool:
            picked = pool.get()
            if picked:
                session.proxies = picked

        urlpost, sft = _get_ppft(session)
        if not urlpost or not sft:
            last_detail = "couldn't extract PPFT"
            time.sleep(0.2)
            continue

        status, token = _submit_credentials(session, email, password, urlpost, sft)
        if status == "2fa":
            return AuthResult("2fa", "Two-factor / additional verification required")
        if status == "bad":
            return AuthResult("bad", "Invalid credentials")
        if status == "retry" or not token:
            last_detail = "login retry"
            time.sleep(0.2)
            continue

        xbl_token, uhs, mc_token = _xbox_xsts_minecraft(session, token)
        if not mc_token:
            # Token without an Xbox profile is still technically a hit but has
            # no Minecraft entitlement — treat as bad for simplicity.
            return AuthResult(
                "bad",
                "Xbox/Minecraft token exchange failed (no Minecraft account)",
            )
        return AuthResult(
            status="hit", mc_token=mc_token, xbox_token=xbl_token, uhs=uhs,
            session=session,
        )

    return AuthResult("error", last_detail or "unknown auth failure")
