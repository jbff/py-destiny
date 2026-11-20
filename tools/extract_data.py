#!/usr/bin/env python3
"""Extract original Ultima V binary files into open JSON formats under data/."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydestiny import DEFAULT_ORIG_DIR
from pydestiny.assets.graphics import load_font_8x8
from pydestiny.assets.maps import (
    load_brit_map,
    load_combat_maps,
    load_dungeon_maps,
    load_npc_schedules,
    load_settlement_maps,
    load_under_map,
)
from pydestiny.assets.tables import load_game_tables
from pydestiny.assets.text import (
    load_delimited_blocks,
    load_look2,
    load_shoppe_strings,
    load_signs,
    load_tlk,
)
from pydestiny.state.savegame import SaveGame

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def extract_all(orig: Path = DEFAULT_ORIG_DIR, out: Path = DEFAULT_OUT_DIR) -> None:
    out.mkdir(parents=True, exist_ok=True)
    tables = load_game_tables(orig / "DATA.OVL")

    # 1. Game tables -> data/tables.json
    tables_json = {
        "spells": [asdict(s) for s in tables.spells],
        "monsters": [asdict(m) for m in tables.monsters],
        "item_names": list(tables.item_names),
        "item_attack": list(tables.item_attack),
        "item_defense": list(tables.item_defense),
        "item_range": list(tables.item_range),
        "foot_impassable_tiles": [
            tid
            for tid in range(256)
            if tables.foot_impassable_mask[tid >> 3] & (0x80 >> (tid & 7))
        ],
        "opaque_tiles": sorted(tables.opaque_tiles),
        "moon_phases": [list(p) for p in tables.moon_phases],
        "location_coords": [list(c) for c in tables.location_coords],
        "settlement_base_maps": list(tables.settlement_base_maps),
    }
    (out / "tables.json").write_text(json.dumps(tables_json, indent=2) + "\n", encoding="utf-8")

    # 2. Maps -> data/maps/
    maps_dir = out / "maps"
    maps_dir.mkdir(exist_ok=True)
    (maps_dir / "brit.json").write_text(
        json.dumps([list(r) for r in load_brit_map(orig / "BRIT.DAT", tables.brit_chunk_map)]),
        encoding="utf-8",
    )
    (maps_dir / "under.json").write_text(
        json.dumps([list(r) for r in load_under_map(orig / "UNDER.DAT")]),
        encoding="utf-8",
    )
    for name in ("CASTLE", "TOWNE", "KEEP", "DWELLING"):
        smaps = load_settlement_maps(orig / f"{name}.DAT")
        (maps_dir / f"{name.lower()}.json").write_text(
            json.dumps([[list(r) for r in m] for m in smaps]),
            encoding="utf-8",
        )
    dngs = load_dungeon_maps(orig / "DUNGEON.DAT")
    (maps_dir / "dungeon.json").write_text(
        json.dumps([[[list(r) for r in lvl] for lvl in d] for d in dngs]),
        encoding="utf-8",
    )
    for cbt in ("BRIT", "DUNGEON"):
        cmaps = load_combat_maps(orig / f"{cbt}.CBT")
        (maps_dir / f"{cbt.lower()}_cbt.json").write_text(
            json.dumps(
                [
                    {
                        "tiles": [list(r) for r in cm.tiles],
                        "party_start_x": list(cm.party_start_x),
                        "monster_types": list(cm.monster_types),
                        "monster_x": list(cm.monster_x),
                        "monster_y": list(cm.monster_y),
                    }
                    for cm in cmaps
                ]
            ),
            encoding="utf-8",
        )

    # 3. NPCs & Dialogue -> data/npcs/, data/dialogue/
    npcs_dir = out / "npcs"
    tlk_dir = out / "dialogue"
    npcs_dir.mkdir(exist_ok=True)
    tlk_dir.mkdir(exist_ok=True)
    for name in ("CASTLE", "TOWNE", "KEEP", "DWELLING"):
        scheds = load_npc_schedules(orig / f"{name}.NPC")
        (npcs_dir / f"{name.lower()}.json").write_text(
            json.dumps(
                [
                    [
                        {
                            "ai_types": list(n.ai_types),
                            "x": list(n.x),
                            "y": list(n.y),
                            "z": list(n.z),
                            "times": list(n.times),
                            "sprite": n.sprite,
                            "talk_id": n.talk_id,
                        }
                        for n in s
                    ]
                    for s in scheds
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        tlk = load_tlk(orig / f"{name}.TLK", tables.tlk_words)
        (tlk_dir / f"{name.lower()}.json").write_text(
            json.dumps({str(k): v for k, v in tlk.items()}, indent=2) + "\n",
            encoding="utf-8",
        )

    # 4. Text -> data/text/
    text_dir = out / "text"
    text_dir.mkdir(exist_ok=True)
    (text_dir / "look2.json").write_text(json.dumps(load_look2(orig / "LOOK2.DAT"), indent=2) + "\n", encoding="utf-8")
    (text_dir / "signs.json").write_text(json.dumps(load_signs(orig / "SIGNS.DAT"), indent=2) + "\n", encoding="utf-8")
    (text_dir / "shoppe.json").write_text(
        json.dumps(load_shoppe_strings(orig / "SHOPPE.DAT", tables.tlk_words), indent=2) + "\n",
        encoding="utf-8",
    )
    for name in ("QUESTION", "STORY", "END"):
        (text_dir / f"{name.lower()}.json").write_text(
            json.dumps(load_delimited_blocks(orig / f"{name}.DAT"), indent=2) + "\n",
            encoding="utf-8",
        )

    # 5. Fonts -> data/font_ibm.json, data/font_runes.json
    (out / "font_ibm.json").write_text(
        json.dumps([list(g) for g in load_font_8x8(orig / "IBM.CH")]),
        encoding="utf-8",
    )
    (out / "font_runes.json").write_text(
        json.dumps([list(g) for g in load_font_8x8(orig / "RUNES.CH")]),
        encoding="utf-8",
    )

    # 6. Initial save -> data/init_save.json
    sg = SaveGame.from_file(orig / "__support" / "save" / "INIT.GAM")
    sg.save_json(out / "init_save.json")
    print(f"Extracted all open JSON assets to {out}")


if __name__ == "__main__":
    extract_all()
