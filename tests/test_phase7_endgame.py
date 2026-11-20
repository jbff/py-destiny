"""Phase 7 tests: Grandfather clock look, Intro/Endgame story, Character Creation, and rendering."""

from __future__ import annotations

import os

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


class TestPhase7Endgame:
    def test_grandfather_clock_shows_time(self) -> None:
        session = OverworldSession.from_data_dir()
        # Enter LB's Castle and place a grandfather clock (0xFA) to the north
        session.save.x, session.save.y = 86, 107
        assert session.enter_location()
        assert session.settlement is not None
        session.settlement.current_floor(0)[session.save.y - 1][session.save.x] = 0xFA
        session.save.hour = 14
        session.save.minute = 5

        desc = session.look_at(0, -1)
        assert "grandfather clock" in desc.lower()
        assert "2:05 PM" in desc

    def test_intro_and_endgame_sequences(self) -> None:
        session = OverworldSession.from_data_dir()
        intro = session.start_intro()
        assert len(intro.pages) == 36
        assert "_" not in intro.current_text
        assert intro.advance()
        assert intro.page_idx == 1
        intro.skip()
        assert intro.finished

        end = session.trigger_endgame()
        assert session.endgame_won
        assert len(end.pages) == 11
        assert "_" not in end.current_text

    def test_character_creation_and_render(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))
        try:
            session = OverworldSession.from_data_dir()
            cc = session.start_char_creation()
            assert len(cc.intro_blocks) == 5
            cc.name = "Dupre"
            cc.step = 1
            cc.answer_choice("M")
            for _ in range(4):
                cc.answer_choice("A")
            assert cc.done
            session.finish_char_creation()
            assert session.save.characters[0].name == "Dupre"
            assert session.save.characters[0].char_class == "M"

            # Render intro and char creation screens
            renderer = EgaRenderer()
            session.start_intro()
            assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)
            session.story_seq = None
            session.start_char_creation()
            assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)
        finally:
            pygame.quit()
