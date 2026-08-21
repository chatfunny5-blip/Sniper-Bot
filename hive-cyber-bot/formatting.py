"""
formatting.py
Shared helpers for StatsCog and TrackingCog:
 - detecting BedWars/SkyWars modes (Solo/Duos/Squads/Mega) from the JSON path
 - KD calculation
 - pretty labels/emoji for known stat fields
 - client-side "live" win streak tracking
 - ANSI "terminal" rendering for the cyberpunk-styled embeds (Discord's
   ```ansi code blocks support a subset of ANSI SGR color codes)

Note: Hive does not publicly document its exact JSON field names. The aliases
below cover the most common spellings seen in real responses. If Hive uses a
different name for something, check with /raw and extend the tables below.
"""
from __future__ import annotations

import re

MODE_ALIASES: dict[str, str] = {
    "solo": "Solo", "solos": "Solo",
    "duo": "Duos", "duos": "Duos",
    "squad": "Squads", "squads": "Squads",
    "mega": "Mega", "megawalls": "Mega",
    "manor": "Manor",
}

# Known stat-field fragments -> (emoji, pretty label).
# NOTE: order does not matter for correctness — label_for_key() always checks
# the longest fragments first so e.g. "final_kills" is never mislabeled as
# generic "kills".
KNOWN_FIELDS: dict[str, tuple[str, str]] = {
    "winstreak": ("🔥", "Winstreak"),
    "win_streak": ("🔥", "Winstreak"),
    "streak": ("🔥", "Winstreak"),
    "victories": ("🏆", "Wins"),
    "wins": ("🏆", "Wins"),
    "losses": ("💀", "Losses"),
    "finalkills": ("🗡️", "Final Kills"),
    "finaldeaths": ("🪦", "Final Deaths"),
    "kills": ("⚔️", "Kills"),
    "deaths": ("☠️", "Deaths"),
    "bedsdestroyed": ("🛏️", "Beds Destroyed"),
    "level": ("⭐", "Level"),
    "prestige": ("🎖️", "Prestige"),
    "xp": ("✨", "XP"),
    "gamesplayed": ("🎮", "Games Played"),
    "played": ("🎮", "Games Played"),
}

# Fields that exist in the API response but aren't displayable stats
# (IDs, timestamps, ...) - hidden from /stats, /raw formatting, and alerts.
EXCLUDED_FIELDS: set[str] = {
    "uuid", "id", "firstplayed", "lastplayed", "createdat", "updatedat",
}


def is_excluded(key: str) -> bool:
    """True for fields that aren't displayable stats (UUID, timestamps, ...)."""
    norm = re.sub(r"[^a-z]", "", key.lower())
    return norm in EXCLUDED_FIELDS


def label_for_key(key: str) -> tuple[str, str]:
    """Returns (emoji, pretty label) for a raw JSON field.
    Checks longer/more specific fragments first so e.g. 'final_kills' is not
    mislabeled as generic 'kills'."""
    norm = re.sub(r"[^a-z]", "", key.lower())
    for fragment, (emoji, label) in sorted(KNOWN_FIELDS.items(), key=lambda kv: -len(kv[0])):
        if fragment in norm:
            return emoji, label
    return "📊", key


def split_game_mode(full_path: str) -> tuple[str, str | None, str]:
    """
    Splits a diff_stats path like 'bed.solo.wins' into
    (game_key='bed', mode_label='Solo', stat_key='wins').
    If no known mode is recognized, mode_label is None and stat_key is
    everything from the second segment onward.
    """
    parts = full_path.split(".")
    game_key = parts[0]
    if len(parts) >= 3 and parts[1].lower() in MODE_ALIASES:
        mode_label = MODE_ALIASES[parts[1].lower()]
        stat_key = ".".join(parts[2:])
    else:
        mode_label = None
        stat_key = ".".join(parts[1:]) if len(parts) > 1 else parts[0]
    return game_key, mode_label, stat_key


def compute_kd(data: dict) -> float | None:
    """Looks for kills/deaths at the top level of a stats dict and computes KD."""
    kills = deaths = None
    for key, value in data.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        norm = re.sub(r"[^a-z]", "", key.lower())
        if norm == "kills":
            kills = value
        elif norm == "deaths":
            deaths = value
    if kills is None or deaths is None:
        return None
    if deaths == 0:
        return float(kills)
    return round(kills / deaths, 2)


