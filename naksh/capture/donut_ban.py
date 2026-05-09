"""DonutSMP ban check via authenticated MC protocol login.

DonutSMP performs ban checks on its proxy AFTER authentication, so the
naive "send LoginStart and watch for Disconnect" trick doesn't work — the
server wants encryption + a real Mojang sessionserver join before it will
tell us whether the account is banned.

We use :mod:`mc_login` for the heavy lifting and decide:

* Disconnect with "ban" / "punish" / "blacklist" / etc keyword in the reason
  → ``BanResult(banned=True, reason=…, time_left=…, ban_id=…)``
* Disconnect with no ban keywords → not a ban (e.g. "outdated client",
  "server full") → ``BanResult(banned=False)``
* LoginSuccess → ``BanResult(banned=False)``
* Anything else → ``BanResult(banned=None)`` (unknown — we did our best)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from . import mc_login

log = logging.getLogger(__name__)


DONUT_HOST = "donutsmp.net"
DONUT_PORT = 25565

BAN_KEYWORDS = (
    "you are banned",
    "you are temporarily banned",
    "you are permanently banned",
    "ban id",
    "banned from this server",
    "permanent ban",
    "temp ban",
    "blacklisted",
    "punishment",
    "punished",
)

REASON_RE = re.compile(r"(You are .+?)(?:\\n|\n|$)", re.IGNORECASE)
TIME_LEFT_RE = re.compile(
    r"(?:Time\s*Left|Duration|Expires|Unbanned\s*in)[:\s]*([^\n\\]+)", re.IGNORECASE,
)
BAN_ID_RE = re.compile(r"Ban\s*ID[:\s]*#?([A-Za-z0-9\-]+)", re.IGNORECASE)
COLOUR_RE = re.compile(r"§.")


@dataclass
class BanResult:
    """Result of a DonutSMP ban check.

    ``banned`` is ``True`` / ``False`` / ``None``. ``None`` means the check
    could not be determined (network error, sessionserver rejection, etc.).
    """
    banned: Optional[bool]
    reason: str = ""
    time_left: str = ""
    ban_id: str = ""
    raw_message: str = ""


def check_donut_ban(
    *,
    username: str,
    player_uuid: str,
    access_token: str,
) -> BanResult:
    """Authenticated MC-protocol ban check against ``donutsmp.net``.

    Returns a :class:`BanResult`. Best-effort — no exception ever propagates.
    """
    if not (username and player_uuid and access_token):
        return BanResult(banned=None)

    if not mc_login.acquire_slot(timeout=20):
        return BanResult(banned=None)
    try:
        try:
            result = mc_login.login_check(
                host=DONUT_HOST,
                port=DONUT_PORT,
                username=username,
                player_uuid=player_uuid,
                access_token=access_token,
            )
        except Exception:
            log.exception("donut login_check crashed")
            return BanResult(banned=None)

        if result.login_success:
            return BanResult(banned=False)

        if result.disconnected:
            clean = COLOUR_RE.sub("", result.disconnect_reason or "").strip()
            lower = clean.lower()
            if not any(kw in lower for kw in BAN_KEYWORDS):
                # Disconnected for a reason other than ban — outdated client,
                # server full, kicked-by-plugin, etc.
                return BanResult(banned=False, raw_message=clean)
            return _parse_ban_message(clean)

        # error / handshake failure → unknown
        return BanResult(banned=None, raw_message=result.detail)
    finally:
        mc_login.release_slot()


def _parse_ban_message(text: str) -> BanResult:
    reason_match = REASON_RE.search(text)
    if reason_match:
        reason = reason_match.group(1).strip()
    else:
        # fall back to the first non-empty line
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        reason = lines[0] if lines else "banned (unknown reason)"

    time_match = TIME_LEFT_RE.search(text)
    time_left = time_match.group(1).strip() if time_match else ""

    id_match = BAN_ID_RE.search(text)
    ban_id = id_match.group(1).strip() if id_match else ""

    return BanResult(
        banned=True,
        reason=reason,
        time_left=time_left,
        ban_id=ban_id,
        raw_message=text,
    )
