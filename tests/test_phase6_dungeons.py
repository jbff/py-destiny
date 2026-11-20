"""Phase 6 tests: 3D dungeons, movement/ladders, dungeon rooms, and 3D slice rendering."""

from __future__ import annotations

import os

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


class TestPhase6Dungeons:
    def test_enter_navigate_klimb_and_exit_dungeon(self) -> None:
        session = OverworldSession.from_data_dir()
        ox, oy = session.tables.location_coords[32]  # Deceit
        session.save.x, session.save.y = ox, oy
        assert session.enter_location()
        assert session.dungeon is not None
        assert session.dungeon.name == "Deceit"
        assert session.dungeon.z == 0
        assert (session.dungeon.current_cell() & 0xF0) == 0x10

        # Turning updates facing without moving
        f0 = session.dungeon.facing
        assert session.step_move(1, 0)
        assert session.dungeon.facing == (f0 + 1) % 4
        assert session.step_move(-1, 0)
        assert session.dungeon.facing == f0

        # Moving forward in facing direction
        assert session.step_move(0, -1)

        # Return to ladder up and klimb out to Britannia
        assert session.step_move(0, 1)
        assert session.klimb_dungeon(up=True)
        assert session.dungeon is None
        assert (session.save.x, session.save.y) == (ox, oy)

    def test_dungeon_ladder_down_and_room_combat(self) -> None:
        session = OverworldSession.from_data_dir()
        ox, oy = session.tables.location_coords[32]
        session.save.x, session.save.y = ox, oy
        assert session.enter_location()
        assert session.dungeon is not None

        # Place on a 0x20 ladder down cell and descend
        found_down = None
        for ry in range(8):
            for rx in range(8):
                if (session.dungeon.cell_at(rx, ry, 0) & 0xF0) == 0x20:
                    found_down = (rx, ry)
                    break
            if found_down:
                break
        assert found_down is not None
        session.dungeon.x, session.dungeon.y = found_down
        assert session.klimb_dungeon(up=False)
        assert session.dungeon.z == 1
        assert session.save.z == 1

        # Trigger dungeon room combat
        cbt = session.start_dungeon_room(0)
        assert cbt is not None
        assert session.combat is cbt

    def test_render_3d_dungeon(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))
        try:
            session = OverworldSession.from_data_dir()
            ox, oy = session.tables.location_coords[32]
            session.save.x, session.save.y = ox, oy
            assert session.enter_location()

            renderer = EgaRenderer()
            surf = renderer.render_overworld(session)
            assert surf.get_size() == (SCREEN_W, SCREEN_H)
            # Verify 3D viewport has drawn non-black wall/ladder pixels
            non_black = sum(
                1
                for y in range(24, 176, 4)
                for x in range(16, 176, 4)
                if surf.get_at((x, y))[:3] != (0, 0, 0)
            )
            assert non_black > 0
        finally:
            pygame.quit()
