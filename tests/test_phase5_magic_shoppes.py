"""Phase 5 tests: spell effects, shoppe purchases, and shop UI rendering."""

from __future__ import annotations

import os
import random

import pygame

from pydestiny.engine.magic_effects import execute_spell
from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


class TestPhase5MagicShoppes:
    def test_spell_effects(self) -> None:
        session = OverworldSession.from_data_dir()
        session.darkness = 16
        # Give Mariah (char 3, level 3, MP 22) prepared spells
        session.save.prepared_spells[0] = 2   # In Lor
        session.save.prepared_spells[3] = 1   # An Nox
        session.save.prepared_spells[4] = 1   # Mani
        session.save.prepared_spells[9] = 1   # In Wis

        ok, _ = session.cast_spell_quick(3, 0)  # In Lor
        assert ok and session.darkness == 0

        # Cure Poison
        session.save.characters[0].status = "P"
        ok, _ = execute_spell(session.save, session.tables, 3, 3, target_char_idx=0)
        assert ok and session.save.characters[0].status == "G"

        # Mani heal
        session.save.characters[0].hp = 10
        ok, _ = execute_spell(
            session.save, session.tables, 3, 4, target_char_idx=0, rng=random.Random(1)
        )
        assert ok and session.save.characters[0].hp > 10

        # In Wis locate
        ok, msg = session.cast_spell_quick(3, 9)
        assert ok and f"({session.save.x},{session.save.y})" in msg

    def test_shoppe_purchases_and_render(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))
        try:
            session = OverworldSession.from_data_dir()
            prev_food = session.save.food
            prev_gold = session.save.gold
            ok, _ = session.shop_buy(0)  # Food x20 for 25g
            assert ok
            assert session.save.food == prev_food + 20
            assert session.save.gold == prev_gold - 25

            session.shop_open = True
            renderer = EgaRenderer()
            surf = renderer.render_overworld(session)
            assert surf.get_size() == (SCREEN_W, SCREEN_H)
        finally:
            pygame.quit()
