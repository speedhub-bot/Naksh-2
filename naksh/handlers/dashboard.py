"""``/dashboard`` — lifetime stats + last-job summary view.

Shows:

* Lifetime aggregates from the user's ``stats`` row
* Top capture from the most recent finished job (parsed from result files)
* Currently running / queued jobs for this user
"""

from __future__ import annotations

import logging
from pathlib import Path

from pyrogram import filters, types

from ..config import SETTINGS

log = logging.getLogger(__name__)


def _last_job_dir_for(user_id: int) -> Path | None:
    """Return the most-recently-modified result directory for ``user_id``."""
    base = SETTINGS.results_dir
    if not base.exists():
        return None
    candidates = [d for d in base.iterdir() if d.is_dir() and d.name.startswith(f"{user_id}_")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def _first_lines(path: Path, n: int = 3) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                out.append(line)
                if len(out) >= n:
                    break
    except OSError:
        return []
    return out


def register(app) -> None:
    client = app.client
    db = app.db

    @client.on_message(filters.command("dashboard") & filters.private)
    async def cmd_dashboard(_, message: types.Message):
        user_id = message.from_user.id
        u = db.get_user(user_id)
        if not u or u["role"] not in ("authorized", "admin"):
            await message.reply("⚠️ You don't have access yet.")
            return

        s = db.get_user_stats(user_id)
        last = _last_job_dir_for(user_id)

        lines = [
            "📊 <b>Dashboard</b>",
            "━━━━━━━━━━━━━━━━━━",
            f"🆔 User: <code>{user_id}</code> · 🎖 {u['role'].capitalize()}",
            "",
            "<b>Lifetime</b>",
            f"🔄 Checked: {s['total_checked'] if s else 0}",
            f"✅ Hits: {s['hits'] if s else 0}",
            f"❌ Bad: {s['bad'] if s else 0}  •  ⚠️ 2FA: {s['twofa'] if s else 0}  "
            f"•  ⚡ Err: {s['errors'] if s else 0}",
        ]

        if last:
            xgpu = _count_lines(last / "XGPU.txt")
            xgp = _count_lines(last / "XGP.txt")
            normal = _count_lines(last / "Normal.txt")
            msa = _count_lines(last / "MSA.txt")
            hits = _count_lines(last / "Hits.txt")
            bal = _count_lines(last / "MS_Balance.txt")
            pts = _count_lines(last / "MS_Points.txt")
            pm = _count_lines(last / "MS_Payments.txt")
            subs = _count_lines(last / "MS_Subscriptions.txt")
            redeem = _count_lines(last / "MS_RedeemHistory.txt")
            hyban = _count_lines(last / "Hypixel_Bans.txt")
            doban = _count_lines(last / "Donut_Bans.txt")
            top_pts = _first_lines(last / "MS_Points.txt", 3)
            top_bal = _first_lines(last / "MS_Balance.txt", 3)

            lines += [
                "",
                f"<b>Last job</b> · <code>{last.name}</code>",
                f"✅ Hits {hits}  (XGPU {xgpu} / XGP {xgp} / Normal {normal} / MSA {msa})",
                f"💰 Balance {bal}  •  ⭐ Points {pts}  •  💳 PM {pm}",
                f"📦 Subs {subs}  •  🎁 Redeem {redeem}",
                f"🚫 Hyp-bans {hyban}  •  🍩 Donut-bans {doban}",
            ]
            if top_pts:
                lines.append("")
                lines.append("<b>Top points</b>")
                for ln in top_pts:
                    lines.append(f"   • <code>{_escape(ln)}</code>")
            if top_bal:
                lines.append("")
                lines.append("<b>Top balance</b>")
                for ln in top_bal:
                    lines.append(f"   • <code>{_escape(ln)}</code>")
        else:
            lines.append("")
            lines.append("<i>No completed jobs yet — drop a combo file to start.</i>")

        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("Credits: @akaza_isnt")
        await message.reply("\n".join(lines))


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
