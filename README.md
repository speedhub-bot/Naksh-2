# Naksh-2 — Minecraft Account Checker (Telegram Bot)

A structured Telegram bot that takes `email:pass` combos and validates them
through the Microsoft Live → Xbox Live → XSTS → Minecraft Services chain. For
every hit it captures Minecraft license tier, profile/capes, Hypixel /
SkyBlock / Donut SMP stats, MS Rewards points, MS account balance, and
payment methods.

> Reference: the legacy `meow.py` console checker is kept in the repo for
> archival reading, but nothing imports from it. The runtime bot lives in the
> `naksh/` package.

## Project layout

```
Naksh-2/
├── run.py                 # entry point
├── naksh/
│   ├── config.py          # all defaults + env loading (one source of truth)
│   ├── bot.py             # Pyrogram client + BotApp singleton
│   ├── db.py              # SQLite (Row factory, no positional indexing)
│   ├── handlers/          # /start, settings, upload, admin
│   ├── core/              # engine, progress, queue, results
│   ├── auth/              # microsoft.py, session.py, proxies.py
│   ├── capture/           # minecraft, hypixel, donut, microsoft (extras)
│   └── utils/             # format helpers, file writers + zip
├── requirements.txt
├── .env.example
└── meow.py                # legacy reference (not imported)
```

## Running

```bash
# 1. clone
git clone https://github.com/speedhub-bot/Naksh-2.git
cd Naksh-2

# 2. system deps (Linux)
sudo apt-get update
sudo apt-get install -y python3-venv

# 3. python venv + deps
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. run — public defaults are hardcoded, no .env needed
python run.py
```

The bot uses Telegram's public Pyrogram credentials by default
(`api_id=2040`, `api_hash=b18441a1ff607e10a989891a5462e627`). Override any
value via env or a `.env` file — see `.env.example`.

## Bot usage

1. Send `/start` to the bot. The first user is the configured admin
   (`ADMIN_ID`, default `5944410248`); everyone else lands in the
   `pending` queue and needs admin approval.
2. Drop a `.txt` combo file (`email:pass` per line). Up to
   `MAX_COMBO_SIZE_MB` (default 256 MB).
3. Optionally drop a proxy `.txt` file right after (filename should contain
   `proxy`). Otherwise send `/noproxy` to run without proxies.
4. Watch the live progress message. When the job finishes you'll get a
   single `Naksh_<userid>_<job>.zip` containing every result file.

### Result zip structure

```
Naksh_<userid>_<job>.zip
├── Hits.txt                 # all hits, email:pass per line
├── XGPU.txt                 # Game Pass Ultimate hits
├── XGP.txt                  # Game Pass (PC) hits
├── Normal.txt               # Bought-Minecraft hits
├── 2fa.txt                  # accounts that need 2-factor
├── Bad.txt                  # invalid credentials
├── Errors.txt
├── Capture.txt              # readable per-hit Capture builder lines
├── MS_Balance.txt           # Microsoft account balance hits
├── MS_Points.txt            # Bing Rewards points hits
├── MS_Payments.txt          # stored payment methods (CC/PayPal)
├── Hypixel_Capture.txt      # SkyBlock networth, BedWars stars, etc.
└── Donut_Capture.txt        # only if DONUT_API_KEY is set
```

## Bot commands

| Command   | Who    | Purpose                                              |
|-----------|--------|------------------------------------------------------|
| `/start`  | all    | Open menu / register                                 |
| `/noproxy`| user   | Skip proxies and run the queued combos               |
| `/cancel` | user   | Drop a pending combo upload                          |
| `/ban`    | admin  | `/ban <user_id>` — block someone                     |
| `/unban`  | admin  | `/unban <user_id>` — restore                         |
| `/broadcast` | admin | reply to any message + `/broadcast` to send to all  |

## What changed vs the previous version

| Area              | Before                                 | Now                               |
|-------------------|-----------------------------------------|------------------------------------|
| Telegram lib      | `aiogram` (Bot API, 20 MB cap)         | `pyrogram` (MTProto, 2 GB cap)    |
| Structure         | 8 top-level files, monolithic          | Clean `naksh/` package, 4 layers  |
| MS auth flow      | Simplified, no `cancel?mkt` branch     | Full meow.py flow                 |
| DB access         | Positional tuples (`user[3]`)          | `sqlite3.Row`, named columns      |
| Settings prompt   | Swallowed any next message             | Scoped to `awaiting_threads` set  |
| File handles      | Leaked on engine GC                    | Per-write open/close              |
| `excepthook` hack | Globally muted threading.excepthook    | Removed                           |
| Buddy Pass claim  | Dead endpoint                          | Removed                           |
| DonutSMP API      | Always called (401s)                   | Gated on `DONUT_API_KEY`          |
| pyCraft dep       | Stale fork, fragile                    | Removed                           |
| Result delivery   | Spammy multi-file when no hits         | One zip with everything           |
| Public creds      | Required env file                      | `2040` / `b18441a1ff607e10a989891a5462e627` baked in |

## Credits

Bot interface and capture flow modeled after `meow.py`.
Maintained by [@akaza_isnt](https://t.me/akaza_isnt).
