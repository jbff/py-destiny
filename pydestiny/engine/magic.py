"""Reagent mixing (CMDS.OVL+0x1ad8) and spell casting validation (CAST.OVL+0x0dba)."""

from __future__ import annotations

from pydestiny.assets.tables import SpellDef
from pydestiny.state.savegame import SaveGame

SPELL_CAP = 99

CTX_COMBAT = 0x01
CTX_OVERWORLD = 0x08


def max_mixable(save: SaveGame, reagent_mask: int) -> int:
    """Compute maximum number of casts mixable from current reagents."""
    if reagent_mask == 0:
        return 0
    counts = [save.reagents[i] for i in range(8) if reagent_mask & (0x80 >> i)]
    return min(counts) if counts else 0


def mix_reagents(save: SaveGame, spell: SpellDef, reagent_mask: int, qty: int) -> bool:
    """Attempt to mix `qty` doses of `spell` using `reagent_mask`.

    Reagents are always consumed; prepared spell count increases only if
    `reagent_mask == spell.reagent_mask`.
    """
    if qty <= 0 or max_mixable(save, reagent_mask) < qty:
        return False

    for i in range(8):
        if reagent_mask & (0x80 >> i):
            save.reagents[i] -= qty

    if reagent_mask == spell.reagent_mask:
        new_val = min(SPELL_CAP, save.prepared_spells[spell.index] + qty)
        save.prepared_spells[spell.index] = new_val
        return True
    return False


def can_cast_spell(
    save: SaveGame,
    caster_idx: int,
    spell: SpellDef,
    context_bit: int,
) -> tuple[bool, str]:
    """Validate castability per CAST.OVL+0x0dba."""
    if not (spell.context_flags & context_bit):
        return False, "Not castable here"
    if save.prepared_spells[spell.index] <= 0:
        return False, "None mixed"
    caster = save.characters[caster_idx]
    if caster.mp < spell.circle:
        return False, "Not enough MP"
    if caster.level < spell.circle:
        return False, "Level too low"
    return True, "OK"


def consume_spell_cost(save: SaveGame, caster_idx: int, spell: SpellDef) -> None:
    """Deduct 1 prepared spell and `spell.circle` MP."""
    save.prepared_spells[spell.index] -= 1
    save.characters[caster_idx].mp -= spell.circle
