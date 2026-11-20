"""Phase 2 tests: OverworldSession and headless EgaRenderer verification."""

from __future__ import annotations

import os
from pathlib import Path

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


class TestPhase2Overworld:
    def test_overworld_session_move_look_save(self, tmp_path: Path) -> None:
        session = OverworldSession.from_data_dir()
        assert session.save.location_id == 0
        start_x, start_y = session.save.x, session.save.y
        start_min = session.save.minute

        # Look at current tile
        desc = session.look_at(0, 0)
        assert len(desc) > 0
        assert any("Thou dost see" in m for m in session.messages)

        # Pass advances 2 minutes
        session.pass_turn()
        assert session.save.minute == (start_min + 2) % 60

        # Try moving in one of the 4 cardinal directions
        moved = False
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if session.step_move(dx, dy):
                moved = True
                assert (session.save.x, session.save.y) == (
                    (start_x + dx) & 0xFF,
                    (start_y + dy) & 0xFF,
                )
                break
        assert moved

        # Save & reload JSON
        save_path = tmp_path / "test_save.json"
        session.save.save_json(save_path)
        session2 = OverworldSession.from_data_dir(save_path=save_path)
        assert (session2.save.x, session2.save.y) == (session.save.x, session.save.y)

    def test_headless_ega_renderer(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))
        try:
            session = OverworldSession.from_data_dir()
            renderer = EgaRenderer()
            surf = renderer.render_overworld(session)
            assert surf.get_size() == (SCREEN_W, SCREEN_H)

            session.ztats_open = True
            surf_ztats = renderer.render_overworld(session)
            assert surf_ztats.get_size() == (SCREEN_W, SCREEN_H)
        finally:
            pygame.quit()
