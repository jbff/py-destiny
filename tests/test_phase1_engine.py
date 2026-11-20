"""Phase 1 tests: headless simulation rules tested against open JSON data/."""

from __future__ import annotations

import random

from pydestiny.assets.open_data import DEFAULT_DATA_DIR, load_open_grid, load_open_tables
from pydestiny.engine.combat_math import (
    apply_party_damage,
    award_exp,
    check_hit,
    effective_dex,
    euclidean_dist,
    roll_1d30,
)
from pydestiny.engine.fov import UNSEEN_TILE, compute_fov
from pydestiny.engine.karma import (
    KARMA_ATTACK_FRIENDLY,
    KARMA_LOCKPICK_SETTLEMENT,
    adjust_karma,
)
from pydestiny.engine.magic import CTX_OVERWORLD, can_cast_spell, consume_spell_cost, mix_reagents
from pydestiny.engine.movement import is_foot_passable, is_water_passable, wrap_world_coord
from pydestiny.engine.time import (
    advance_time,
    get_moon_sky_positions,
    update_darkness,
)
from pydestiny.state.savegame import SaveGame


def _load_init_save() -> SaveGame:
    return SaveGame.load_json(DEFAULT_DATA_DIR / "init_save.json")


class TestPhase1Engine:
    def test_time_calendar_and_moons(self) -> None:
        tables = load_open_tables()
        sg = _load_init_save()
        # Init: year=139, month=4, day=5, hour=8, minute=35
        t, f = advance_time(sg, 30, tables.moon_phases)
        assert sg.minute == 5 and sg.hour == 9
        assert (t, f) == tables.moon_phases[5]

        # Quicken ('Q') halves minutes
        sg.active_spell = ord("Q")
        advance_time(sg, 10, tables.moon_phases)
        assert sg.minute == 10

        # Time Stop ('T') freezes time
        sg.active_spell = ord("T")
        advance_time(sg, 120, tables.moon_phases)
        assert sg.minute == 10 and sg.hour == 9

        # Roll over month (28 days) and year (13 months)
        sg.active_spell = 0
        sg.month = 13
        sg.day = 28
        sg.hour = 23
        sg.minute = 50
        sg.characters[0].months_in_party = 3
        advance_time(sg, 15, tables.moon_phases)
        assert (sg.year, sg.month, sg.day, sg.hour, sg.minute) == (140, 1, 1, 0, 5)
        assert sg.characters[0].months_in_party == 4

        # Sky visibility
        assert get_moon_sky_positions(8) == (0, None)   # Trammel rising at 8, Felucca below horizon
        assert get_moon_sky_positions(2) == (6, 0)      # Both visible at 2am

        # Day/night darkness
        assert update_darkness(0, 22) == 1
        assert update_darkness(16, 23) == 16
        assert update_darkness(5, 12) == 4
        assert update_darkness(0, 12) == 0

    def test_fov_and_opacity(self) -> None:
        tables = load_open_tables()
        # Empty grass (0x04) with a stone wall (0x4f) at (6, 5)
        def get_tile(x: int, y: int) -> int:
            if (x, y) == (6, 5):
                return 0x4F
            return 0x04

        fov = compute_fov(get_tile, 5, 5, light_radius=5, opaque_tiles=tables.opaque_tiles)
        assert fov[5][5] == 0x04
        assert fov[5][6] == 0x4F
        # Behind wall at (7, 5) and (8, 5) should still be reachable only if another path wraps around;
        # test a full vertical wall blocking the right half completely:
        def wall_col(x: int, y: int) -> int:
            return 0x4F if x == 6 else 0x04

        fov2 = compute_fov(wall_col, 5, 5, light_radius=5, opaque_tiles=tables.opaque_tiles)
        assert fov2[5][6] == 0x4F
        assert fov2[5][7] == UNSEEN_TILE
        assert fov2[5][4] == 0x04

        # Semi-transparent tile (0x4a) visible at dist=1, blocks beyond
        def forest_wall(x: int, y: int) -> int:
            return 0x4A if x >= 6 else 0x04

        fov3 = compute_fov(forest_wall, 5, 5, light_radius=5, opaque_tiles=tables.opaque_tiles)
        assert fov3[5][6] == 0x4A  # dist=1 -> seen & transparent
        assert fov3[5][7] == 0x4A  # dist=2 -> seen, but opaque -> blocks (8,5)
        assert fov3[5][8] == UNSEEN_TILE

    def test_movement_and_passability(self) -> None:
        tables = load_open_tables()
        brit = load_open_grid(DEFAULT_DATA_DIR / "maps" / "brit.json")
        # Grass (0x04) is foot-passable, deep water (0x01) is not
        assert is_foot_passable(0x04, tables.foot_impassable_tiles)
        assert not is_foot_passable(brit[0][0], tables.foot_impassable_tiles)
        assert is_water_passable(brit[0][0])
        assert not is_water_passable(0x04)
        assert wrap_world_coord(-1, 256) == (255, 0)

    def test_karma(self) -> None:
        sg = _load_init_save()
        assert sg.karma == 75
        assert adjust_karma(sg, KARMA_LOCKPICK_SETTLEMENT) == 73
        assert adjust_karma(sg, KARMA_ATTACK_FRIENDLY) == 68
        assert adjust_karma(sg, -200) == 0
        assert adjust_karma(sg, 200) == 99

    def test_magic_mix_and_cast(self) -> None:
        tables = load_open_tables()
        sg = _load_init_save()
        in_lor = tables.spells[0]  # Circle 1, Ash (0x80)
        assert sg.reagents[0] == 4  # Sulfurous Ash
        before = sg.prepared_spells[0]
        assert mix_reagents(sg, in_lor, 0x80, 2)
        assert sg.reagents[0] == 2
        assert sg.prepared_spells[0] == before + 2

        # Wrong recipe consumes reagents without adding spell
        assert not mix_reagents(sg, in_lor, 0x40, 1)
        assert sg.reagents[1] == 5

        # Cast In Lor with Mariah (char 3, Mage, MP=22, Level=3) in Overworld
        ok, _ = can_cast_spell(sg, 3, in_lor, CTX_OVERWORLD)
        assert ok
        consume_spell_cost(sg, 3, in_lor)
        assert sg.characters[3].mp == 21
        assert sg.prepared_spells[0] == before + 1

    def test_combat_math(self) -> None:
        assert euclidean_dist(0, 0, 3, 4) == 5
        assert euclidean_dist(0, 0, 1, 1) == 1
        assert effective_dex(20, 0x40, ord("T")) == 1
        assert effective_dex(20, 0x08, 0) == 1
        assert effective_dex(20, 0x40, 0) == 20

        rng = random.Random(42)
        r = roll_1d30(rng)
        assert 1 <= r <= 29
        assert check_hit(20, 10, 19) is True   # threshold = (20-10+30)//2 = 20
        assert check_hit(20, 10, 20) is False

        sg = _load_init_save()
        shamino = sg.characters[1]
        assert not apply_party_damage(shamino, 3)
        assert shamino.hp == 2 and shamino.status == "G"
        assert apply_party_damage(shamino, 10)
        assert shamino.hp == 0 and shamino.status == "D"

        assert award_exp(shamino, 50000) == 9999
