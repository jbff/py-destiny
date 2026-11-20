"""Phase 3 tests: settlements, NPC schedules, dialogue engine, and enter/exit."""

from __future__ import annotations

import os

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.engine.settlement import resolve_schedule_slot
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


class TestPhase3Settlements:
    def test_npc_schedule_resolution(self) -> None:
        # Zachariah in Moonglow: times = [21, 9, 17, 18]
        times = [21, 9, 17, 18]
        assert resolve_schedule_slot(times, 8) == 0   # night
        assert resolve_schedule_slot(times, 10) == 1  # morning
        assert resolve_schedule_slot(times, 17) == 2  # evening
        assert resolve_schedule_slot(times, 18) == 1  # back to slot 1

    def test_enter_talk_exit_moonglow(self) -> None:
        session = OverworldSession.from_data_dir()
        # Move to Moonglow entrance (232, 135)
        session.save.x, session.save.y = 232, 135
        assert session.enter_location()
        assert session.settlement is not None
        assert session.save.location_id == 1

        # Find Zachariah (talk_id == 1)
        zach = next(n for n in session.settlement.npcs if n.talk_id == 1)
        session.save.x = zach.x
        session.save.y = zach.y + 1
        session.save.z = zach.z
        assert session.start_talk(0, -1)
        assert session.talk_session is not None
        assert "Zachariah" in session.submit_talk("name")
        assert "stars" in session.submit_talk("job")
        assert "planets" in session.submit_talk("star")
        assert "Good journeys" in session.submit_talk("bye")
        assert session.talk_session is None

        # Exit by stepping off south edge (y=32)
        session.save.x, session.save.y = 15, 31
        assert session.step_move(0, 1)
        assert session.settlement is None
        assert session.save.location_id == 0
        assert (session.save.x, session.save.y) == (232, 135)

    def test_render_settlement_with_npcs(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))
        try:
            session = OverworldSession.from_data_dir()
            session.save.x, session.save.y = 232, 135
            session.enter_location()
            renderer = EgaRenderer()
            surf = renderer.render_overworld(session)
            assert surf.get_size() == (SCREEN_W, SCREEN_H)
        finally:
            pygame.quit()
