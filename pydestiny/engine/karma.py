"""Karma rules and modifiers (DS:[0x5888])."""

from __future__ import annotations

from pydestiny.state.savegame import SaveGame

KARMA_MIN = 0
KARMA_MAX = 99

KARMA_LOCKPICK_SETTLEMENT = -2  # SJOG.OVL+0x11f0
KARMA_STEAL_ITEM = -1           # SJOG.OVL+0x1a50
KARMA_ATTACK_FRIENDLY = -5      # TOWN.OVL+0x0ae8


def adjust_karma(save: SaveGame, delta: int) -> int:
    """Adjust karma clamped to 0..99 and return the new karma value."""
    save.karma = max(KARMA_MIN, min(KARMA_MAX, save.karma + delta))
    return save.karma
