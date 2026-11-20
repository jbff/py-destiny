"""End-to-end automated game simulation using GameSimulator and trace verification."""

from __future__ import annotations

import os
import random

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.engine.simulator import GameSimulator
from pydestiny.ui.ega_renderer import SCREEN_H, SCREEN_W, EgaRenderer


def test_full_game_simulation_trace(tmp_path) -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((SCREEN_W, SCREEN_H))
    try:
        session = OverworldSession.from_data_dir()
        sim = GameSimulator(session)
        renderer = EgaRenderer()

        # 1. Intro & Character Creation
        sim.act("start_intro", session.start_intro)
        assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)
        sim.act("skip_intro", lambda: setattr(session, "story_seq", None))

        sim.act("start_char_create", session.start_char_creation)
        assert session.char_create is not None
        session.char_create.name = "Shamino"
        session.char_create.step = 1
        session.char_create.answer_choice("M")
        for _ in range(4):
            session.char_create.answer_choice("B")
        sim.act("finish_char_create", session.finish_char_creation)
        assert session.save.characters[0].name == "Shamino"

        # 2. Overworld movement, Look, Pass, Save/Load
        sim.act("overworld_move_s", lambda: session.step_move(0, 1))
        sim.act("overworld_look_n", lambda: session.look_at(0, -1))
        sim.act("overworld_pass", session.pass_turn)
        save_file = tmp_path / "sim_save.json"
        sim.act("save_json", lambda: session.save.save_json(save_file))
        assert save_file.exists()

        # 3. Lord British's Castle: enter, walk onto a chair, clock, stairs, talk to Chuckles
        session.save.x, session.save.y = 86, 107
        sim.act("enter_lb_castle", session.enter_location)
        assert session.settlement is not None

        # Place a chair (0x90) ahead and step onto it -> verify not blocked & renders sitting
        session.settlement.current_floor(0)[session.save.y - 1][session.save.x] = 0x90
        moved = sim.act("step_onto_chair", lambda: session.step_move(0, -1))
        assert moved is True
        assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)

        # Grandfather clock look
        session.settlement.current_floor(0)[session.save.y - 1][session.save.x] = 0xFA
        clock_desc = sim.act("look_clock", lambda: session.look_at(0, -1))
        assert "AM" in clock_desc or "PM" in clock_desc

        # Climb ladder up & down at (3, 3)
        session.save.x, session.save.y = 3, 3
        assert sim.act("klimb_castle_up", lambda: session.klimb_settlement(up=True))
        assert sim.act("klimb_castle_down", lambda: session.klimb_settlement(up=False))

        # Talk to Chuckles (or first talkable NPC in LB's castle)
        talkable = next(n for n in session.settlement.npcs if 1 <= n.talk_id < 0x80 and n.z == 0)
        session.save.x, session.save.y = talkable.x, talkable.y + 1
        assert sim.act("talk_start", lambda: session.start_talk(0, -1))
        sim.act("talk_name", lambda: session.submit_talk("name"))
        sim.act("talk_job", lambda: session.submit_talk("job"))
        sim.act("talk_bye", lambda: session.submit_talk("bye"))
        assert session.talk_session is None

        # Open chest & jimmy locked door
        session.settlement.current_floor(0)[15][15] = 0x8F
        session.settlement.current_floor(0)[15][17] = 0xB8
        session.save.x, session.save.y = 16, 15
        session.save.keys = 2
        assert sim.act("open_chest", lambda: session.open_at(-1, 0))
        assert sim.act("jimmy_door", lambda: session.jimmy_door(1, 0))

        sim.act("exit_lb_castle", session.exit_settlement)

        # 4. Britain: open merchant shoppe & buy item
        session.save.x, session.save.y = 81, 106
        sim.act("enter_britain", session.enter_location)
        assert session.settlement is not None
        merchant = next(n for n in session.settlement.npcs if 0x81 <= n.talk_id <= 0x88 and n.z == 0)
        session.save.x, session.save.y = merchant.x, merchant.y + 1
        assert sim.act("open_shop", lambda: session.start_talk(0, -1))
        assert session.shop_open
        assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)
        sim.act("shop_buy_0", lambda: session.shop_buy(0))
        session.shop_open = False
        sim.act("exit_britain", session.exit_settlement)

        # 5. Tactical Combat (F2 grass map): attack & win
        cbt = sim.act("start_combat", session.start_combat)
        cbt.rng = random.Random(7)
        assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)
        enemies = [a for a in cbt.actors if not a.is_party]
        for idx, e in enumerate(enemies):
            if idx == 0:
                e.hp = 1
                e.x, e.y = cbt.active_actor.x, cbt.active_actor.y - 1
            else:
                e.hp = 0
        cbt.active_actor.dex = 99
        sim.act("combat_attack", lambda: cbt.attack_dir(0, -1))
        sim.act("finish_combat", session.finish_combat_if_done)
        assert session.combat is None

        # 6. 3D Dungeon (Deceit): enter, move, turn, descend, room combat, exit
        session.save.x, session.save.y = session.tables.location_coords[32]
        assert sim.act("enter_deceit", session.enter_location)
        assert session.dungeon is not None
        assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)
        sim.act("dng_turn_r", lambda: session.step_move(1, 0))
        sim.act("dng_turn_l", lambda: session.step_move(-1, 0))
        sim.act("dng_forward", lambda: session.step_move(0, -1))
        sim.act("dng_back", lambda: session.step_move(0, 1))
        assert sim.act("dng_exit", lambda: session.klimb_dungeon(up=True))
        assert session.dungeon is None

        # 7. Underworld Doom gate & Endgame
        session.save.z = 0
        session.save.x, session.save.y = session.tables.location_coords[39]
        assert sim.act("doom_blocked_overworld", session.enter_location) is False
        session.save.z = 0xFF
        assert sim.act("enter_doom_underworld", session.enter_location) is True
        sim.act("trigger_endgame", session.trigger_endgame)
        assert session.endgame_won
        assert renderer.render_overworld(session).get_size() == (SCREEN_W, SCREEN_H)

        transcript = sim.to_transcript()
        assert len(sim.trace) >= 25
        assert "overworld" in transcript and "settlement" in transcript and "dungeon" in transcript
    finally:
        pygame.quit()
