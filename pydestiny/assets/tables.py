"""Core game data tables extracted from DATA.OVL."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REAGENT_NAMES: tuple[str, ...] = (
    "Sulfurous Ash",
    "Ginseng",
    "Garlic",
    "Spider Silk",
    "Blood Moss",
    "Black Pearl",
    "Nightshade",
    "Mandrake",
)

SEMI_TRANSPARENT_TILES: frozenset[int] = frozenset({0x4A, 0x4B, 0x98, 0xBA, 0xBB})


@dataclass(frozen=True)
class SpellDef:
    index: int
    circle: int
    name: str
    reagent_mask: int
    context_flags: int


@dataclass(frozen=True)
class MonsterDef:
    index: int
    name: str
    strength: int
    dexterity: int
    intelligence: int
    armour: int
    damage: int
    hp: int
    max_spawn: int
    special: int


@dataclass(frozen=True)
class GameTables:
    spells: tuple[SpellDef, ...]
    monsters: tuple[MonsterDef, ...]
    item_names: tuple[str, ...]
    item_attack: bytes
    item_defense: bytes
    item_range: bytes
    foot_impassable_mask: bytes
    opaque_tiles: frozenset[int]
    moon_phases: tuple[tuple[int, int], ...]
    brit_chunk_map: bytes
    tlk_words: dict[int, str]
    location_coords: tuple[tuple[int, int], ...]
    settlement_base_maps: tuple[int, ...]


def _read_cstrings(data: bytes, offset: int, count: int) -> list[str]:
    out: list[str] = []
    p = offset
    for _ in range(count):
        end = data.find(b"\x00", p)
        out.append(data[p:end].decode("ascii", errors="replace"))
        p = end + 1
    return out


def load_game_tables(data_ovl_path: Path) -> GameTables:
    """Load all verified static tables from DATA.OVL."""
    d = data_ovl_path.read_bytes()

    # 48 Spells
    spell_names = _read_cstrings(d, 0x0709, 48)
    reagent_masks = d[0x1CD0 : 0x1CD0 + 48]
    context_flags = d[0x1CA0 : 0x1CA0 + 48]
    spells = tuple(
        SpellDef(
            index=i,
            circle=(i // 6) + 1,
            name=spell_names[i],
            reagent_mask=reagent_masks[i],
            context_flags=context_flags[i],
        )
        for i in range(48)
    )

    # 48 Monster / Actor defs (0..15 NPC classes, 16..47 monsters; slots 42, 43 are unused)
    npc_class_names = _read_cstrings(d, 0x01D3, 15) + ["NPC_15"]
    monster_names = _read_cstrings(d, 0x023E, 30)
    monsters = []
    mname_idx = 0
    for i in range(48):
        rec = d[0x13CC + i * 8 : 0x13CC + (i + 1) * 8]
        if i < 16:
            name = npc_class_names[i]
        elif rec == b"\x00" * 8:
            name = f"Unused_{i}"
        else:
            name = monster_names[mname_idx] if mname_idx < len(monster_names) else f"Monster_{i}"
            mname_idx += 1
        monsters.append(
            MonsterDef(
                index=i,
                name=name,
                strength=rec[0],
                dexterity=rec[1],
                intelligence=rec[2],
                armour=rec[3],
                damage=rec[4],
                hp=rec[5],
                max_spawn=rec[6],
                special=rec[7],
            )
        )

    # Equipment tables (48 items)
    item_names = tuple(_read_cstrings(d, 0x0052, 28))
    item_attack = d[0x1614 : 0x1614 + 48]
    item_defense = d[0x1644 : 0x1644 + 48]
    item_range = d[0x16AC : 0x16AC + 48]

    # Passability & Opacity
    foot_impassable_mask = d[0x54E4 : 0x54E4 + 32]
    opaque_tiles = frozenset(d[0x6A96 : 0x6A96 + 19])

    # Moon phases (days 0..28 -> (trammel, felucca) as 0..7)
    moon_phases = tuple(
        (d[0x1EE8 + day * 2] - 0x30, d[0x1EE8 + day * 2 + 1] - 0x30)
        for day in range(29)
    )

    # BRIT.DAT 16x16 chunk map
    brit_chunk_map = d[0x3886 : 0x3886 + 256]

    # 40 Location (x, y) overworld coordinates (0..31 settlements, 32..39 dungeons)
    loc_xs = d[0x1E9A : 0x1E9A + 40]
    loc_ys = d[0x1EC2 : 0x1EC2 + 40]
    location_coords = tuple((loc_xs[i], loc_ys[i]) for i in range(40))

    # 32 Settlement base map indices into TOWNE/DWELLING/CASTLE/KEEP.DAT (DATA.OVL+0x1e2a)
    settlement_base_maps = tuple(d[0x1E2A + i] for i in range(32))

    # .TLK word dictionary (0x24F8 + idx*2, string pool +0x10)
    import struct

    tlk_words: dict[int, str] = {}
    for i in range(1, 128):
        ptr = struct.unpack_from("<H", d, 0x24F8 + i * 2)[0]
        if ptr == 0xFFFF or ptr < 0x1000 or ptr > 0x2400:
            continue
        p = ptr + 0x10
        end = d.find(b"\x00", p)
        tlk_words[i] = d[p:end].decode("ascii", errors="replace")

    return GameTables(
        spells=spells,
        monsters=tuple(monsters),
        item_names=item_names,
        item_attack=item_attack,
        item_defense=item_defense,
        item_range=item_range,
        foot_impassable_mask=foot_impassable_mask,
        opaque_tiles=opaque_tiles,
        moon_phases=moon_phases,
        brit_chunk_map=brit_chunk_map,
        tlk_words=tlk_words,
        location_coords=location_coords,
        settlement_base_maps=settlement_base_maps,
    )
