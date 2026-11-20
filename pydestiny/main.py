"""Entry point for PyDestiny (Ultima V Python reimplementation)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCALE, SCREEN_H, SCREEN_W, EgaRenderer

DIR_KEYS = {
    pygame.K_UP: (0, -1),
    pygame.K_KP8: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_KP2: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_KP4: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_KP6: (1, 0),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="PyDestiny — Ultima V Reimplementation")
    parser.add_argument("--save", type=Path, default=Path("save.json"), help="Save file path")
    parser.add_argument("--intro", action="store_true", help="Start with STORY.DAT intro")
    parser.add_argument("--new-game", action="store_true", help="Start character creation")
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W * SCALE, SCREEN_H * SCALE))
    pygame.display.set_caption("PyDestiny — Ultima V")
    clock = pygame.time.Clock()

    session = OverworldSession.from_data_dir(save_path=args.save)
    if args.intro:
        session.start_intro()
    elif args.new_game:
        session.start_char_creation()
    renderer = EgaRenderer()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if session.story_seq is not None:
                    if event.key == pygame.K_ESCAPE:
                        session.story_seq.skip()
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        session.story_seq.advance()
                    if session.story_seq.finished:
                        session.story_seq = None
                    continue

                if session.char_create is not None:
                    cc = session.char_create
                    if cc.step == 0:
                        if event.key == pygame.K_RETURN:
                            cc.step = 1
                        elif event.key == pygame.K_BACKSPACE:
                            cc.name = cc.name[:-1]
                        elif event.unicode and event.unicode.isprintable() and len(cc.name) < 8:
                            cc.name += event.unicode
                    elif cc.step == 1 and event.unicode:
                        cc.answer_choice(event.unicode)
                    elif 2 <= cc.step and event.unicode:
                        cc.answer_choice(event.unicode)
                    if cc.done:
                        session.finish_char_creation()
                    continue

                if session.shop_open:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        session.shop_open = False
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        session.shop_buy(event.key - pygame.K_1)
                    continue

                if session.talk_session is not None:
                    if event.key == pygame.K_RETURN:
                        session.submit_talk(session.talk_input)
                    elif event.key == pygame.K_ESCAPE:
                        session.talk_session = None
                        session.talk_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        session.talk_input = session.talk_input[:-1]
                    elif event.unicode and event.unicode.isprintable():
                        session.talk_input += event.unicode
                    continue

                if session.combat is not None:
                    if session.awaiting_attack_dir and event.key in DIR_KEYS:
                        dx, dy = DIR_KEYS[event.key]
                        session.combat.attack_dir(dx, dy)
                        session.awaiting_attack_dir = False
                        session.finish_combat_if_done()
                    elif event.key in DIR_KEYS:
                        dx, dy = DIR_KEYS[event.key]
                        session.combat.move_active(dx, dy)
                        session.finish_combat_if_done()
                    elif event.key == pygame.K_a:
                        session.awaiting_attack_dir = True
                        session.log("Attack-dir?")
                    elif event.key == pygame.K_SPACE:
                        session.combat.pass_active()
                        session.finish_combat_if_done()
                    continue

                if session.awaiting_look_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.look_at(dx, dy)
                    session.awaiting_look_dir = False
                elif session.awaiting_talk_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.start_talk(dx, dy)
                    session.awaiting_talk_dir = False
                elif session.awaiting_jimmy_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.jimmy_door(dx, dy)
                    session.awaiting_jimmy_dir = False
                elif session.awaiting_open_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.open_at(dx, dy)
                    session.awaiting_open_dir = False
                elif session.awaiting_search_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.search_at(dx, dy)
                    session.awaiting_search_dir = False
                elif event.key in DIR_KEYS and not session.ztats_open:
                    dx, dy = DIR_KEYS[event.key]
                    session.step_move(dx, dy)
                elif event.key == pygame.K_SPACE and not session.ztats_open:
                    session.pass_turn()
                elif event.key == pygame.K_e and not session.ztats_open:
                    session.enter_location()
                elif event.key == pygame.K_t and not session.ztats_open:
                    session.awaiting_talk_dir = True
                    session.log("Talk-dir?")
                elif event.key == pygame.K_l and not session.ztats_open:
                    session.awaiting_look_dir = True
                    session.log("Look-dir?")
                elif event.key == pygame.K_j and not session.ztats_open:
                    session.awaiting_jimmy_dir = True
                    session.log("Jimmy-dir?")
                elif event.key == pygame.K_o and not session.ztats_open:
                    session.awaiting_open_dir = True
                    session.log("Open-dir?")
                elif event.key == pygame.K_s and not session.ztats_open:
                    session.awaiting_search_dir = True
                    session.log("Search-dir?")
                elif event.key == pygame.K_c and not session.ztats_open:
                    session.cast_spell_quick(0, 0)  # In Lor (Light)
                elif event.key == pygame.K_k and not session.ztats_open:
                    if session.dungeon is not None:
                        session.klimb_dungeon(up=True)
                    elif session.settlement is not None:
                        session.klimb_settlement(up=True)
                elif event.key == pygame.K_d and not session.ztats_open:
                    if session.dungeon is not None:
                        session.klimb_dungeon(up=False)
                    elif session.settlement is not None:
                        session.klimb_settlement(up=False)
                elif event.key == pygame.K_F1 and not session.ztats_open:
                    session.start_intro()
                elif event.key == pygame.K_F2 and not session.ztats_open:
                    session.start_combat()
                elif event.key == pygame.K_F3 and not session.ztats_open and session.dungeon is None:
                    ox, oy = session.tables.location_coords[32]
                    session.save.x, session.save.y = ox, oy
                    session.enter_location()
                elif event.key == pygame.K_F4 and not session.ztats_open:
                    session.start_char_creation()
                elif event.key == pygame.K_z:
                    session.ztats_open = not session.ztats_open
                elif event.key == pygame.K_q:
                    session.save.save_json(args.save)
                    session.log("Saved!")
                    running = False

        canvas = renderer.render_overworld(session)
        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
