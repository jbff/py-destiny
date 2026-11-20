"""Loaders for the extracted open JSON data under data/ (independent of orig/)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydestiny.assets.tables import MonsterDef, SpellDef

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass(frozen=True)
class OpenTables:
    spells: tuple[SpellDef, ...]
    monsters: tuple[MonsterDef, ...]
    item_names: tuple[str, ...]
    item_attack: tuple[int, ...]
    item_defense: tuple[int, ...]
    item_range: tuple[int, ...]
    foot_impassable_tiles: frozenset[int]
    opaque_tiles: frozenset[int]
    moon_phases: tuple[tuple[int, int], ...]


def load_open_tables(data_dir: Path = DEFAULT_DATA_DIR) -> OpenTables:
    raw = json.loads((data_dir / "tables.json").read_text(encoding="utf-8"))
    return OpenTables(
        spells=tuple(SpellDef(**s) for s in raw["spells"]),
        monsters=tuple(MonsterDef(**m) for m in raw["monsters"]),
        item_names=tuple(raw["item_names"]),
        item_attack=tuple(raw["item_attack"]),
        item_defense=tuple(raw["item_defense"]),
        item_range=tuple(raw["item_range"]),
        foot_impassable_tiles=frozenset(raw["foot_impassable_tiles"]),
        opaque_tiles=frozenset(raw["opaque_tiles"]),
        moon_phases=tuple((p[0], p[1]) for p in raw["moon_phases"]),
    )


def load_open_grid(path: Path) -> list[list[int]]:
    return json.loads(path.read_text(encoding="utf-8"))
