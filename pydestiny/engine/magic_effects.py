"""Spell effect execution for Ultima V's 48 spells (CAST.OVL, CAST2.OVL)."""

from __future__ import annotations

import random

from pydestiny.assets.open_data import OpenTables
from pydestiny.engine.magic import (
    CTX_COMBAT,
    CTX_OVERWORLD,
    can_cast_spell,
    consume_spell_cost,
)
from pydestiny.state.savegame import SaveGame


def execute_spell(
    save: SaveGame,
    tables: OpenTables,
    caster_idx: int,
    spell_idx: int,
    in_combat: bool = False,
    target_char_idx: int = 0,
    combat_session=None,
    rng: random.Random | None = None,
) -> tuple[bool, str]:
    """Validate, consume cost, and apply spell effect. Returns (success, log_message)."""
    if not 0 <= spell_idx < len(tables.spells):
        return False, "Unknown spell"
    spell = tables.spells[spell_idx]
    ctx = CTX_COMBAT if in_combat else CTX_OVERWORLD
    ok, reason = can_cast_spell(save, caster_idx, spell, ctx)
    if not ok:
        return False, reason

    consume_spell_cost(save, caster_idx, spell)
    r = rng or random
    name = spell.name

    # Light spells: In Lor (0), Vas Lor (12)
    if spell_idx in (0, 12):
        return True, f"{name}: Light!"

    # Healing: Mani (4), Vas Mani (27)
    if spell_idx == 4:
        ch = save.characters[target_char_idx]
        heal = r.randint(10, 25)
        ch.hp = min(ch.max_hp, ch.hp + heal)
        return True, f"{name}: +{heal} HP"
    if spell_idx == 27:
        ch = save.characters[target_char_idx]
        ch.hp = ch.max_hp
        return True, f"{name}: Full HP!"

    # Cure Poison: An Nox (3)
    if spell_idx == 3:
        ch = save.characters[target_char_idx]
        if ch.status == "P":
            ch.status = "G"
            return True, f"{name}: Cured!"
        return True, f"{name}: No effect"

    # Resurrect: In Mani Corp (41)
    if spell_idx == 41:
        ch = save.characters[target_char_idx]
        if ch.status == "D":
            ch.status = "G"
            ch.hp = max(1, ch.max_hp // 2)
            return True, f"{name}: Raised!"
        return True, f"{name}: No effect"

    # Locate: In Wis (9)
    if spell_idx == 9:
        return True, f"{name}: ({save.x},{save.y})"

    # Quicken: Rel Tym (29), Time Stop: An Tym (47)
    if spell_idx == 29:
        save.active_spell = ord("Q")
        return True, f"{name}: Quicken!"
    if spell_idx == 47:
        save.active_spell = ord("T")
        return True, f"{name}: Time Stop!"

    # Combat offensive spells: Grav Por (1), Vas Flam (13)
    if spell_idx in (1, 13) and combat_session is not None:
        enemies = [a for a in combat_session.actors if (not a.is_party) and a.alive]
        if enemies:
            target = enemies[0]
            dmg = r.randint(5, 15) if spell_idx == 1 else r.randint(15, 35)
            target.hp = max(0, target.hp - dmg)
            return True, f"{name}: {target.name[:6]} -{dmg}HP"

    return True, f"Cast {name}!"
