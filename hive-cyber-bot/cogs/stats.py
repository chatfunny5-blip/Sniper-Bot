"""
cogs/stats.py
Slash commands for looking up Hive stats. Renders results as a cyberpunk
"terminal" readout using Discord's ```ansi code-block color support.
Exports build_full_stats_embed(), build_live_dashboard_embed(), and
activity_status() for reuse by cogs/tracking.py (/livestats, /online,
round-finished alerts) so the whole bot shares one visual language.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from hive_api import HiveAPIError
from formatting import (
    label_for_key, compute_kd, MODE_ALIASES, is_excluded,
    ansi, ansi_stat_lines, ansi_banner,
)

log = logging.getLogger("hivebot.stats")

GAME_NAMES = {
    "wars": "Treasure Wars", "dr": "Deathrun", "hide": "Hide & Seek",
    "sg": "Survival Games", "murder": "Murder Mystery", "sky": "SkyWars",
    "ctf": "Capture the Flag", "drop": "Just Drop", "ground": "Ground Wars",
    "build": "Build Battle", "party": "Party Games", "bridge": "The Bridge",
    "grav": "Gravity", "bed": "BedWars",
}

# Keep headroom under Discord's 4096-char embed description limit once the
# ```ansi fences and escape codes are added.
EMBED_DESC_BUDGET = 3600


def _is_mode_split(data: dict) -> bool:
    return any(k.lower() in MODE_ALIASES for k in data.keys())


def _game_block(label: str, mode_label: str | None, block_data: dict, limit: int = 5) -> str:
    header = f"[ {label.upper()}{' :: ' + mode_label.upper() if mode_label else ''} ]"
    lines = ansi_stat_lines(block_data, limit=limit)
    body = "\n".join(lines) if lines else ansi("no displayable fields", "0;37")
    return f"{ansi(header, '1;34')}\n{body}"


def activity_status(last_active_iso: str | None) -> tuple[str, int, str]:
    """Honest, clearly-labeled activity indicator — NOT a real online status
    (the Hive API has no such endpoint). Returns
    (status_line, embed_color, ansi_banner_color)."""
    if last_active_iso is None:
        return "STATUS   UNKNOWN (awaiting first poll cycle)", 0x5A5A5A, "37"

    last_active = datetime.fromisoformat(last_active_iso)
    minutes = int((datetime.now(timezone.utc) - last_active).total_seconds() // 60)

    if minutes < 5:
        return "STATUS   ACTIVE (signal < 5min ago)", 0x39FF14, "32"
    if minutes < 30:
        return f"STATUS   IDLE (signal {minutes}min ago)", 0xFFB000, "33"
    hours = minutes // 60
    tail = f"{hours}h {minutes % 60}min" if hours else f"{minutes}min"
    return f"STATUS   DORMANT (signal {tail} ago)", 0x8B00FF, "35"


def build_full_stats_embed(name: str, data: dict, game: str | None = None) -> discord.Embed:
    """Plain (non-live) stats readout, used by /stats."""
    banner = ansi_banner([f"TARGET   {name.upper()}", "QUERY    COMPLETE"], color="36")
    blocks: list[str] = [banner]
    budget = EMBED_DESC_BUDGET - len(banner)
    omitted = 0

    def _try_add(block: str):
        nonlocal budget, omitted
        if len(block) + 2 > budget:
            omitted += 1
            return
        blocks.append(block)
        budget -= len(block) + 2

    if game:
        label = GAME_NAMES.get(game, game)
        if _is_mode_split(data):
            for mode_key, mode_data in data.items():
                if isinstance(mode_data, dict) and mode_data:
                    mode_label = MODE_ALIASES.get(mode_key.lower(), mode_key.capitalize())
                    _try_add(_game_block(label, mode_label, mode_data, limit=8))
        else:
            _try_add(_game_block(label, None, data, limit=8))
    else:
        for game_key, game_data in data.items():
            if not isinstance(game_data, dict) or not game_data:
                continue
            label = GAME_NAMES.get(game_key, game_key)
            if _is_mode_split(game_data):
                first_mode_key, first_mode_data = next(iter(game_data.items()))
                mode_label = MODE_ALIASES.get(first_mode_key.lower(), first_mode_key.capitalize())
                _try_add(_game_block(label, mode_label, first_mode_data, limit=5))
            else:
                _try_add(_game_block(label, None, game_data, limit=5))

    if omitted:
        blocks.append(ansi(f"... {omitted} more categories omitted — use /stats game:<code> ...", "0;37"))

    embed = discord.Embed(title="⟦ H.I.V.E DATASTREAM ⟧", color=0x00F0FF)
    if len(blocks) == 1 and not omitted:
        blocks.append(ansi("NO DISPLAYABLE FIELDS FOUND — TRY /raw", "0;31"))
    embed.description = f"```ansi\n{(chr(10) + chr(10)).join(blocks)}\n```"
    return embed


def build_live_dashboard_embed(name: str, data: dict, last_active_iso: str | None,
                                poll_interval: int) -> discord.Embed:
    """Themed, continuously-refreshed dashboard embed used by /livestats."""
    status_line, color, banner_color = activity_status(last_active_iso)
    banner = ansi_banner([f"TARGET   {name.upper()}", status_line], color=banner_color)

    blocks: list[str] = [banner]
    budget = EMBED_DESC_BUDGET - len(banner)
    omitted = 0
    total_kills = total_deaths = total_wins = 0

    def _try_add(block: str):
        nonlocal budget, omitted
        if len(block) + 2 > budget:
            omitted += 1
            return
        blocks.append(block)
        budget -= len(block) + 2

    for game_key, game_data in data.items():
        if not isinstance(game_data, dict) or not game_data:
            continue
        label = GAME_NAMES.get(game_key, game_key)
        if _is_mode_split(game_data):
            first_mode_key, block_data = next(iter(game_data.items()))
            mode_label = MODE_ALIASES.get(first_mode_key.lower(), first_mode_key.capitalize())
        else:
            block_data = game_data
            mode_label = None

        for key, value in block_data.items():
            if is_excluded(key) or not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            norm = key.lower()
            if "kill" in norm and "final" not in norm:
                total_kills += value
            elif "death" in norm and "final" not in norm:
                total_deaths += value
            elif norm in ("wins", "victories"):
                total_wins += value

        _try_add(_game_block(label, mode_label, block_data, limit=5))

    overall_kd = round(total_kills / total_deaths, 2) if total_deaths else float(total_kills)
    summary = "\n".join([
        ansi("[ AGGREGATE POWER LEVEL ]", "1;35"),
        f"{ansi('TOTAL WINS'.ljust(16), '0;32')} {total_wins}",
        f"{ansi('TOTAL KILLS'.ljust(16), '0;36')} {total_kills}",
        f"{ansi('OVERALL K/D'.ljust(16), '0;33')} {overall_kd}",
    ])
    _try_add(summary)

    if omitted:
        blocks.append(ansi(f"... {omitted} more categories omitted ...", "0;37"))

    embed = discord.Embed(title="👾 ⟦ NEURAL-LINK :: LIVE FEED ⟧ 👾", color=color)
    embed.description = f"```ansi\n{(chr(10)+chr(10)).join(blocks)}\n```"
    embed.set_footer(text=f"🔴 LIVE · refreshes ~every {poll_interval}s · "
                           f"not a real online status — see /online")
    return embed


class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.hive = bot.hive

    @app_commands.command(description="Show a player's Hive stats")
    @app_commands.describe(
        name="Minecraft Bedrock username",
        game="Game code like bed, sky, wars, murder ... (leave empty for all games)",
    )
    async def stats(self, interaction: discord.Interaction, name: str, game: str | None = None):
        await interaction.response.defer()
        try:
            data = await self.hive.get_game_stats(game, name) if game else await self.hive.get_all_stats(name)
        except HiveAPIError as e:
            await interaction.followup.send(f"⚠️ API error: {e}")
            return
        except Exception:
            log.exception("Unexpected error in /stats for %s", name)
            await interaction.followup.send("⚠️ Something went wrong fetching that player's stats.")
            return

        if data is None:
            await interaction.followup.send(f"❌ Player `{name}` not found.")
            return

        embed = build_full_stats_embed(name, data, game)
        await interaction.followup.send(embed=embed)

    @app_commands.command(description="Show the raw API response (e.g. to find mode/winstreak field names)")
    @app_commands.describe(name="Minecraft Bedrock username", game="Game code like bed, sky, wars ... (leave empty for all games)")
    async def raw(self, interaction: discord.Interaction, name: str, game: str | None = None):
        await interaction.response.defer()
        try:
            data = await self.hive.get_game_stats(game, name) if game else await self.hive.get_all_stats(name)
        except HiveAPIError as e:
            await interaction.followup.send(f"⚠️ API error: {e}")
            return
        except Exception:
            log.exception("Unexpected error in /raw for %s", name)
            await interaction.followup.send("⚠️ Something went wrong fetching that player's data.")
            return
        if data is None:
            await interaction.followup.send(f"❌ Player `{name}` not found.")
            return
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated, use game=<code> to narrow it down)"
        await interaction.followup.send(f"```json\n{text}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