# ---------------------------------------------------------------------------
# "Live" win streak: NOT provided by the Hive API itself (see README).
# Tracked client-side here: every detected win increments it, every detected
# non-win round resets it to 0. Based on periodically comparing "wins"/
# "victories" and "played"/"gamesplayed" fields.
# ---------------------------------------------------------------------------

def extract_wins_played(data: dict) -> tuple[float | None, float | None]:
    """Finds wins-like and played-like fields in a flat stats dict."""
    wins = played = None
    for key, value in data.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        norm = re.sub(r"[^a-z]", "", key.lower())
        if norm in ("wins", "victories"):
            wins = value
        elif norm in ("played", "gamesplayed"):
            played = value
    return wins, played


def leaf_stat_dicts(game_data: dict) -> dict[str | None, dict]:
    """
    Splits a game's stats into {mode_label_or_None: flat_stats_dict}.
    If there's no mode split (common on Hive), returns a single entry keyed
    by None.
    """
    if any(k.lower() in MODE_ALIASES for k in game_data.keys()):
        result: dict[str | None, dict] = {}
        for key, value in game_data.items():
            if isinstance(value, dict):
                result[MODE_ALIASES.get(key.lower(), key.capitalize())] = value
        return result
    return {None: game_data}


def update_streak(old_streak: int, delta_played: float, delta_wins: float) -> int:
    """
    Advances a client-side tracked win streak.
    - No new round since the last check -> streak stays the same.
    - All new rounds were wins -> streak increases by delta_wins.
    - At least one new round was not a win -> streak resets to 0
      (conservative assumption if multiple rounds happened within one
      poll interval).
    """
    if delta_played <= 0:
        return old_streak
    if delta_wins >= delta_played:
        return old_streak + int(delta_wins)
    return 0


# ---------------------------------------------------------------------------
# Cyberpunk terminal rendering.
#
# Discord's ```ansi code blocks render a subset of ANSI SGR escape codes as
# actual colors in the Desktop and web clients (format;color, e.g. "1;35" =
# bold magenta). NOT all mobile Discord clients render these — they fall
# back to plain monospace text there, which still looks fine, just not
# colored. There is no way to force color on every platform; this is a
# Discord client limitation, not something the bot can work around.
# ---------------------------------------------------------------------------

def ansi(text: str, code: str) -> str:
    """Wraps text in an ANSI SGR escape code for a ```ansi code block."""
    return f"\x1b[{code}m{text}\x1b[0m"


def _ansi_color_for_label(label: str) -> str:
    l = label.lower()
    if "win" in l:
        return "32"   # green
    if "death" in l or "loss" in l:
        return "31"   # red
    if "kill" in l:
        return "36"   # cyan
    if "streak" in l:
        return "33"   # yellow
    if "level" in l or "prestige" in l or "xp" in l:
        return "35"   # magenta
    return "37"        # white


def ansi_stat_lines(data: dict, limit: int = 8) -> list[str]:
    """Renders the numeric fields of a flat stats dict as color-coded,
    aligned ANSI lines, e.g. 'WINS             142'."""
    lines: list[str] = []
    for key, value in data.items():
        if is_excluded(key):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            _, label = label_for_key(key)
            color = _ansi_color_for_label(label)
            lines.append(f"{ansi(label.upper().ljust(16), f'0;{color}')} {value}")
            if len(lines) >= limit:
                break
    kd = compute_kd(data)
    if kd is not None and len(lines) < limit + 1:
        lines.append(f"{ansi('K/D RATIO'.ljust(16), '0;33')} {kd}")
    return lines


def ansi_banner(lines: list[str], color: str = "35") -> str:
    """A boxed ANSI header banner using box-drawing characters, e.g. for the
    top of a stats/dashboard/alert embed."""
    width = max((len(l) for l in lines), default=0) + 2
    top = "╔" + "═" * width + "╗"
    bottom = "╚" + "═" * width + "╝"
    body = "\n".join(f"║ {l.ljust(width - 1)}║" for l in lines)
    return ansi(f"{top}\n{body}\n{bottom}", f"1;{color}")
