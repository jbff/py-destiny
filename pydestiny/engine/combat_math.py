"""Combat math: distance, effective DEX, hit/miss, damage/death, EXP (COMBAT.OVL / COMSUBS.OVL)."""

from __future__ import annotations

import random

from pydestiny.state.savegame import CharacterRecord

EXP_CAP = 9999


def euclidean_dist(x1: int, y1: int, x2: int, y2: int) -> int:
    """Integer Euclidean distance matching COMSUBS.OVL+0x048a."""
    dx = x1 - x2
    dy = y1 - y2
    sq = dx * dx + dy * dy
    odd = 1
    dist = 0
    while sq >= odd:
        sq -= odd
        odd += 2
        dist += 1
    return dist


def effective_dex(
    base_dex: int,
    flags: int,
    active_spell: int,
    actor_type: int = 0,
) -> int:
    """Matches COMBAT.OVL+0x139a:
    - Time Stop ('T' = 0x54) on enemies (flags & 0x40) -> 1
    - Actor type 0x1a or asleep/paralyzed (flags & 0x08) -> 1
    """
    if active_spell == ord("T") and (flags & 0x40):
        return 1
    if actor_type == 0x1A or (flags & 0x08):
        return 1
    return base_dex


def roll_1d30(rng: random.Random | None = None) -> int:
    """Matches 0x0000:0x3abe: (rand() % 60) >> 1, clamped >= 1 (range 1..29)."""
    r = rng.randrange(60) if rng else random.randrange(60)
    val = r >> 1
    return 1 if val == 0 else val


def check_hit(att_stat: int, def_stat: int, roll: int) -> bool:
    """Matches COMBAT.OVL+0x14d6:
    threshold = (att_stat - def_stat + 30) // 2
    Returns True if roll < threshold (0 = HIT in original), False on MISS.
    """
    threshold = (att_stat - def_stat + 30) // 2
    return roll < threshold


def apply_party_damage(char: CharacterRecord, dmg: int) -> bool:
    """Apply `dmg` to a party member per COMBAT.OVL+0x1574. Returns True if killed."""
    if dmg < 1:
        return False
    char.hp -= dmg
    if char.hp < 1 or dmg == 99:
        char.hp = 0
        char.status = "D"
        return True
    return False


def award_exp(char: CharacterRecord, xp_gain: int) -> int:
    """Award EXP capped at 9999 per COMBAT.OVL+0x1934."""
    char.exp = min(EXP_CAP, char.exp + max(0, xp_gain))
    return char.exp
