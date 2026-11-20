"""Phase 4 tests: 11x11 tactical combat, monster AI, victory/flee, and rendering."""

from __future__ import annotations

import os
import random

import pygame

from pydestiny.engine.combat_session import CombatSession
from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


class TestPhase4Combat:
    def test_combat_victory_and_exp(self) -> None:
        session = OverworldSession.from_data_dir()
        cbt = session.start_combat(cbt_index=0, monster_idx=20)  # Giant Rat (HP 10)
        assert cbt.active_actor is not None
        assert cbt.active_actor.is_party

        # Place all enemies adjacent to Avatar with 1 HP and high DEX for deterministic kill
        enemies = [a for a in cbt.actors if not a.is_party]
        assert len(enemies) > 0
        for idx, e in enumerate(enemies):
            e.hp = 1
            if idx == 0:
                e.x, e.y = cbt.active_actor.x, cbt.active_actor.y - 1
            else:
                e.hp = 0  # Leave 1 enemy alive

        cbt.active_actor.dex = 99  # Guarantee hit
        cbt.rng = random.Random(1)
        char_idx = cbt.active_actor.index
        prev_exp = session.save.characters[char_idx].exp
        cbt.attack_dir(0, -1)
        assert cbt.finished and cbt.victory
        assert session.save.characters[char_idx].exp > prev_exp

        session.finish_combat_if_done()
        assert session.combat is None

    def test_combat_flee_and_render(self) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))
        try:
            session = OverworldSession.from_data_dir()
            cbt = session.start_combat()
            party_actors = [a for a in cbt.actors if a.is_party]
            enemy_actors = [a for a in cbt.actors if not a.is_party]
            assert party_actors and all(a.tile_id in (320, 324, 328, 332) for a in party_actors)
            assert all(a.y in (9, 10) for a in party_actors)
            assert enemy_actors and all(a.tile_id == 448 for a in enemy_actors)
            renderer = EgaRenderer()
            surf = renderer.render_overworld(session)
            assert surf.get_size() == (SCREEN_W, SCREEN_H)

            # Flee all party actors off bottom edge
            while not cbt.finished and cbt.active_actor is not None:
                cbt.active_actor.y = 10
                cbt.move_active(0, 1)
            assert cbt.finished and not cbt.victory
        finally:
            pygame.quit()
