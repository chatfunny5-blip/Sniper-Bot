# 👾 HIVE CYBER STATS BOT

<div align="center">

```
██╗  ██╗██╗██╗   ██╗███████╗    ██████╗██╗   ██╗██████╗ ███████╗██████╗
██║  ██║██║██║   ██║██╔════╝   ██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗
███████║██║██║   ██║█████╗     ██║      ╚████╔╝ ██████╔╝█████╗  ██████╔╝
██╔══██║██║╚██╗ ██╔╝██╔══╝     ██║       ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗
██║  ██║██║ ╚████╔╝ ███████╗   ╚██████╗   ██║   ██████╔╝███████╗██║  ██║
╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝    ╚═════╝   ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝
```

**A Discord bot for Hive (Minecraft Bedrock) stats — neon terminal UI, adaptive polling, crash-resistant.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

## 📖 Table of Contents

- [What is this?](#-what-is-this)
- [⚠️ Limitations — please read](#️-limitations--please-read)
- [🎨 The look](#-the-look)
- [Features](#-features)
- [Commands](#-commands)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [How it works](#-how-it-works)
- [Setup — Step by Step](#-setup--step-by-step)
- [Launching on Railway](#-launching-on-railway)
- [Environment Variables](#-environment-variables)
- [Speed tuning](#-speed-tuning)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)

---

## 🎯 What is this?

`hive-cyber-stats-bot` is a modular Discord bot that queries the official
Hive API (`api.playhive.com/v0`) and renders player stats as a neon
"terminal readout" — on demand via slash command, continuously via a
self-refreshing live dashboard, or as an alert when a tracked player's
stats change.

Built with `discord.py` using the Cog pattern, with defensive error handling
throughout: a single bad API response, missing field, formatting edge case,
or rate-limit hit can't take the whole bot down or silently kill the
background tracker.

---

## ⚠️ Limitations — please read

The Hive API does **not** expose live online status, current game/server, or
a player's location — that's a deliberate anti-sniping design choice by
Hive. Nothing built on top of this API can show that in real time, no matter
how it's styled or how fast it polls.

**What this bot does instead:**
- **`/online`** and the **live dashboard's STATUS line** — infer "recently
  active" from the *last time a stat change was detected*. Not a real
  status; labeled as such in the response.
- **Round-finished alerts** — report a *time window* (between the last clean
  check and the check that found a change), never an exact live moment.
  Round **start** time cannot be determined at all this way — there is no
  "player joined a game" signal in the API, only stat totals.
- **Live winstreak** — Hive's API doesn't provide a winstreak field, so this
  bot counts it client-side: detected win → +1, detected non-win round → 0.
  If several rounds happen within one poll interval and at least one was a
  loss, it conservatively resets to 0 (can't tell which round came first).

---

## 🎨 The look

Every embed is rendered as a colored terminal readout using Discord's
`` ```ansi `` code-block support — a subset of real ANSI escape codes that
Discord's **Desktop and web clients** render as actual neon colors:

```ansi
╔═══════════════════╗
║ TARGET   NOTCH    ║
║ QUERY    COMPLETE ║
╚═══════════════════╝

[ BEDWARS :: SOLO ]
WINS             142
KILLS            891
DEATHS           203
K/D RATIO       4.39
```

⚠️ **Honest caveat:** not every Discord **mobile** client version renders
ANSI colors — some fall back to plain monospace text there. That's a
Discord client limitation, not something this bot can control. Everything
still reads fine either way, it's just not colored on those clients.

---

## ✨ Features

| Feature | Description |
|---|---|
| 👾 **Neon Terminal UI** | Every embed is a colored ANSI "readout", not plain text fields |
| 🔴 **Live Dashboard** | `/livestats` posts one message that self-refreshes every poll cycle with all stats + an aggregate power-level summary |
| ⚡ **Adaptive Fast Polling** | Default interval cut to 15s; each tracked player has independent exponential backoff on rate limits instead of one global slowdown |
| 📊 **Stats on Demand** | Stats for 14 Hive games, cleanly rendered with color-coded categories + KD |
| 🔍 **Raw JSON Viewer** | Inspect raw data to discover new/undocumented fields |
| 👁️ **Player Watchlist** | Track any number of players per channel |
| 🔔 **Round-Finished Alerts** | Neon embed with a time window when stats increase |
| 🔥 **Live Winstreak** | Client-side computed streak, persisted across restarts |
| 🟢 **Activity Indicator** | Best-effort "recently active" status, both standalone and inside the live dashboard |
| 🧩 **Cog Architecture** | Cleanly separated modules, easy to extend |
| 🛡️ **Crash-Resistant Polling** | Per-player error isolation + auto-restarting background loop |
| ☁️ **One-Click Deploy** | Runs straight from GitHub via Railway |

---

## 💬 Commands

| Command | Arguments | Description |
|---|---|---|
| `/stats` | `name`, `game` *(optional)* | Shows a player's stats as a neon terminal readout |
| `/livestats` | `name` | Posts a **self-refreshing live dashboard** for a player |
| `/stoplive` | `name` | Stops refreshing that player's live dashboard |
| `/raw` | `name`, `game` *(optional)* | Shows the raw API response as JSON |
| `/track` | `name` | Starts tracking a player in the current channel (round-finished alerts) |
| `/untrack` | `name` | Stops tracking a player |
| `/tracked` | – | Lists all currently tracked players |
| `/streak` | `name` | Shows the current client-side live winstreak(s) |
| `/online` | `name` | Shows a best-effort "recently active" indicator |

**Game codes:** `wars` `dr` `hide` `sg` `murder` `sky` `ctf` `drop` `ground` `build` `party` `bridge` `grav` `bed`

```
/stats name:Steve123 game:bed
/livestats name:Steve123
/track name:Steve123
/online name:Steve123
/streak name:Steve123
```

---

## 🏗️ Architecture

```
┌─────────────┐   Slash Commands   ┌──────────────┐
│   Discord    │ ◄─────────────────► │   bot.py     │
│   Server     │                     │  (loader +   │
└─────────────┘                     │ error handler)│
                                     └──────┬───────┘
                                            │ loads
                    ┌────────────────────────┼────────────────────────┐
                    ▼                                                 ▼
           ┌────────────────┐                                ┌────────────────┐
           │ cogs/stats.py  │                                │cogs/tracking.py│
           │ /stats /raw    │ ◄── shared ANSI embed builders ─│ /livestats     │
           │ /livestats*    │       (activity_status, etc.)   │ /track /online │
           └───────┬────────┘                                │  poll_loop()   │
                    │                                         │  + backoff     │
                    │                                         └───────┬────────┘
                    └──────────────┐                   ┌──────────────┘
                                    ▼                   ▼
                             ┌─────────────┐    ┌─────────────┐
                             │ hive_api.py │    │ storage.py  │
                             │ API wrapper │    │ JSON store  │
                             └──────┬──────┘    └─────────────┘
                                    ▼
                         api.playhive.com/v0

              formatting.py: shared labels, KD, mode detection,
             streak math, ANSI rendering — used by both cogs

  * build_full_stats_embed() lives in cogs/stats.py; build_live_dashboard_embed()
    is called from both /livestats and poll_loop() to keep the dashboard message fresh
```

---

## 📂 Project Structure

```
hive-cyber-bot/
├── bot.py                    # Entry point — starts the bot, loads cogs, global error handler
├── hive_api.py                # Async wrapper around the Hive REST API
├── storage.py                  # Persists the watchlist + streaks + timestamps + live-message refs as JSON
├── formatting.py                # Shared labels, KD calc, mode detection, streak logic, ANSI rendering
├── requirements.txt
├── Procfile                     # Start command for Railway
├── env.example
├── .gitignore
├── README.md                     # ← you are here
└── cogs/
    ├── __init__.py
    ├── stats.py                # /stats, /raw, /livestats, /stoplive + shared embed builders
    └── tracking.py              # /track, /untrack, /tracked, /streak, /online, poll_loop + backoff
```

---

## ⚙️ How it works

1. **Startup:** `bot.py` reads `.env`, builds the Discord client + `HiveAPI`
   client, loads both cogs, and registers a global error handler for slash
   commands so failures show a clear message instead of a silent
   "This interaction failed."
2. **Slash sync:** on `on_ready`, the bot syncs its command tree with
   Discord and logs how many commands were synced.
3. **`/stats` / `/raw`:** fetch from `api.playhive.com/v0/game/all/...` and
   render an ANSI terminal embed or raw JSON. Wrapped in try/except so any
   failure returns a clean error message instead of crashing.
4. **`/livestats`:** posts one embed, registers it in `data/tracked.json`,
   and from then on `poll_loop` overwrites that same message every cycle
   with fresh data — a true live dashboard instead of a spam of new alerts.
5. **`poll_loop`** (runs every `POLL_INTERVAL_SECONDS`, staggered across
   tracked players): for each player — in its own try/except so one
   player's failure can't affect others — checks a per-player backoff
   window first, then fetches current stats, diffs them against the last
   snapshot, updates the live winstreak, updates the "last active"
   timestamp, refreshes that player's live dashboard message if one exists,
   and posts an alert if anything increased. A 429 response sets an
   exponential, per-player cool-down instead of erroring every cycle. If
   the loop itself ever crashes unexpectedly, a registered error handler
   logs it and restarts it after 10 seconds.

---

## 🚀 Setup — Step by Step

### 1. Create a Discord bot
1. [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**
2. **Bot** tab → **Reset Token** → copy it → this is your `DISCORD_TOKEN`
3. **Installation** tab (or **OAuth2 → URL Generator** in the classic view):
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Embed Links`, `Read Message History`, `Use Application Commands`
     *(`Read Message History` is needed so the bot can find and edit its own live-dashboard message)*
   - Save changes, then copy the install link
4. Open the link in a browser tab → select your server → Authorize

### 2. Get a Hive API key (recommended, especially for fast polling)
Send a plain-text request to **api@hivemc.com** — without a key, rate limits are very low.

### 3. Add the files
Add all files exactly as laid out in the project structure above.

---

## ☁️ Launching on Railway

1. [railway.app](https://railway.app) → sign in with GitHub
2. **New Project → Deploy from GitHub repo** → select your repo
3. Railway auto-detects Python (Nixpacks) and uses the `Procfile`
4. Set the **Variables** (see table below)
5. **Settings → Volumes → Add Volume** → mount path `/data` (otherwise the
   watchlist, streaks, and activity data are lost on every redeploy)
6. Done — Railway auto-deploys on every push to `main`

Check **Deployments → View Logs → Deploy Logs**. You should see:
```
Loaded cog: cogs.stats
Loaded cog: cogs.tracking
Logged in as YourBot#1234 | synced 9 slash command(s)
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Bot token from the Developer Portal |
| `HIVE_API_KEY` | recommended | Significantly raises the API rate limit |
| `POLL_INTERVAL_SECONDS` | – | How often tracked players are checked (default: `15`) |
| `ALERT_CHANNEL_ID` | – | Fallback channel if `/track` runs without channel context |
| `DATA_FILE` | – | Path to the watchlist JSON (Railway: `/data/tracked.json`) |

---

## ⚡ Speed tuning

`POLL_INTERVAL_SECONDS` sets the *target* cadence, but it's not the whole
story: each tracked player also gets independent, in-memory exponential
backoff (`POLL_INTERVAL * 2^errors`, capped at 5 minutes) whenever a request
for that specific player gets rate-limited. Every other player keeps polling
at full speed regardless. This means you can safely experiment with lower
values — worst case a single player self-throttles for a while instead of
the whole bot erroring out.

| Setup | Reasonable interval |
|---|---|
| No API key, 1 player | ~15s (the default) |
| No API key, several players | 30-45s |
| With `HIVE_API_KEY`, 1-2 players | 5-10s |
| With `HIVE_API_KEY`, many players | 10-15s |

To change it: Railway → your project → **Variables** → `POLL_INTERVAL_SECONDS` → redeploys automatically.

Two independent ceilings to keep in mind at very low values:
- **Hive's API rate limit** (unpublished exact number; much higher with a key)
- **Discord's message-edit rate limit** (~5 edits / 5s per message) — relevant if you run `/livestats` for several players in the same channel at a very low interval

---

## 🔧 Troubleshooting

**A command doesn't show up in Discord at all**
1. Confirm the file that defines it is actually committed and pushed to GitHub
2. Confirm Railway redeployed after that push (Deployments tab, latest entry should be after your commit time, status "Success")
3. Check Deploy Logs for `Loaded cog: cogs.tracking` and `synced N slash command(s)`
4. Fully close and reopen the Discord app (slash commands are cached client-side)
5. New commands can take up to an hour to propagate globally, though it's usually minutes

**Live dashboard stopped updating**
- Check Deploy Logs for `Failed to update live message` — usually means the message was deleted or the bot lost `Read Message History` permission in that channel.
- If you see repeated `Rate limit/error for <name> — backing off Ns`, that player is in a cool-down window after hitting Hive's rate limit; it recovers automatically once the backoff expires.

**Alerts stopped appearing after they used to work**
- Check Deploy Logs for a line starting with `poll_loop crashed unexpectedly` — this version auto-restarts the loop after logging, so it should recover within 10s on its own. If you see repeated crashes, copy the traceback from the logs so the root cause can be fixed.
- Make sure a Volume is mounted at `/data` — without persistence, a redeploy wipes the tracked list and `/track`/`/livestats` need to be re-run.

**"This interaction failed" in Discord**
- As of this version, command errors are caught and reported back as a visible message instead. If you still see the generic Discord error, check Deploy Logs — the actual exception is logged there.

**Embeds show as plain text, no colors**
- Expected on some mobile Discord client versions — see [The look](#-the-look). Desktop and web always render the colors.

---

## ❓ FAQ

**Does the bot show when someone comes online/goes offline?**
No official API can. `/online` and the live dashboard's STATUS line give a best-effort "recently active" guess based on stat changes — clearly labeled as such.

**Why don't I see `winstreak` in `/stats`?**
Hive's API doesn't expose that field. Use `/streak` for the client-side computed live winstreak instead.

**Can I track multiple players at once?**
Yes — run `/track` or `/livestats` for each, in whichever channel you want alerts/dashboards to post in.

**What's the difference between `/track` and `/livestats`?**
`/track` posts a new alert embed only when stats change. `/livestats` posts one message and keeps overwriting it every poll cycle regardless of whether anything changed — a persistent dashboard rather than a stream of alerts. Running both on the same player is fine; `/livestats` automatically also tracks the player.
