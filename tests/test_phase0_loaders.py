"""Phase 0 tests: verify all binary asset loaders and SaveGame round-trip against orig/extracted/."""

from __future__ import annotations

import pytest

from pydestiny import DEFAULT_ORIG_DIR
from pydestiny.assets.graphics import (
    load_font_8x8,
    load_image_container,
    load_tileset16,
)
from pydestiny.assets.lzw import lzw_decompress
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

ORIG = DEFAULT_ORIG_DIR


@pytest.mark.skipif(not ORIG.exists(), reason="orig/extracted not present")
class TestPhase0Loaders:
    def test_lzw_all_compressed_graphics(self) -> None:
        files = sorted(list(ORIG.glob("*.16")) + list(ORIG.glob("*.4")) + list(ORIG.glob("*.BIT")))
        assert len(files) == 55
        for p in files:
            if p.name == "WD.BIT":
                continue
            dec = lzw_decompress(p.read_bytes())
            assert len(dec) > 0

    def test_tileset16_and_fonts(self) -> None:
        tiles = load_tileset16(ORIG / "TILES.16")
        assert len(tiles) == 512
        assert all(len(t) == 256 and max(t) <= 15 for t in tiles)

        ibm = load_font_8x8(ORIG / "IBM.CH")
        runes = load_font_8x8(ORIG / "RUNES.CH")
        assert len(ibm) == 128 and len(runes) == 128
        assert len(ibm[ord("A")]) == 8

    def test_image_containers(self) -> None:
        items = load_image_container(ORIG / "ITEMS.16")
        assert len(items) == 40  # 20 image+mask pairs
        assert (items[0].width, items[0].height) == (40, 80)

        create = load_image_container(ORIG / "CREATE.16")
        assert len(create) == 11
        assert (create[0].width, create[0].height) == (168, 96)

        dng1 = load_image_container(ORIG / "DNG1.16")
        assert len(dng1) == 28

        title = load_image_container(ORIG / "TITLE.BIT")
        assert len(title) == 10

        wd = load_image_container(ORIG / "WD.BIT", compressed=False)
        assert len(wd) == 1 and (wd[0].width, wd[0].height) == (288, 49)

    def test_data_ovl_tables(self) -> None:
        tables = load_game_tables(ORIG / "DATA.OVL")
        assert len(tables.spells) == 48
        assert tables.spells[0].name == "In Lor"
        assert tables.spells[0].reagent_mask == 0x80
        assert tables.spells[1].name == "Grav Por"
        assert tables.spells[1].reagent_mask == 0x84

        assert len(tables.monsters) == 48
        assert tables.monsters[16].name == "Sea Horse"
        assert tables.monsters[47].name == "Shadow Lord"
        assert tables.monsters[47].hp == 99

        assert len(tables.opaque_tiles) == 19
        assert 0x4F in tables.opaque_tiles

        assert len(tables.moon_phases) == 29
        assert tables.moon_phases[1] == (0, 0)

    def test_maps_and_npcs(self) -> None:
        tables = load_game_tables(ORIG / "DATA.OVL")
        brit = load_brit_map(ORIG / "BRIT.DAT", tables.brit_chunk_map)
        assert len(brit) == 256 and all(len(r) == 256 for r in brit)
        assert brit[0][0] == 0x01  # ocean

        under = load_under_map(ORIG / "UNDER.DAT")
        assert len(under) == 256 and under[0][0] == 0x0C

        towne = load_settlement_maps(ORIG / "TOWNE.DAT")
        assert len(towne) == 16 and len(towne[0]) == 32 and len(towne[0][0]) == 32

        dng = load_dungeon_maps(ORIG / "DUNGEON.DAT")
        assert len(dng) == 8 and len(dng[0]) == 8 and len(dng[0][0]) == 8

        brit_cbt = load_combat_maps(ORIG / "BRIT.CBT")
        dng_cbt = load_combat_maps(ORIG / "DUNGEON.CBT")
        assert len(brit_cbt) == 16 and len(dng_cbt) == 112
        assert len(brit_cbt[0].tiles) == 11

        npcs = load_npc_schedules(ORIG / "TOWNE.NPC")
        assert len(npcs) == 8 and len(npcs[0]) == 32
        assert npcs[0][3].talk_id == 1  # Zachariah in Moonglow

    def test_text_and_dialogue(self) -> None:
        tables = load_game_tables(ORIG / "DATA.OVL")
        castle_tlk = load_tlk(ORIG / "CASTLE.TLK", tables.tlk_words)
        assert 1 in castle_tlk
        assert "Alistair the Bard" in castle_tlk[1]

        look2 = load_look2(ORIG / "LOOK2.DAT")
        assert len(look2) == 512

        signs = load_signs(ORIG / "SIGNS.DAT")
        assert len(signs) == 0x42

        questions = load_delimited_blocks(ORIG / "QUESTION.DAT")
        assert len(questions) > 0

        shoppe = load_shoppe_strings(ORIG / "SHOPPE.DAT", tables.tlk_words)
        assert "Thanks for nothing" in shoppe[0]

    def test_savegame_round_trip(self) -> None:
        init_path = ORIG / "__support" / "save" / "INIT.GAM"
        raw = init_path.read_bytes()
        sg = SaveGame(raw)
        assert sg.to_bytes() == raw

        assert sg.characters[1].name == "Shamino"
        assert sg.characters[2].name == "Iolo"
        assert sg.food == 63
        assert sg.gold == 150
        assert sg.year == 139
        assert sg.month == 4
        assert sg.day == 5
        assert sg.hour == 8
        assert sg.karma == 75
        assert sg.location_id == 13
        assert sg.x == 15 and sg.y == 15


def test_savegame_json_round_trip(tmp_path) -> None:
    from pathlib import Path

    init_json = Path(__file__).resolve().parent.parent / "data" / "init_save.json"
    sg = SaveGame.load_json(init_json)
    out_path = tmp_path / "save.json"
    sg.save_json(out_path)
    sg2 = SaveGame.load_json(out_path)
    assert sg2.to_dict() == sg.to_dict()
    assert sg2.characters[1].name == "Shamino"
    assert sg2.karma == 75

